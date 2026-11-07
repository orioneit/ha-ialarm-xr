"""End-to-end tests against a fake cloud."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.ialarm_xr.const import CONF_DEVICE_ID, CONF_PIN, DOMAIN


async def _setup(hass: HomeAssistant, cloud, options=None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Casa Mamma",
        unique_id="0123456789",
        data={CONF_DEVICE_ID: "0123456789", CONF_PASSWORD: "secret",
              CONF_HOST: "127.0.0.1", CONF_PORT: cloud.port},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow(hass: HomeAssistant, cloud) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    bad = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Casa", CONF_DEVICE_ID: "0123456789", CONF_PASSWORD: "wrong",
         CONF_HOST: "127.0.0.1", CONF_PORT: cloud.port}
    )
    assert bad["errors"] == {"base": "invalid_auth"}
    ok = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Casa", CONF_DEVICE_ID: "0123456789", CONF_PASSWORD: "secret",
         CONF_HOST: "127.0.0.1", CONF_PORT: cloud.port}
    )
    assert ok["type"] is FlowResultType.CREATE_ENTRY
    assert ok["title"] == "Casa"


async def test_entities(hass: HomeAssistant, cloud) -> None:
    await _setup(hass, cloud)
    assert hass.states.get("alarm_control_panel.casa_mamma").state == "disarmed"
    assert hass.states.get("binary_sensor.casa_mamma_cucinapersiana_battery").state == "on"
    assert hass.states.get("binary_sensor.casa_mamma_portone_alarm").state == "off"
    reg = er.async_get(hass)
    # Disabled panel zones are created but disabled in HA
    tunnel = reg.async_get("binary_sensor.casa_mamma_tunnel_pir_alarm")
    assert tunnel is not None and tunnel.disabled_by is not None
    # Unnamed zones are not created
    assert len([e for e in reg.entities.values() if e.platform == DOMAIN and e.domain == "binary_sensor"]) == 10 * 4


async def test_arm_disarm(hass: HomeAssistant, cloud) -> None:
    await _setup(hass, cloud)
    await hass.services.async_call("alarm_control_panel", "alarm_arm_away",
                                   {"entity_id": "alarm_control_panel.casa_mamma"}, blocking=True)
    await hass.async_block_till_done()
    assert cloud.commands == ["ARM"]
    assert hass.states.get("alarm_control_panel.casa_mamma").state == "armed_away"
    # Zone in alarm while armed -> triggered
    cloud.zone_raw[1] = 3
    await hass.config_entries.async_entries(DOMAIN)[0].runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("alarm_control_panel.casa_mamma").state == "triggered"
    await hass.services.async_call("alarm_control_panel", "alarm_disarm",
                                   {"entity_id": "alarm_control_panel.casa_mamma"}, blocking=True)
    await hass.async_block_till_done()
    assert cloud.commands[-1] == "DISARM"


async def test_pin(hass: HomeAssistant, cloud) -> None:
    await _setup(hass, cloud, options={CONF_PIN: "4321"})
    cloud.status = "ARM"
    await hass.config_entries.async_entries(DOMAIN)[0].runtime_data.async_refresh()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("alarm_control_panel", "alarm_disarm",
                                       {"entity_id": "alarm_control_panel.casa_mamma", "code": "0000"},
                                       blocking=True)
    assert cloud.commands == []
    await hass.services.async_call("alarm_control_panel", "alarm_disarm",
                                   {"entity_id": "alarm_control_panel.casa_mamma", "code": "4321"},
                                   blocking=True)
    assert cloud.commands == ["DISARM"]
