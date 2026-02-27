# Конфигурация SNMP для MikroTik

Файл `snmp_mikrotik.yml` использует формат [snmp_exporter](https://github.com/prometheus/snmp_exporter).

## Генерация конфига

1. Клонируйте репозиторий `snmp_exporter`
2. Используйте `generator` для создания конфига с модулем `mikrotik`
3. Скопируйте результат в `snmp_mikrotik.yml` рядом с `config.alloy`

## Минимальный пример (if_mib)

```yaml
modules:
  if_mib:
    walk:
      - 1.3.6.1.2.1.2
    version: 2
    auth:
      community: monitor
```

На практике лучше использовать сгенерированный конфиг с модулем `mikrotik` для полной поддержки RouterOS.
