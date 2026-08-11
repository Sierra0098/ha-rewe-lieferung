"""Konstanten für die REWE Lieferung Integration."""
from datetime import timedelta

DOMAIN = "rewe_lieferung"

CONF_ZIP_CODE = "zip_code"
CONF_WEBHOOK_ID = "webhook_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SLOW_SCAN_INTERVAL = "slow_scan_interval"

DEFAULT_SCAN_INTERVAL = 300  # Sekunden, aktiv sobald die SMS (Liefertag) da war
DEFAULT_SLOW_SCAN_INTERVAL = 3600  # Sekunden, aktiv wenn nur die Bestell-Mail da ist
MIN_SCAN_INTERVAL = 60

# Sicherheitsnetz: falls REWE nie einen finalen Status (DELIVERED/CANCELLED)
# meldet, verwerfen wir die ID trotzdem irgendwann, um nicht endlos eine tote
# Bestellung abzufragen. Der eigentliche Reset passiert aber status-basiert.
DELIVERY_ID_TTL = timedelta(hours=48)

STATUS_NO_DELIVERY = "NO_DELIVERY"

# Status-Codes, bei denen die Bestellung abgeschlossen ist. Danach wird die
# gemerkte Tracking-ID verworfen, damit der Sensor wieder "Keine Lieferung"
# zeigt statt den alten Endstatus stehen zu lassen.
TERMINAL_STATUSES = {"DELIVERED", "CANCELLED"}

STATUS_LABELS_DE = {
    "CREATED": "Bestellt",
    "NOT_FIXED": "Wird gepackt",
    "COMMISSION_STARTED": "Wird gepackt",
    "LOADED": "Eingepackt",
    "COMMISSIONED": "Eingepackt",
    "STARTED": "Unterwegs",
    "POSTPONED": "Unterwegs",
    "APPROACHING_POSTPONED": "Gleich da",
    "APPROACHING": "Gleich da",
    "ARRIVED": "Am Haus angekommen",
    "DELIVERED": "Geliefert",
    "CANCELLED": "Storniert",
    STATUS_NO_DELIVERY: "Keine Lieferung",
}

# Rohfeld-Namen aus der wannkommt.rewe.de-Antwort. Bestätigt durch echte
# Debug-Log-Mitschnitte (siehe README) – KEINE Vermutungen mehr.
FIELD_STATUS = "status"
FIELD_SHOP_ORDER_ID = "shopOrderId"
FIELD_ORDER_VALUE = "orderValue"
FIELD_ORDER_CREATED_TIMESTAMP = "orderCreatedTimestamp"
FIELD_TIME_SLOT_START = "timeSlotStart"
FIELD_TIME_SLOT_END = "timeSlotEnd"
FIELD_EXPECTED_ARRIVAL_START = "expectedArrivalIntervalStart"
FIELD_EXPECTED_ARRIVAL_END = "expectedArrivalIntervalEnd"
FIELD_CANCEL_REASON = "cancelReason"
FIELD_DELAY_CLASS = "delayClass"
FIELD_ETA_ROUNDED = "etaRounded"
FIELD_STATUS_TIMESTAMP = "statusTimestamp"
FIELD_CUSTOMERS_BEFORE_ME = "customersBeforeMe"
FIELD_ORDER_STATUS_LIST = "orderStatusList"
FIELD_MAP_DETAILS = "mapDetails"
FIELD_DRIVER_LOCATION = "driverLocation"
FIELD_ADDRESS = "address"  # wird bewusst NICHT ausgelesen (personenbezogen)

REWE_API_URL = "https://wannkommt.rewe.de/api/delivery/{delivery_id}"

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
