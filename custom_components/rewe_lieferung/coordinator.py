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
    CONF_ZIP_CODE,
    DEFAULT_SCAN_INTERVAL,
    DELIVERY_ID_TTL,
    DOMAIN,
    REWE_API_URL,
    STATUS_NO_DELIVERY,
)

_LOGGER = logging.getLogger(__name__)

TRACKING_ID_RE = re.compile(r"wannkommt\.rewe\.de/([A-Za-z0-9\-_]+)")
ORDER_NUMBER_RE = re.compile(
    r"(?:Bestellnummer|Bestell-?Nr\.?|Auftragsnummer|Order-?Nr\.?|Order[- ]?ID)"
    r"[:\s]+([A-Za-z0-9\-]+)",
    re.IGNORECASE,
)


class ReweLieferungCoordinator(DataUpdateCoordinator[dict]):
    """Fragt den REWE-Lieferstatus für die zuletzt per Webhook empfangene
    Tracking-ID ab."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._delivery_id: str | None = None
        self._received_at = None

        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    @property
    def zip_code(self) -> str:
        return self.entry.data[CONF_ZIP_CODE]

    def handle_incoming_text(self, text: str) -> bool:
        """Wird vom Webhook mit rohem Text aufgerufen (SMS oder E-Mail).

        Sucht zuerst nach einem vollständigen wannkommt.rewe.de-Link
        (z.B. aus der SMS). Falls keiner gefunden wird, versucht es
        alternativ, eine Bestellnummer aus einer Bestellbestätigungs-Mail
        zu extrahieren, die denselben Zweck erfüllt.
        Gibt True zurück, wenn eine ID gefunden wurde.
        """
        match = TRACKING_ID_RE.search(text)
        if match:
            new_id = match.group(1)
            source = "SMS-Link"
        else:
            match = ORDER_NUMBER_RE.search(text)
            if not match:
                _LOGGER.debug("Keine REWE-Tracking-ID/Bestellnummer im Text gefunden")
                return False
            new_id = match.group(1)
            source = "Bestellnummer (E-Mail)"

        self._delivery_id = new_id
        self._received_at = dt_util.utcnow()
        _LOGGER.info("Neue REWE-Tracking-ID empfangen (%s): %s", source, new_id)
        self.hass.async_create_task(self.async_request_refresh())
        return True

    def _delivery_id_is_valid(self) -> bool:
        if self._delivery_id is None or self._received_at is None:
            return False
        return dt_util.utcnow() - self._received_at < DELIVERY_ID_TTL

    async def _async_update_data(self) -> dict:
        if not self._delivery_id_is_valid():
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

        _LOGGER.debug("REWE Rohantwort für %s: %s", delivery_id, delivery)

        result: dict = {
            "delivery_id": delivery_id,
            "tracking_id_received_at": self._received_at.isoformat()
            if self._received_at
            else None,
        }

        order_status_list = delivery.get("orderStatusList") or []
        result["status"] = (
            order_status_list[0]["status"] if order_status_list else STATUS_NO_DELIVERY
        )

        if delivery.get("customersBeforeMe") is not None:
            result["customers_before"] = delivery["customersBeforeMe"]

        if delivery.get("expectedArrivalIntervalStart"):
            result["expected_arrival_start"] = delivery["expectedArrivalIntervalStart"]

        if delivery.get("expectedArrivalIntervalEnd"):
            result["expected_arrival_end"] = delivery["expectedArrivalIntervalEnd"]

        # Undokumentierte Felder: falls REWE ein geplantes Lieferdatum/-fenster
        # unter einem dieser Namen mitliefert, nehmen wir es automatisch mit.
        for key in ("deliveryDate", "plannedDeliveryDate", "deliverySlot", "timeSlot"):
            if delivery.get(key):
                result[key] = delivery[key]

        return result
