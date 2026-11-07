"""Zone binary sensors for iAlarm-XR."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import Zone
from .coordinator import IAlarmConfigEntry, IAlarmCoordinator
from .entity import IAlarmEntity


@dataclass(frozen=True, kw_only=True)
class ZoneSensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[Zone], bool | None]


DESCRIPTIONS: tuple[ZoneSensorDescription, ...] = (
    ZoneSensorDescription(
        key="alarm",
        translation_key="zone_alarm",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=lambda z: z.alarm,
    ),
    ZoneSensorDescription(
        key="low_battery",
        translation_key="zone_low_battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda z: z.low_battery,
    ),
    ZoneSensorDescription(
        key="lost",
        translation_key="zone_lost",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda z: z.lost,
    ),
    ZoneSensorDescription(
        key="bypass",
        translation_key="zone_bypass",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda z: z.bypass,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ZoneBinarySensor(coordinator, zone, description)
        for zone in coordinator.data.zones.values()
        for description in DESCRIPTIONS
    )


class ZoneBinarySensor(IAlarmEntity, BinarySensorEntity):
    """One aspect (alarm, battery, ...) of one zone."""

    entity_description: ZoneSensorDescription

    def __init__(self, coordinator: IAlarmCoordinator, zone: Zone, description: ZoneSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._zone = zone.number
        self._attr_unique_id = f"{coordinator.client.device_id}_zone{zone.number}_{description.key}"
        self._attr_translation_placeholders = {"zone": zone.name}
        # Disabled zones on the panel: create the entities but keep them disabled.
        if not zone.enabled:
            self._attr_entity_registry_enabled_default = False

    @property
    def is_on(self) -> bool | None:
        zone = self.coordinator.data.zones.get(self._zone)
        return None if zone is None else self.entity_description.value_fn(zone)

    @property
    def extra_state_attributes(self) -> dict:
        zone = self.coordinator.data.zones.get(self._zone)
        if zone is None:
            return {}
        return {"zone": zone.number, "zone_type": zone.type, "zone_enabled": zone.enabled}
