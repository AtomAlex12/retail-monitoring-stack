# Retail Monitoring Stack

> Система мониторинга розничных точек: Windows‑ПК, роутеры MikroTik (LTE), Grafana Alloy, Prometheus, Grafana.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0--beta-orange)](VERSION)
[![Grafana Alloy](https://img.shields.io/badge/Grafana-Alloy-orange)](https://grafana.com/docs/alloy/)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-red)](https://prometheus.io/)

---

## Возможности

- **Windows‑ПК** — CPU, память, диск, сеть, сервисы (через Grafana Alloy)
- **MikroTik** — статус интерфейсов, трафик, ICCID/UICC SIM‑карт (SNMP)
- **Универсальный конфиг** — один `config.alloy` на все точки, `store = hostname`
- **Store Registry** — автообнаружение точек, хранение 30 дней, отображение недоступных красным
- **Веб‑панель** — техническая страница экспортёра (редактируемая без пересборки)
- **Grafana** — готовые дашборды для Windows и MikroTik

## Архитектура

```
┌─────────────────┐     VPN      ┌──────────────────────┐
│  Точка (магазин)│──────────────│  Центральный сервер   │
│                 │              │                      │
│  ┌───────────┐  │  remote_write│  ┌──────────────┐   │
│  │ Alloy     │──┼──────────────┼─►│ Prometheus   │   │
│  │ Windows   │  │              │  └──────┬───────┘   │
│  │ + SNMP    │  │              │         │           │
│  └───────────┘  │              │  ┌──────▼───────┐   │
│        │        │              │  │ Grafana      │   │
│  ┌─────▼─────┐  │              │  └──────────────┘   │
│  │ MikroTik  │  │              │  ┌──────────────┐   │
│  │ (SNMP)    │  │              │  │ Store Registry│   │
│  └───────────┘  │              │  │ (Docker)      │   │
└─────────────────┘              │  └──────────────┘   │
                                 └──────────────────────┘
```

## Быстрый старт

### 1. На Windows‑ПК (точка)

1. Установите [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/windows/).
2. Скопируйте `config.alloy` и `snmp_mikrotik.yml` в папку Alloy.
3. Укажите IP MikroTik и URL Prometheus в `config.alloy`.
4. Запустите Alloy (служба или `alloy run config.alloy`).

### 2. На MikroTik

Выполните скрипт SNMP и ICCID (см. [docs/mikrotik.md](docs/mikrotik.md)).

### 3. На центральном сервере

```bash
# Store Registry (опционально, для отображения недоступных точек красным)
docker compose up -d
```

- **Веб‑панель:** http://localhost:8080/
- **Метрики:** http://localhost:9095/metrics

### 4. Prometheus

Добавьте в `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "store-registry"
    static_configs:
      - targets: ["localhost:9095"]
```

### 5. Grafana

Импортируйте `dashboard-retail.json` и `dashboard-points-overview.json`.

---

## Структура проекта

```
.
├── config.alloy              # Конфиг Alloy (Windows + MikroTik SNMP)
├── snmp_mikrotik.yml         # SNMP‑модули (создать по образцу)
├── store-registry-exporter.py
├── docker-compose.yml
├── Dockerfile.store-registry
├── web/                      # Веб‑панель (редактируется без пересборки)
│   ├── index.html
│   └── static/
│       ├── style.css
│       └── app.js
├── dashboard-retail.json     # Дашборд Windows + MikroTik
├── dashboard-points-overview.json
└── docs/
    ├── mikrotik.md           # Скрипты MikroTik
    └── snmp-config.md        # Настройка SNMP
```

---

## Документация

| Раздел | Описание |
|-------|----------|
| [config.alloy](config.alloy) | Конфигурация Alloy |
| [docs/mikrotik.md](docs/mikrotik.md) | SNMP и ICCID на MikroTik |
| [docs/snmp-config.md](docs/snmp-config.md) | Генерация snmp_mikrotik.yml |

---

## Store Registry Exporter

Экспортёр реестра точек — опрашивает Prometheus, автоматически добавляет новые точки, хранит 30 дней.

**Переменные окружения:**

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `PROMETHEUS_URL` | URL Prometheus | `http://localhost:9090` |
| `REGISTRY_FILE` | Файл реестра | `store-registry-state.json` |
| `WEB_PORT` | Порт веб‑панели | `8080` |
| `WEB_DIR` | Папка с HTML/CSS/JS | `./web` |

**API:**

- `GET /api/registry` — реестр точек
- `GET /api/status` — статус экспортёра
- `GET /api/up` — текущие онлайн‑точки

---

### Версионность

- Версия в файле `VERSION` (сейчас `0.2.0-beta`)
- При пуше в Git — репозиторий в статусе beta
- Смена версии: отредактируйте `VERSION`, закоммитьте
- Для стабильного релиза: `1.0.0` вместо `0.2.0-beta`

---

## Лицензия

[MIT](LICENSE)
