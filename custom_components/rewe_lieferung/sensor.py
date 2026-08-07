"""Sensor-Plattform für die REWE Lieferung Integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CUSTOMERS_BEFORE,
    ATTR_DELIVERY_ID,
    ATTR_EXPECTED_ARRIVAL_START,
    ATTR_RAW_STATUS,
    ATTR_RECEIVED_AT,
    CONF_WEBHOOK_ID,
    DOMAIN,
    STATUS_LABELS_DE,
)
from .coordinator import ReweLieferungCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ReweLieferungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReweLieferungSensor(coordinator, entry)])


class ReweLieferungSensor(CoordinatorEntity[ReweLieferungCoordinator], SensorEntity):
    """Zeigt den aktuellen REWE-Lieferstatus."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:truck-delivery"

    def __init__(self, coordinator: ReweLieferungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="REWE Lieferung",
            manufacturer="REWE",
            model="Lieferservice Tracking",
        )

    @property
    def native_value(self) -> str:
        raw_status = self.coordinator.data.get("status", "unknown")
        return STATUS_LABELS_DE.get(raw_status, raw_status)

    @property
    def _webhook_url(self) -> str:
        webhook_id = self._entry.data[CONF_WEBHOOK_ID]
        try:
            base_url = get_url(self.hass, allow_internal=False)
        except NoURLAvailableError:
            try:
                base_url = get_url(self.hass, allow_internal=True)
            except NoURLAvailableError:
                base_url = "<deine-ha-url>"
        return f"{base_url}/api/webhook/{webhook_id}"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        attrs: dict = {
            ATTR_RAW_STATUS: data.get("status"),
            "webhook_url": self._webhook_url,
        }

        if "customers_before" in data:
            attrs[ATTR_CUSTOMERS_BEFORE] = data["customers_before"]
        if "expected_arrival_start" in data:
            attrs[ATTR_EXPECTED_ARRIVAL_START] = data["expected_arrival_start"]
        if "expected_arrival_end" in data:
            attrs["expected_arrival_end"] = data["expected_arrival_end"]
        for key in ("deliveryDate", "plannedDeliveryDate", "deliverySlot", "timeSlot"):
            if key in data:
                attrs[key] = data[key]
        if "delivery_id" in data:
            attrs[ATTR_DELIVERY_ID] = data["delivery_id"]
        if data.get("tracking_id_received_at"):
            attrs[ATTR_RECEIVED_AT] = data["tracking_id_received_at"]

        return attrs
