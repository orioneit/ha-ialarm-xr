# Changelog

## 0.2.0

- New per-zone **contact open/closed** sensor. Requires *Magnet check*
  ("Controllo Magneti") to be enabled in the iAlarm app.
- Nuovo sensore **contatto aperto/chiuso** per ogni zona. Richiede che nell'app
  iAlarm sia attivo *Controllo Magneti*.
- Zone sensors expose the raw panel status as the `zone_status_raw` attribute.

## 0.1.0

- Initial release: alarm control panel, optional disarm PIN, per-zone alarm,
  low battery, signal lost and bypass sensors.
