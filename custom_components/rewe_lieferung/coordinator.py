"""Coordinator für die REWE Lieferung Integration."""
from __future__ import annotations

import logging
import re
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLOW_SCAN_INTERVAL,
    CONF_ZIP_CODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLOW_SCAN_INTERVAL,
    DELIVERY_ID_TTL,
    DOMAIN,
    FIELD_CANCEL_REASON,
    FIELD_CUSTOMERS_BEFORE_ME,
    FIELD_DELAY_CLASS,
    FIELD_DRIVER_LOCATION,
    FIELD_ETA_ROUNDED,
    FIELD_EXPECTED_ARRIVAL_END,
    FIELD_EXPECTED_ARRIVAL_START,
    FIELD_MAP_DETAILS,
    FIELD_ORDER_CREATED_TIMESTAMP,
    FIELD_ORDER_STATUS_LIST,
    FIELD_ORDER_VALUE,
    FIELD_SHOP_ORDER_ID,
    FIELD_STATUS,
    FIELD_STATUS_TIMESTAMP,
    FIELD_TIME_SLOT_END,
    FIELD_TIME_SLOT_START,
    REWE_API_URL,
    STATUS_NO_DELIVERY,
    TERMINAL_STATUSES,
)

_LOGGER = logging.getLogger(__name__)

TRACKING_ID_RE = re.compile(r"wannkommt\.rewe\.de/([A-Za-z0-9\-_]+)")
ORDER_NUMBER_RE = re.compile(
    r"(?:Bestellnummer|Bestell-?Nr\.?|Auftragsnummer|Order-?Nr\.?|Order[- ]?ID)"
    r"[:\s]+([A-Za-z0-9\-]+)",
    re.IGNORECASE,
)

SOURCE_SMS = "sms"
SOURCE_EMAIL = "email"


class ReweLieferungCoordinator(DataUpdateCoordinator[dict]):
    """Fragt den REWE-Lieferstatus für die zuletzt per Webhook empfangene
    Tracking-ID ab. Pollt schnell am Liefertag (Signal: SMS empfangen) und
    langsam davor (Signal: nur die Bestell-Mail empfangen)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._delivery_id: str | None = None
        self._received_at = None
        self._source: str | None = None

        self._fast_interval = timedelta(
            seconds=entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        self._slow_interval = timedelta(
            seconds=entry.options.get(
                CONF_SLOW_SCAN_INTERVAL,
                entry.data.get(CONF_SLOW_SCAN_INTERVAL, DEFAULT_SLOW_SCAN_INTERVAL),
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._slow_interval,
        )

    @property
    def zip_code(self) -> str:
        return self.entry.data[CONF_ZIP_CODE]

    def _apply_interval_for_source(self) -> None:
        """Stellt das Poll-Intervall passend zur zuletzt bekannten Quelle ein."""
        new_interval = (
            self._fast_interval if self._source == SOURCE_SMS else self._slow_interval
        )
        if new_interval != self.update_interval:
            _LOGGER.debug(
                "Poll-Intervall auf %s gesetzt (Quelle: %s)", new_interval, self._source
            )
        self.update_interval = new_interval

    def handle_incoming_text(self, text: str) -> bool:
        """Wird vom Webhook mit rohem Text aufgerufen (SMS oder E-Mail).

        Sucht zuerst nach einem vollständigen wannkommt.rewe.de-Link
        (SMS, kommt kurz vor der Lieferung -> schnelles Polling). Falls
        keiner gefunden wird, versucht es alternativ, eine Bestellnummer
        aus einer Bestellbestätigungs-Mail zu extrahieren (kommt direkt
        nach der Bestellung -> langsames Polling, da Liefertag noch fern).
        Gibt True zurück, wenn eine ID gefunden wurde.
        """
        match = TRACKING_ID_RE.search(text)
        if match:
            new_id = match.group(1)
            source = SOURCE_SMS
            source_label = "SMS-Link"
        else:
            match = ORDER_NUMBER_RE.search(text)
            if not match:
                _LOGGER.debug("Keine REWE-Tracking-ID/Bestellnummer im Text gefunden")
                return False
            new_id = match.group(1)
            source = SOURCE_EMAIL
            source_label = "Bestellnummer (E-Mail)"

        self._delivery_id = new_id
        self._received_at = dt_util.utcnow()
        self._source = source
        self._apply_interval_for_source()
        _LOGGER.info("Neue REWE-Tracking-ID empfangen (%s): %s", source_label, new_id)
        self.hass.async_create_task(self.async_request_refresh())
        return True

    def _delivery_id_is_valid(self) -> bool:
        if self._delivery_id is None or self._received_at is None:
            return False
        return dt_util.utcnow() - self._received_at < DELIVERY_ID_TTL

    async def _async_update_data(self) -> dict:
        if not self._delivery_id_is_valid():
            self._source = None
            self._apply_interval_for_source()
            return {"status": STATUS_NO_DELIVERY}
        return await self._fetch_delivery_status(self._delivery_id)

    async def _fetch_delivery_status(self, delivery_id: str) -> dict:
        session = async_get_clientsession(self.hass)
        url = REWE_API_URL.format(delivery_id=delivery_id)
        try:
            async with session.post(
                url,
                headers={"Accept": "application/json, text/plain, */*"},
                json={"zipCode": self.zip_code},
            ) as response:
                response.raise_for_status()
                delivery = await response.json(content_type=None)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"REWE-Status konnte nicht geladen werden: {err}") from err

        # ACHTUNG: delivery["address"] enthält Name, Straße, PLZ und
        # Koordinaten der Lieferadresse. Wird absichtlich NICHT ausgelesen
        # und landet dadurch nicht in Entitäten/Attributen - taucht aber
        # weiterhin in dieser Debug-Logzeile auf (siehe README, Datenschutz-
        # Hinweis).
        _LOGGER.debug("REWE Rohantwort für %s: %s", delivery_id, delivery)

        result: dict = {
            "delivery_id": delivery_id,
            "tracking_id_received_at": self._received_at.isoformat()
            if self._received_at
            else None,
            "source": self._source,
        }

        order_status_list = delivery.get(FIELD_ORDER_STATUS_LIST) or []
        result["status"] = (
            order_status_list[0][FIELD_STATUS]
            if order_status_list
            else delivery.get(FIELD_STATUS, STATUS_NO_DELIVERY)
        )
        result["order_status_list"] = order_status_list

        result["shop_order_id"] = delivery.get(FIELD_SHOP_ORDER_ID)
        result["order_value"] = delivery.get(FIELD_ORDER_VALUE)
        result["order_created_at"] = delivery.get(FIELD_ORDER_CREATED_TIMESTAMP)
        result["time_slot_start"] = delivery.get(FIELD_TIME_SLOT_START)
        result["time_slot_end"] = delivery.get(FIELD_TIME_SLOT_END)
        result["expected_arrival_start"] = delivery.get(FIELD_EXPECTED_ARRIVAL_START)
        result["expected_arrival_end"] = delivery.get(FIELD_EXPECTED_ARRIVAL_END)
        result["cancel_reason"] = delivery.get(FIELD_CANCEL_REASON)
        result["delay_class"] = delivery.get(FIELD_DELAY_CLASS)
        result["eta_rounded"] = delivery.get(FIELD_ETA_ROUNDED)
        result["status_timestamp"] = delivery.get(FIELD_STATUS_TIMESTAMP)
        result["customers_before_me"] = delivery.get(FIELD_CUSTOMERS_BEFORE_ME)

        map_details = delivery.get(FIELD_MAP_DETAILS) or {}
        driver_location = map_details.get(FIELD_DRIVER_LOCATION) or {}
        result["driver_latitude"] = driver_location.get("latitude")
        result["driver_longitude"] = driver_location.get("longitude")

        if result["status"] in TERMINAL_STATUSES:
            _LOGGER.info(
                "Lieferung %s abgeschlossen (%s), Tracking-ID wird zurückgesetzt",
                delivery_id,
                result["status"],
            )
            self._delivery_id = None
            self._received_at = None
            self._source = None
            self._apply_interval_for_source()

        return result
