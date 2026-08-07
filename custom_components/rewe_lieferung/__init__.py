"""REWE Lieferung Integration."""
from __future__ import annotations

import logging

from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url

from .const import CONF_WEBHOOK_ID, DOMAIN
from .coordinator import ReweLieferungCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Config Entry einrichten."""
    coordinator = ReweLieferungCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    webhook_id = entry.data[CONF_WEBHOOK_ID]

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request
    ) -> web.Response:
        """Nimmt die weitergeleitete SMS entgegen und sucht die Tracking-ID."""
        try:
            text = await request.text()
        except Exception:  # noqa: BLE001
            text = ""

        found = coordinator.handle_incoming_text(text)
        return web.json_response({"tracking_id_found": found})

    webhook.async_register(
        hass, DOMAIN, "REWE Lieferung", webhook_id, handle_webhook
    )

    try:
        webhook_url = f"{get_url(hass, allow_internal=False)}/api/webhook/{webhook_id}"
    except Exception:  # noqa: BLE001
        webhook_url = f"<deine-ha-url>/api/webhook/{webhook_id}"

    _LOGGER.info("REWE Lieferung Webhook-URL: %s", webhook_url)
    hass.components.persistent_notification.async_create(
        (
            "Leite REWE-Liefer-SMS an folgende URL weiter (z.B. via MacroDroid):\n\n"
            f"`{webhook_url}`"
        ),
        title="REWE Lieferung: Webhook einrichten",
        notification_id=f"{DOMAIN}_{entry.entry_id}_webhook",
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(lambda: webhook.async_unregister(hass, webhook_id))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config Entry entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bei geänderten Optionen (z.B. Abfrageintervall) neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)
