"""The iAlarm-XR integration (cloud)."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .api import IAlarmXR
from .const import CONF_DEVICE_ID
from .coordinator import IAlarmConfigEntry, IAlarmCoordinator

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: IAlarmConfigEntry) -> bool:
    """Set up iAlarm-XR from a config entry."""
    client = IAlarmXR(
        entry.data[CONF_DEVICE_ID],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
    )
    coordinator = IAlarmCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IAlarmConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: IAlarmConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
