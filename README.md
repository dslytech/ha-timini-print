<p align="center">
  <img src="custom_components/timini_print/brand/logo.png" alt="TiMini Print logo" width="180">
</p>

# TiMini Print for Home Assistant

A HACS-installable integration for the companion **TiMini Print Server**
add-on (wraps [TiMini-Print](https://github.com/Dejniel/TiMini-Print)'s
CLI).

> **This integration does nothing on its own.** It's a thin client for
> the separate **TiMini Print Server** Home Assistant add-on, which is
> what actually talks to Bluetooth and the printer. You need both
> installed - this integration alone, without the add-on running,
> can't print anything; every service call just fails with a
> "could not reach the add-on" error. Install and confirm the add-on
> works on its own first (via its own web UI at `http://<host>:8096/`)
> before setting up this integration.

## Requirements

- The **TiMini Print Server** add-on already installed, running, and
  confirmed working via its own web UI (`http://<host>:8096/`) - scan
  and print a test message there first. This integration is useless
  without it.

## Installation

Same as any custom HACS repository: HACS → Integrations → "..." →
Custom repositories → add this repo's URL as an Integration, install,
restart Home Assistant. Or copy `custom_components/timini_print` into
your `config/custom_components/` folder manually.

## Setup

Settings → Devices & Services → Add Integration → "TiMini Print".
Enter the host/port of the add-on (same IP as your Home Assistant
instance, port `8096` by default). This step only runs a **scan** to
confirm the add-on is reachable - it never prints anything, so setup
never wastes paper.

## Usage

### Lovelace card (recommended - no helpers needed)

This integration bundles its own dashboard card, auto-registered as a
frontend resource - no manual "Add Resource" step needed in most
cases. On your dashboard: Edit Dashboard → Add Card → search for
**"TiMini Print"** in the card picker (or add a Manual card with
`type: custom:timini-print-card`). It gives you a text box + a
"Characters per line" size control + print darkness + a printer picker
(with a **Scan** button, same as the add-on's own web UI), and a file
picker for images/PDFs, all in one card - no helpers or scripts to set
up.

The card's own UI text defaults to **English** regardless of your Home
Assistant language setting. Hungarian, German, and Polish are also
included - set `language` in the card's own config to pick one:

```yaml
type: custom:timini-print-card
title: TiMini Print
language: hu   # or: en, de, pl
```

Anything not (yet) translated falls back to English automatically.
Translations live as plain JSON files under this integration's
`www/lang/` folder (`en.json`, `hu.json`, `de.json`, `pl.json`) - copy
one and add a new `language: xx` entry to contribute another.

If the card doesn't show up in the picker (e.g. a Home Assistant
version where the auto-registration didn't work, or nothing showed up
in the log either way), add it manually - this always works
regardless of why the automatic step didn't fire:

1. First, confirm the card file itself is actually being served: open
   `http://<your-home-assistant-host>:8123/timini_print_frontend/timini-print-card.js`
   directly in a browser tab. You should see JavaScript source code
   (starting with a comment block, then `const EMBEDDED_EN_FALLBACK =
   {...`). If you get a 404 instead, the integration's files weren't
   copied correctly - re-check that
   `custom_components/timini_print/www/timini-print-card.js` exists on
   your Home Assistant instance, then restart Home Assistant.
2. If step 1 showed the JavaScript correctly, go to: Settings →
   Dashboards → (⋮ menu, top right) → **Resources** → **+ Add Resource**.
3. URL: `/timini_print_frontend/timini-print-card.js`
4. Resource type: **JavaScript Module**
5. Save, then hard-refresh your browser (Ctrl+Shift+R / Cmd+Shift+R).
6. Add the card again: Edit Dashboard → Add Card → search **"TiMini
   Print"**, or add a Manual card with:
   ```yaml
   type: custom:timini-print-card
   title: TiMini Print
   ```

### Card seems to ignore a setting after an update

Browsers cache JavaScript files by URL. When this integration
auto-registers the card, it appends a version number to the URL
(`...timini-print-card.js?v=N`) that changes whenever the card itself
changes, specifically so browsers fetch the new version instead of
silently reusing an old cached copy after you update. If you added the
resource **manually** (the fallback above), that version number isn't
included, so after a future update you may need to hard-refresh
(Ctrl+Shift+R) and/or remove and re-add the manual resource to pick up
changes to the card. The `lang/*.json` translation files aren't
versioned this way (fetched fresh each time the card renders), so
editing a translation doesn't need any of this.

### Services (for automations, scripts, or your own card)

```yaml
service: timini_print.print_text
data:
  message: "Motion detected in the garage!"
```

If you have more than one supported printer nearby, override which one
to use:

```yaml
service: timini_print.print_text
data:
  message: "Hello from Home Assistant"
  printer: "TD-11308-ECF8"
  text_columns: 20
  darkness: 4
```

`text_columns` controls the printed text size - fewer columns means
bigger letters, more means smaller (matches the "Characters per line"
setting in TiMini-Print's own Android app). `darkness` (1-5) controls
the printer's thermal intensity. Both are optional; leave either out
for TiMini-Print's own defaults. See the add-on's own README ("Text
size and print darkness: native controls, not a workaround") for the
full story of how these were found.

(Use the same name/address a scan shows, on the add-on's own web UI or
via `timini_print`'s add-on `/scan` endpoint.)

### Printing an image or PDF

```yaml
service: timini_print.print_image
data:
  file_path: "/config/www/snapshot.jpg"
  printer: "TD-11308-ECF8"
  darkness: 4
```

`file_path` must point to a `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, or
`.pdf` file that Home Assistant is allowed to read - by default this
means under `/config` or `/media`; for other locations add the folder
to `allowlist_external_dirs` in `configuration.yaml` first. `darkness`
(1-5, optional) works the same as for `print_text`.

There's also `timini_print.print_image_data`, which takes base64 image
data directly instead of a file path - this is what the bundled
Lovelace card's file-upload button uses internally, so you generally
won't need to call it by hand unless building your own card/script.

## Status / disclaimer

**Confirmed working** end-to-end (services + bundled Lovelace card) on
a Home Assistant instance controlling a TiMini Print Server add-on
running on a **Raspberry Pi 4**, printing to a **TD-11308** cat-printer
clone. See the add-on's own README for exactly which hardware has been
tested on the Bluetooth/printing side - this integration itself only
talks HTTP to that add-on, so it doesn't depend on your Home Assistant
host's own hardware at all (Home Assistant and the add-on can even run
on different machines, as long as they can reach each other over the
network).

## Credits

This integration only talks to the companion **TiMini Print Server**
add-on over HTTP - it contains none of
[TiMini-Print](https://github.com/Dejniel/TiMini-Print)'s own code.
All credit for actually talking to the printer goes to
[Dejniel](https://github.com/Dejniel)'s TiMini-Print project; this repo
is an independent Home Assistant integration built on top, not a fork.
