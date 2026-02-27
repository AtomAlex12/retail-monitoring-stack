#!/usr/bin/env python3
"""
Экспортёр реестра точек (stores) для Prometheus.
- При появлении новой точки в Prometheus — автоматически добавляет её в реестр
- Хранит точки 30 дней с момента последнего появления
- Через 30 дней без появлений точка удаляется

Веб-интерфейс: техническая страница для настройки и мониторинга.
HTML/CSS/JS в папке web/ — монтируется как volume, можно редактировать без пересборки контейнера.

Запуск: PROMETHEUS_URL=http://... python store-registry-exporter.py
Порты: 9095 (metrics), 8080 (web)
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

from flask import Flask, jsonify, send_from_directory
from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily

VERSION = "0.2.0-beta"
REGISTRY_FILE = os.environ.get(
    "REGISTRY_FILE",
    os.path.join(os.path.dirname(__file__), "store-registry-state.json"),
)
PORT = int(os.environ.get("PORT", "9095"))
WEB_PORT = int(os.environ.get("WEB_PORT", "8080"))
WEB_DIR = os.environ.get("WEB_DIR", os.path.join(os.path.dirname(__file__), "web"))
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
QUERY_INTERVAL = 300
RETENTION_DAYS = 30
# Порог "свежести" данных (сек). При remote_write Prometheus не помечает метрики stale,
# и возвращает последнее значение до 5+ минут. Точки без данных за STALENESS_SEC считаются офлайн.
STALENESS_SEC = int(os.environ.get("STALENESS_SEC", "120"))

registry: dict[str, float] = {}
registry_lock = threading.Lock()
last_sync_time: float = 0
last_sync_error: str | None = None

app = Flask(__name__, static_folder=os.path.join(WEB_DIR, "static"))


def load_version():
    vfile = os.path.join(os.path.dirname(__file__), "VERSION")
    if os.path.exists(vfile):
        with open(vfile, encoding="utf-8") as f:
            return f.read().strip()
    return VERSION


def load_registry():
    global registry
    old_file = os.path.join(os.path.dirname(__file__), "stores-registry.json")
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                with registry_lock:
                    registry.update(data)
        except (json.JSONDecodeError, IOError):
            pass
    elif os.path.exists(old_file):
        try:
            with open(old_file, encoding="utf-8") as f:
                stores = json.load(f)
            now = time.time()
            with registry_lock:
                for store in stores:
                    registry[store] = now
            save_registry()
            print(f"Миграция: загружено {len(stores)} точек из stores-registry.json")
        except (json.JSONDecodeError, IOError):
            pass


def save_registry():
    with registry_lock:
        data = dict(registry)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_stores_from_prometheus():
    # Фильтр по свежести: только точки с данными за последние STALENESS_SEC.
    # При remote_write Prometheus не помечает метрики stale — возвращает последнее значение.
    # Без фильтра точка остаётся "зелёной" 5+ минут после остановки Alloy.
    query = (
        f'max by (store) (up{{job=~"retail_windows|retail_mikrotik"}} '
        f'and (time() - timestamp(up{{job=~"retail_windows|retail_mikrotik"}}) < {STALENESS_SEC}))'
    )
    url = f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query?{urlencode({'query': query})}"
    try:
        with urlopen(url, timeout=10) as resp:
            data = json.load(resp)
    except Exception as e:
        return [], str(e)
    if data.get("status") != "success":
        return [], data.get("error", "unknown")
    results = data.get("data", {}).get("result", [])
    # Только up=1 (онлайн)
    return [
        r["metric"]["store"]
        for r in results
        if "store" in r.get("metric", {}) and r.get("value", [None, "0"])[1] == "1"
    ], None


def cleanup_expired():
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).timestamp()
    with registry_lock:
        expired = [s for s, ts in registry.items() if ts < cutoff]
        for s in expired:
            del registry[s]
    if expired:
        print(f"Удалено {len(expired)} точек старше {RETENTION_DAYS} дней")


def update_registry():
    global last_sync_time, last_sync_error
    stores, err = fetch_stores_from_prometheus()
    last_sync_error = err
    last_sync_time = time.time()
    if err:
        return
    now = time.time()
    added = []
    with registry_lock:
        for store in stores:
            if store not in registry:
                added.append(store)
            registry[store] = now
    if added:
        print(f"Добавлено новых точек: {added}")
    cleanup_expired()
    save_registry()


def get_active_stores():
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).timestamp()
    with registry_lock:
        return [s for s, ts in registry.items() if ts >= cutoff]


class StoreRegistryCollector:
    def collect(self):
        gauge = GaugeMetricFamily(
            "retail_store_expected",
            "Ожидаемая точка (в реестре, автообновление)",
            labels=["store"],
        )
        for store in get_active_stores():
            gauge.add_metric([store], 1)
        yield gauge


def sync_loop():
    while True:
        try:
            update_registry()
        except Exception as e:
            print(f"Ошибка в sync_loop: {e}")
        time.sleep(QUERY_INTERVAL)


# --- Web routes ---


@app.route("/")
def index():
    path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(path):
        return send_from_directory(WEB_DIR, "index.html")
    return "<h1>Store Registry Exporter</h1><p>Добавьте web/index.html</p>", 404


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(WEB_DIR, "static"), filename)


@app.route("/api/registry")
def api_registry():
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).timestamp()
    with registry_lock:
        items = [
            {"store": s, "last_seen": ts, "last_seen_iso": datetime.fromtimestamp(ts).isoformat()}
            for s, ts in sorted(registry.items(), key=lambda x: -x[1])
            if ts >= cutoff
        ]
    return jsonify({"stores": items, "count": len(items)})


@app.route("/api/status")
def api_status():
    stores_up, err = fetch_stores_from_prometheus()
    return jsonify({
        "version": load_version(),
        "prometheus_url": PROMETHEUS_URL,
        "registry_file": REGISTRY_FILE,
        "retention_days": RETENTION_DAYS,
        "last_sync": last_sync_time and datetime.fromtimestamp(last_sync_time).isoformat(),
        "last_sync_error": last_sync_error,
        "prometheus_reachable": err is None,
        "stores_up_now": len(stores_up) if not err else 0,
        "stores_in_registry": len(get_active_stores()),
    })


@app.route("/api/up")
def api_up():
    """Текущий статус up из Prometheus."""
    stores_up, err = fetch_stores_from_prometheus()
    if err:
        return jsonify({"error": err, "stores": []}), 500
    return jsonify({"stores": sorted(stores_up)})


def prometheus_query(query: str):
    """Выполнить instant-запрос к Prometheus."""
    url = f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query?{urlencode({'query': query})}"
    try:
        with urlopen(url, timeout=10) as resp:
            data = json.load(resp)
    except Exception as e:
        return None, str(e)
    if data.get("status") != "success":
        return None, data.get("error", "unknown")
    return data.get("data", {}).get("result", []), None


@app.route("/api/version")
def api_version():
    return jsonify({"version": load_version()})


@app.route("/api/store/<store>")
def api_store_detail(store):
    """Детали по точке: Windows (ПК) и MikroTik (SNMP)."""
    out = {"version": load_version(), "store": store, "windows": [], "mikrotik": [], "snmp_interfaces": [], "error": None}

    # Windows: все метрики
    res, err = prometheus_query('{job="retail_windows", store="' + store + '"}')
    if err:
        out["error"] = err
    else:
        for r in res:
            m = r.get("metric", {})
            val = r.get("value", [None, None])[1]
            out["windows"].append({
                "metric": m.get("__name__", "?"),
                "value": val,
                "labels": {k: v for k, v in m.items() if k not in ("__name__", "job", "store")},
            })

    # MikroTik / SNMP: все метрики и интерфейсы
    res, err = prometheus_query('{job="retail_mikrotik", store="' + store + '"}')
    if not err:
        seen_if = set()
        for r in res:
            m = r.get("metric", {})
            val = r.get("value", [None, None])[1]
            name = m.get("__name__", "?")
            out["mikrotik"].append({
                "metric": name,
                "value": val,
                "labels": {k: v for k, v in m.items() if k not in ("__name__", "job", "store")},
            })
            # Интерфейсы из snmp_if_oper_status или snmp_ifOperStatus
            if name in ("snmp_if_oper_status", "snmp_ifOperStatus") and "ifName" in m:
                key = m.get("ifName", "")
                if key and key not in seen_if:
                    seen_if.add(key)
                    out["snmp_interfaces"].append({
                        "ifName": m.get("ifName", "?"),
                        "ifAlias": m.get("ifAlias", ""),
                        "status": "Up" if val == "1" else "Down",
                        "value": val,
                    })

    return jsonify(out)


def run_web():
    app.run(host="0.0.0.0", port=WEB_PORT, threaded=True, use_reloader=False)


def main():
    load_registry()
    cleanup_expired()

    REGISTRY.register(StoreRegistryCollector())

    print(f"Prometheus: {PROMETHEUS_URL}")
    print(f"Реестр: {REGISTRY_FILE}, хранение {RETENTION_DAYS} дней")
    print(f"Метрики: http://0.0.0.0:{PORT}/metrics")
    print(f"Веб-интерфейс: http://0.0.0.0:{WEB_PORT}/ (папка web/ редактируется без пересборки)")
    start_http_server(PORT)
    t_sync = threading.Thread(target=sync_loop, daemon=True)
    t_sync.start()
    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
