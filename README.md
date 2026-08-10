# REWE Lieferung – Home Assistant Integration

Zeigt den aktuellen REWE-Lieferstatus (`wannkommt.rewe.de`) als Sensor in Home
Assistant an – ganz ohne Kalendereintrag oder Browser-Extension.

Die Integration bekommt ihre Daten per Webhook: Entweder die REWE-Tracking-SMS
(kurz vor der Lieferung) oder die Bestellbestätigungs-Mail (direkt nach der
Bestellung) wird an einen HA-Webhook weitergeleitet. Die Integration erkennt
selbst, was sie bekommen hat, extrahiert Tracking-ID bzw. Bestellnummer und
pollt den Lieferstatus – **langsam**, solange nur die Bestellung bekannt ist,
und **schnell**, sobald die Tracking-SMS eingetroffen ist.

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
3. Die per Benachrichtigung angezeigte Webhook-URL kopieren
   (`.../api/webhook/<webhook_id>`)

Danach gibt es zwei unabhängige Wege, wie die Integration an ihre Daten kommt.
**Empfohlen ist, beide gleichzeitig einzurichten**: Die Bestell-Mail (Weg 2)
sorgt dafür, dass die Integration schon ab dem Bestelltag im langsamen
Intervall pollt, die Tracking-SMS (Weg 1) schaltet dann am Liefertag aufs
schnelle Intervall um. Nutzt man nur einen der beiden Wege, verpasst man
entweder die frühe Vorwarnung (nur SMS) oder das feinere Live-Tracking kurz
vor der Lieferung (nur E-Mail).

### Weg 1: Tracking-SMS weiterleiten

Sobald REWE die Lieferung startet, kommt eine SMS mit einem
`wannkommt.rewe.de`-Link. Diese SMS an die Webhook-URL weiterleiten, sobald sie
ankommt, schaltet die Integration automatisch auf das schnelle Poll-Intervall.

**iOS – Kurzbefehl**
Der Kurzbefehl lässt sich aktuell nicht direkt zum Download teilen, daher hier
Screenshots der Einrichtung (Trigger + Aktion) zum Nachbauen:

Trigger = SMS enthält `wannkommt.rewe.de`,

<img width="300" alt="IMG_6280" src="https://github.com/user-attachments/assets/da573abd-ba05-41c3-9e5e-f87186f163a7" />

Aktion = HTTP POST mit dem SMS-Text an die Webhook-URL (die Webhook-URL aus
Schritt 3 der Einrichtung dabei in die Aktion eintragen).

<img width="300" alt="IMG_6281" src="https://github.com/user-attachments/assets/87a0aa0b-4106-403b-b537-eb1d78d6a7e8" />
<img width="300" alt="IMG_6279" src="https://github.com/user-attachments/assets/4ff111cb-4947-4094-8090-62eabd00fdd8" />



**Android (ungetestet)**
In einer SMS-Weiterleitungs-App (z. B. MacroDroid) hinterlegen: Trigger = SMS
enthält `wannkommt.rewe.de`, Aktion = HTTP POST mit dem SMS-Text an die
Webhook-URL.

### Weg 2: Bestell-Mail per Home Assistant IMAP weiterleiten

Damit die Integration schon direkt nach der Bestellung weiß, dass eine
Lieferung ansteht (und dann im langsamen Intervall pollt, bis die SMS kommt),
kann die Bestellbestätigungs-Mail von REWE über die eingebaute
**IMAP**-Integration von Home Assistant automatisch an den Webhook geschickt
werden – ganz ohne Handy-App.

1. **IMAP-Integration einrichten**
   Einstellungen → Geräte & Dienste → Integration hinzufügen → **IMAP**.
   Zugangsdaten des Mail-Postfachs eintragen (Server, Port, Benutzername,
   Passwort/App-Passwort, Ordner z. B. `INBOX`).

2. **Suche und Event-Vorlage konfigurieren**
   Beim Einrichten (oder später über die Optionen der IMAP-Integration)
   folgendes setzen:
   - **Suche**: kann breit bleiben (z. B. `UNSEEN` oder leer) – die
     eigentliche Filterung auf REWE-Mails übernimmt weiter unten die
     Automation über `event_data.sender`
   - **Zeichensatz**: `UTF-8`
   - **Eigene Event-Daten-Vorlage** ("Custom event data template"): hier den
     Text der Mail durchreichen, z. B.
     ```
     {{ subject }}\n{{ text }}
     ```
   Dadurch feuert die IMAP-Integration bei jeder passenden Mail ein Event
   `imap_content` mit Absender (`sender`) und Mailtext (`text`) in den
   Event-Daten.

3. **rest_command anlegen**
   In der `configuration.yaml`:
   ```yaml
   rest_command:
     rewe_mail_forward:
       url: "https://<deine-ha-url>/api/webhook/<webhook_id>"
       method: POST
       content_type: "text/plain"
       payload: "{{ text }}"
   ```
   `<webhook_id>` durch die eigene Webhook-URL aus Schritt 3 der Einrichtung
   ersetzen.

4. **Automation anlegen**
   Einstellungen → Automatisierungen → Neue Automatisierung → im YAML-Modus:
   ```yaml
   alias: REWE Lieferservice
   triggers:
     - trigger: event
       event_type: imap_content
       event_data:
         sender: reweshop@mailing.rewe.de
   conditions: []
   actions:
     - action: rest_command.rewe_mail_forward
       data:
         text: "{{ trigger.event.data.text }}"
   mode: single
   ```
   Die Filterung auf die passende Mail läuft hier direkt über `event_data.sender`
   – nur Events der IMAP-Integration, deren Absender `reweshop@mailing.rewe.de`
   entspricht, lösen die Automation aus. Eine zusätzliche `condition` ist damit
   nicht mehr nötig.

Nach Bestelleingang wird so automatisch die Bestellnummer erkannt und die
Integration pollt im langsamen Intervall, bis später die SMS (Weg 1) das
schnelle Intervall aktiviert.

## Poll-Intervalle anpassen

Über Einstellungen → Geräte & Dienste → REWE Lieferung → *Konfigurieren*
lassen sich zwei Intervalle einstellen:

- **Abfrageintervall**: aktiv, sobald die Tracking-SMS da war (Liefertag)
- **Langsames Abfrageintervall**: aktiv, solange nur die Bestell-Mail bekannt
  ist

Standard: 300 s (schnell) / 3600 s (langsam), Minimum jeweils 60 s.

## Entity

`sensor.rewe_lieferung_status` mit den Attributen:

- `raw_status` – Rohstatus von REWE
- `delivery_id` – erkannte Tracking-ID
- `tracking_id_received_at` – Zeitpunkt, zu dem die ID empfangen wurde
- `polling_quelle` – ob die letzte Aktualisierung von der SMS- oder
  E-Mail-Erkennung ausgelöst wurde
- `webhook_url` – die aktuelle Webhook-URL, zum Nachschlagen direkt in HA

Sobald die Lieferung abgeschlossen ist (`DELIVERED`/`CANCELLED`), wird die
gemerkte Tracking-ID automatisch verworfen und der Sensor zeigt wieder „Keine
Lieferung“.

Inspiriert von [toelke/rewe-lieferung-home-assistant](https://github.com/toelke/rewe-lieferung-home-assistant)
und [LinqLover/wannkommtrewe-calendar](https://github.com/LinqLover/wannkommtrewe-calendar).
