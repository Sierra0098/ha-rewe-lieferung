"""Sensor-Plattform für die REWE Lieferung Integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_WEBHOOK_ID, DOMAIN, STATUS_LABELS_DE
from .coordinator import ReweLieferungCoordinator


def _parse_dt(value: str | None) -> datetime | None:
    """Wandelt einen ISO-Zeitstempel aus der REWE-API in ein datetime um."""
    if not value:
        return None
    return dt_util.parse_datetime(value)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ReweLieferungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ReweLieferungStatusSensor(coordinator, entry),
            ReweLieferungOrderNumberSensor(coordinator, entry),
            ReweLieferungOrderValueSensor(coordinator, entry),
            ReweLieferungOrderCreatedSensor(coordinator, entry),
            ReweLieferungTimeSlotStartSensor(coordinator, entry),
            ReweLieferungTimeSlotEndSensor(coordinator, entry),
            ReweLieferungExpectedArrivalStartSensor(coordinator, entry),
            ReweLieferungExpectedArrivalEndSensor(coordinator, entry),
            ReweLieferungStatusTimestampSensor(coordinator, entry),
            ReweLieferungCustomersBeforeMeSensor(coordinator, entry),
            ReweLieferungCancelReasonSensor(coordinator, entry),
            ReweLieferungDelayClassSensor(coordinator, entry),
            ReweLieferungEtaRoundedSensor(coordinator, entry),
            ReweLieferungDriverLatitudeSensor(coordinator, entry),
            ReweLieferungDriverLongitudeSensor(coordinator, entry),
            ReweLieferungStatusHistorySensor(coordinator, entry),
        ]
    )


class ReweLieferungBaseSensor(CoordinatorEntity[ReweLieferungCoordinator], SensorEntity):
    """Basisklasse mit gemeinsamem Geräte-Kontext für alle Sensoren."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ReweLieferungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="REWE Lieferung",
            manufacturer="REWE",
            model="Lieferservice Tracking",
        )

    @property
    def _key(self) -> str:
        """Eindeutiger Teil-Key für unique_id, aus dem Klassennamen abgeleitet."""
        raise NotImplementedError


class ReweLieferungStatusSensor(ReweLieferungBaseSensor):
    """Zeigt den aktuellen REWE-Lieferstatus."""

    _attr_name = "Status"
    _attr_icon = "mdi:truck-delivery"
    _key = "status"

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
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "raw_status": data.get("status"),
            "webhook_url": self._webhook_url,
            "delivery_id": data.get("delivery_id"),
            "polling_quelle": data.get("source"),
            "tracking_id_received_at": data.get("tracking_id_received_at"),
        }


class ReweLieferungOrderNumberSensor(ReweLieferungBaseSensor):
    """shopOrderId aus der REWE-Antwort."""

    _attr_name = "Bestellnummer"
    _attr_icon = "mdi:pound-box-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "shop_order_id"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("shop_order_id")


class ReweLieferungOrderValueSensor(ReweLieferungBaseSensor):
    """orderValue (Cent) aus der REWE-Antwort, als Euro-Betrag."""

    _attr_name = "Bestellwert"
    _attr_icon = "mdi:currency-eur"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "order_value"

    @property
    def native_value(self) -> float | None:
        cents = self.coordinator.data.get("order_value")
        return None if cents is None else round(cents / 100, 2)


class ReweLieferungOrderCreatedSensor(ReweLieferungBaseSensor):
    """orderCreatedTimestamp aus der REWE-Antwort."""

    _attr_name = "Bestellt am"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "order_created_at"

    @property
    def native_value(self) -> datetime | None:
        return _parse_dt(self.coordinator.data.get("order_created_at"))


class ReweLieferungTimeSlotStartSensor(ReweLieferungBaseSensor):
    """timeSlotStart: gebuchtes Lieferfenster, Beginn."""

    _attr_name = "Lieferfenster Start"
    _attr_icon = "mdi:clock-start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _key = "time_slot_start"

    @property
    def native_value(self) -> datetime | None:
        return _parse_dt(self.coordinator.data.get("time_slot_start"))


class ReweLieferungTimeSlotEndSensor(ReweLieferungBaseSensor):
    """timeSlotEnd: gebuchtes Lieferfenster, Ende."""

    _attr_name = "Lieferfenster Ende"
    _attr_icon = "mdi:clock-end"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _key = "time_slot_end"

    @property
    def native_value(self) -> datetime | None:
        return _parse_dt(self.coordinator.data.get("time_slot_end"))


class ReweLieferungExpectedArrivalStartSensor(ReweLieferungBaseSensor):
    """expectedArrivalIntervalStart: engeres, live aktualisiertes Ankunftsfenster."""

    _attr_name = "Erwartete Ankunft Start"
    _attr_icon = "mdi:clock-fast"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _key = "expected_arrival_start"

    @property
    def native_value(self) -> datetime | None:
        return _parse_dt(self.coordinator.data.get("expected_arrival_start"))


class ReweLieferungExpectedArrivalEndSensor(ReweLieferungBaseSensor):
    """expectedArrivalIntervalEnd: engeres, live aktualisiertes Ankunftsfenster."""

    _attr_name = "Erwartete Ankunft Ende"
    _attr_icon = "mdi:clock-fast"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _key = "expected_arrival_end"

    @property
    def native_value(self) -> datetime | None:
        return _parse_dt(self.coordinator.data.get("expected_arrival_end"))


class ReweLieferungStatusTimestampSensor(ReweLieferungBaseSensor):
    """statusTimestamp: Zeitpunkt des letzten Statuswechsels (erst ab ARRIVED/DELIVERED gefüllt)."""

    _attr_name = "Letzter Statuswechsel"
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "status_timestamp"

    @property
    def native_value(self) -> datetime | None:
        return _parse_dt(self.coordinator.data.get("status_timestamp"))


class ReweLieferungCustomersBeforeMeSensor(ReweLieferungBaseSensor):
    """customersBeforeMe: Anzahl Kund:innen vor dieser Lieferung in der Route.

    Hinweis: REWE liefert nach DELIVERED teils negative Werte - wirkt wie ein
    Zähler-Bug auf REWE-Seite, wird hier unverändert durchgereicht.
    """

    _attr_name = "Kund:innen vor mir"
    _attr_icon = "mdi:account-multiple-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _key = "customers_before_me"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("customers_before_me")


class ReweLieferungCancelReasonSensor(ReweLieferungBaseSensor):
    """cancelReason: bislang in allen beobachteten Antworten null."""

    _attr_name = "Stornierungsgrund"
    _attr_icon = "mdi:cancel"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "cancel_reason"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("cancel_reason")


class ReweLieferungDelayClassSensor(ReweLieferungBaseSensor):
    """delayClass: bislang in allen beobachteten Antworten null."""

    _attr_name = "Verzögerungsklasse"
    _attr_icon = "mdi:clock-alert-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "delay_class"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("delay_class")


class ReweLieferungEtaRoundedSensor(ReweLieferungBaseSensor):
    """etaRounded: bislang in allen beobachteten Antworten null, Format unbekannt."""

    _attr_name = "ETA gerundet"
    _attr_icon = "mdi:timer-sand"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "eta_rounded"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("eta_rounded")


class ReweLieferungDriverLatitudeSensor(ReweLieferungBaseSensor):
    """mapDetails.driverLocation.latitude, nur ab APPROACHING gefüllt."""

    _attr_name = "Fahrer Breitengrad"
    _attr_icon = "mdi:map-marker"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "driver_latitude"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("driver_latitude")


class ReweLieferungDriverLongitudeSensor(ReweLieferungBaseSensor):
    """mapDetails.driverLocation.longitude, nur ab APPROACHING gefüllt."""

    _attr_name = "Fahrer Längengrad"
    _attr_icon = "mdi:map-marker"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "driver_longitude"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("driver_longitude")


class ReweLieferungStatusHistorySensor(ReweLieferungBaseSensor):
    """orderStatusList: Verlauf aller Statuswechsel, neuester Eintrag zuerst.

    Der State ist die Anzahl der bisherigen Statuswechsel, der komplette
    Verlauf (inkl. Zeitstempel je Status) steht als Attribut zur Verfügung.
    """

    _attr_name = "Statusverlauf"
    _attr_icon = "mdi:history"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _key = "order_status_list"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("order_status_list") or [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"verlauf": self.coordinator.data.get("order_status_list") or []}
