# Remote Write и «залипание» зелёного статуса

## Проблема

При использовании **remote_write** (Alloy → Prometheus) точка остаётся зелёной **5+ минут** после остановки Alloy или обрыва связи.

**Причина:** Prometheus при remote_write не помечает метрики как stale. В отличие от активного scrape, где при неудачном опросе сразу пишется `up=0`, при push-модели Prometheus просто перестаёт получать данные и продолжает возвращать **последнее известное значение** (up=1).

## Решение

Фильтр по свежести данных через `timestamp()` в PromQL:

```promql
up{job=~"retail_windows|retail_mikrotik"}
  and (time() - timestamp(up{job=~"retail_windows|retail_mikrotik"}) < 120)
```

Точка считается **онлайн** только если данные получены за последние **120 секунд** (2 мин).

## Где применено

- **Дашборд** `dashboard-points-overview.json` — панель «Точки (store = hostname)»
- **Store Registry Exporter** — запрос `fetch_stores_from_prometheus()` для подсчёта онлайн-точек

## Настройка порога

Переменная окружения `STALENESS_SEC` (по умолчанию 120):

```bash
docker run -e STALENESS_SEC=90 ...
```

Или в `docker-compose.yml`:

```yaml
environment:
  - STALENESS_SEC=90
```

Рекомендуется: 90–180 сек. Интервал scrape Alloy: 15s (Windows), 30s (SNMP).
