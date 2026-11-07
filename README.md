# iAlarm-XR (cloud) for Home Assistant

[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/orioneit/ha-ialarm-xr/actions/workflows/validate.yml/badge.svg)](https://github.com/orioneit/ha-ialarm-xr/actions/workflows/validate.yml)

Unofficial Home Assistant integration for **Antifurto365 iAlarm-XR** alarm panels,
which are not supported by the core [iAlarm integration](https://www.home-assistant.io/integrations/ialarm/).
It connects through the iAlarm cloud, like the mobile app.

🇮🇹 [Versione italiana](#italiano)

> [!IMPORTANT]
> We strongly recommend changing the factory default panel password in the iAlarm app.

> [!NOTE]
> Not affiliated with Antifurto365 or Meian. The vendor may change its service at any time.

## Features

- Alarm control panel: arm away, arm home (partial), disarm; shows triggered.
- Optional PIN to disarm from Home Assistant.
- Per zone: alarm, low battery, signal lost and bypass (disabled by default) sensors.

**Limitations:** door/window open-closed state is not reported by the panel;
state is polled every 30 s (configurable); requires Internet.

## Installation

**HACS:** *Custom repositories* → `https://github.com/orioneit/ha-ialarm-xr` (category *Integration*) → install → restart.

**Manual:** copy `custom_components/ialarm_xr` to `config/custom_components/` and restart.

## Configuration

*Settings → Devices & services → Add integration → iAlarm-XR (cloud)*

- **Panel ID** and **panel password**: from the iAlarm app (the device password, not your account).
- **Cloud server** and **port**: see the iAlarm app settings or the official manuals.

Options: polling interval and disarm PIN.

## Credits

Based on the Meian protocol work of [wildstray/meian-client](https://github.com/wildstray/meian-client)
and [pyasyncialarm](https://pypi.org/project/pyasyncialarm/). MIT license.

---

<a name="italiano"></a>
## 🇮🇹 Italiano

Integrazione non ufficiale per le centrali **Antifurto365 iAlarm-XR**, non supportate
dall'integrazione iAlarm ufficiale. Si collega tramite il cloud iAlarm, come l'app.

> [!IMPORTANT]
> Ti consigliamo vivamente di cambiare la password di fabbrica della centrale dall'app iAlarm.

**Funzioni:** pannello d'allarme (totale, parziale, disinserito, scattato), PIN opzionale
per disinserire, e per ogni zona sensori di allarme, batteria scarica, segnale perso ed esclusione.

**Limiti:** la centrale non comunica porte/finestre aperte; aggiornamento ogni 30 s
(configurabile); serve Internet.

**Installazione:** HACS → *Repository personalizzati* → `https://github.com/orioneit/ha-ialarm-xr`
(categoria *Integrazione*), poi *Impostazioni → Dispositivi e servizi → Aggiungi integrazione*.

**Configurazione:** ID e password della centrale dall'app iAlarm (non quelli dell'account);
server cloud e porta li trovi nelle impostazioni dell'app iAlarm o nei manuali ufficiali.
