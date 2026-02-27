#!/bin/bash
# Развёртывание Store Registry из публичного репо
# Использование: ./deploy.sh [URL_PROMETHEUS]
# Пример: ./deploy.sh http://192.168.141.49:9090

set -e
REPO="https://github.com/AtomAlex12/retail-monitoring-stack.git"
DIR="retail-monitoring-stack"

PROMETHEUS_URL="${1:-http://192.168.141.49:9090}"

if [ ! -d "$DIR" ]; then
  echo "Клонирование репозитория..."
  git clone "$REPO" "$DIR"
  cd "$DIR"
else
  echo "Обновление репозитория..."
  cd "$DIR"
  git pull
fi

echo "PROMETHEUS_URL=$PROMETHEUS_URL"
export PROMETHEUS_URL
docker compose up -d --build

echo ""
echo "Готово. Веб-панель: http://localhost:8080/  Метрики: http://localhost:9095/metrics"
