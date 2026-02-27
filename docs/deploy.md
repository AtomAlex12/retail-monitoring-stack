# Развёртывание

## Первоначальная настройка

### 1. Репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/retail-monitoring-stack.git
cd retail-monitoring-stack
```

### 2. Конфигурация

- Отредактируйте `config.alloy` — URL Prometheus, IP MikroTik
- Создайте `snmp_mikrotik.yml` (см. [snmp-config.md](snmp-config.md))
- В `docker-compose.yml` укажите `PROMETHEUS_URL`

### 3. Развёртывание на точках

На каждый Windows‑ПК:

1. Установите Grafana Alloy
2. Скопируйте `config.alloy` и `snmp_mikrotik.yml`
3. Настройте MikroTik (см. [mikrotik.md](mikrotik.md))
4. Запустите Alloy

### 4. Центральный сервер

```bash
docker compose up -d
```

Добавьте в Prometheus scrape для `store-registry` (порт 9095).

### 5. Grafana

Импортируйте дашборды из `dashboard-retail.json` и `dashboard-points-overview.json`.
