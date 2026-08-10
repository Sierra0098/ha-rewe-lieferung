# REWE Lieferung – Home Assistant Integration

Zeigt den aktuellen REWE-Lieferstatus (`wannkommt.rewe.de`) als Sensor in Home
Assistant an – ganz ohne Kalendereintrag oder Browser-Extension.

Die REWE-Tracking-SMS wird per Handy-Automatisierung (z.B. MacroDroid) an
einen HA-Webhook weitergeleitet. Die Integration extrahiert die Tracking-ID
selbst und pollt den Lieferstatus.

## Installation über HACS

1. HACS → Integrationen → Menü (⋮) oben rechts → *Benutzerdefinierte
   Repositories*
2. Repository-URL eintragen, Kategorie **Integration** wählen, hinzufügen
3. "REWE Lieferung" in HACS suchen und installieren
4. Home Assistant neu starten

## Einrichtung

1. Einstellungen → Geräte & Dienste → Integration hinzufügen → **REWE
   Lieferung**
2. Postleitzahl eingeben
3. Die angezeigte Webhook-URL in einer SMS-Weiterleitungs-App (z.B.
   MacroDroid) hinterlegen: Trigger = SMS enthält `wannkommt.rewe.de`,
   Aktion = HTTP POST mit dem SMS-Text an die Webhook-URL

## Entity

`sensor.rewe_lieferung_status` mit Attributen `raw_status`,
`customers_before`, `expected_arrival_start`, `delivery_id`,
`tracking_id_received_at`.

Inspiriert von [toelke/rewe-lieferung-home-assistant](https://github.com/toelke/rewe-lieferung-home-assistant)
und [LinqLover/wannkommtrewe-calendar](https://github.com/LinqLover/wannkommtrewe-calendar).
