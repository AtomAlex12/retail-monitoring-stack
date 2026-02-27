# Развёртывание Store Registry из публичного репо
# Использование: .\deploy.ps1 [-PrometheusUrl "http://192.168.141.49:9090"]

param(
    [string]$PrometheusUrl = "http://192.168.141.49:9090"
)

$ErrorActionPreference = "Stop"
$Repo = "https://github.com/AtomAlex12/retail-monitoring-stack.git"
$Dir = "retail-monitoring-stack"

if (-not (Test-Path $Dir)) {
    Write-Host "Клонирование репозитория..."
    git clone $Repo $Dir
    Set-Location $Dir
} else {
    Write-Host "Обновление репозитория..."
    Set-Location $Dir
    git pull
}

$env:PROMETHEUS_URL = $PrometheusUrl
Write-Host "PROMETHEUS_URL=$PrometheusUrl"
docker compose up -d --build

Write-Host ""
Write-Host "Готово. Веб-панель: http://localhost:8080/  Метрики: http://localhost:9095/metrics"
