"""Base entity for iAlarm-XR."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IAlarmCoordinator


class IAlarmEntity(CoordinatorEntity[IAlarmCoordinator]):
    """Common device info."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IAlarmCoordinator) -> None:
        super().__init__(coordinator)
        device_id = coordinator.client.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=coordinator.config_entry.title,
            manufacturer="Antifurto365 / Meian",
            model="iAlarm-XR",
            serial_number=device_id,
        )
