"""Alarm control panel for iAlarm-XR."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import STATUS_ARM, STATUS_CLEAR, STATUS_DISARM, STATUS_STAY, IAlarmError
from .const import CONF_PIN
from .coordinator import IAlarmConfigEntry
from .entity import IAlarmEntity

_STATE_MAP = {
    STATUS_ARM: AlarmControlPanelState.ARMED_AWAY,
    STATUS_STAY: AlarmControlPanelState.ARMED_HOME,
    STATUS_DISARM: AlarmControlPanelState.DISARMED,
    STATUS_CLEAR: AlarmControlPanelState.DISARMED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([IAlarmPanel(entry.runtime_data)])


class IAlarmPanel(IAlarmEntity, AlarmControlPanelEntity):
    """The panel."""

    _attr_name = None
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY | AlarmControlPanelEntityFeature.ARM_HOME
    )
    _attr_code_arm_required = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.client.device_id
        self._pin: str | None = coordinator.config_entry.options.get(CONF_PIN) or None
        self._attr_code_format = CodeFormat.NUMBER if self._pin else None

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        data = self.coordinator.data
        state = _STATE_MAP.get(data.status)
        if state in (AlarmControlPanelState.ARMED_AWAY, AlarmControlPanelState.ARMED_HOME) and data.triggered:
            return AlarmControlPanelState.TRIGGERED
        return state

    @property
    def extra_state_attributes(self) -> dict:
        return {"panel_status": self.coordinator.data.status}

    async def _send(self, status: str) -> None:
        try:
            await self.coordinator.client.set_status(status)
        except IAlarmError as err:
            raise HomeAssistantError(f"iAlarm-XR: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        if self._pin and code != self._pin:
            raise ServiceValidationError("Codice errato / wrong code")
        await self._send(STATUS_DISARM)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._send(STATUS_ARM)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._send(STATUS_STAY)
