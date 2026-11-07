"""Data update coordinator for iAlarm-XR."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IAlarmAuthError, IAlarmError, IAlarmXR, PanelData
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type IAlarmConfigEntry = ConfigEntry[IAlarmCoordinator]


class IAlarmCoordinator(DataUpdateCoordinator[PanelData]):
    """Polls the panel through the cloud."""

    config_entry: IAlarmConfigEntry

    def __init__(self, hass: HomeAssistant, entry: IAlarmConfigEntry, client: IAlarmXR) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self._failures = 0

    async def _async_update_data(self) -> PanelData:
        try:
            data = await self.client.fetch()
        except IAlarmAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except IAlarmError as err:
            # The cloud occasionally misses a reply: tolerate one failure
            # before marking entities unavailable.
            self._failures += 1
            if self._failures < 2 and self.data is not None:
                _LOGGER.debug("Transient error, keeping last data: %s", err)
                return self.data
            raise UpdateFailed(str(err)) from err
        self._failures = 0
        return data
