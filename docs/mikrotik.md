# Настройка MikroTik

## Включение SNMP v2c

Выполните в терминале WinBox/SSH:

```routeros
:local snmpCommunity "monitor"
:local snmpContact   "IT Dept"
:local snmpLocation  "Store-001 Router"

/snmp set enabled=yes contact=$snmpContact location=$snmpLocation

/snmp community
:if ([:len [find name=$snmpCommunity]] = 0) do={
    add name=$snmpCommunity addresses="" authentication-password="" encryption-password="" security=none
} else={
    :put ("SNMP community \"" . $snmpCommunity . "\" уже существует")
}
```

## Скрипт ICCID/UICC для LTE

Создаёт комментарии у интерфейсов `lte1` и `lte2` с ICCID/UICC (видны по SNMP как `ifAlias`).

```routeros
/system script
add name="update-lte-comments" policy=read,write,test source="
  :local iccid1 \"\"
  :local iccid2 \"\"
  :local uicc1 \"\"
  :local uicc2 \"\"

  :do { :set iccid1 [/interface lte at-chat lte1 input=\"AT+ICCID?\" as-value] } on-error={ :set iccid1 \"error\" }
  :do { :set iccid2 [/interface lte at-chat lte2 input=\"AT+ICCID?\" as-value] } on-error={ :set iccid2 \"error\" }
  :do { :local info1 [/interface lte info lte1 once as-value]; :set uicc1 (\$info1->\"uicc\") } on-error={ :set uicc1 \"\" }
  :do { :local info2 [/interface lte info lte2 once as-value]; :set uicc2 (\$info2->\"uicc\") } on-error={ :set uicc2 \"\" }

  /interface lte
  :if ([:len [find name=\"lte1\"]] > 0) do={ set [find name=\"lte1\"] comment=(\"MAIN_ICCID=\" . \$iccid1 . \"; MAIN_UICC=\" . \$uicc1) }
  :if ([:len [find name=\"lte2\"]] > 0) do={ set [find name=\"lte2\"] comment=(\"BACKUP_ICCID=\" . \$iccid2 . \"; BACKUP_UICC=\" . \$uicc2) }
"
```

Планировщик (раз в час):

```routeros
/system scheduler
add name="update-lte-comments" interval=1h on-event="update-lte-comments" start-time=startup
```
