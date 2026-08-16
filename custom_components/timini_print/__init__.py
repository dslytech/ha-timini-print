"""The TiMini Print integration.

Talks to the companion **TiMini Print Server** Home Assistant add-on
over its small HTTP wrapper API - never directly to Bluetooth or to
TiMini-Print's own CLI. You must have that add-on installed and running
first (see its own README for setup, including picking a working
Bluetooth adapter for your printer).
"""
from __future__ import annotations

import base64
import logging
import os

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .client import TiminiPrintError, list_models, print_image, print_text, scan_printers
from .const import (
    ALLOWED_IMAGE_EXTENSIONS,
    ATTR_DARKNESS,
    ATTR_FILE_PATH,
    ATTR_FILENAME,
    ATTR_IMAGE_B64,
    ATTR_MESSAGE,
    ATTR_PRINTER,
    ATTR_PRINTER_MODEL,
    ATTR_TEXT_COLUMNS,
    DOMAIN,
    SERVICE_PRINT_IMAGE,
    SERVICE_PRINT_IMAGE_DATA,
    SERVICE_PRINT_TEXT,
    SERVICE_SCAN,
    SERVICE_LIST_MODELS,
    SERVICE_LIST_HA_BLUETOOTH_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

# Bump this whenever timini-print-card.js changes, so browsers that
# cached an older copy (by URL) are forced to fetch the new one
# instead of silently keeping stale JS after an update.
CARD_VERSION = "14"

CARD_BASE_PATH = "/timini_print_frontend/timini-print-card.js"
CARD_URL_PATH = f"{CARD_BASE_PATH}?v={CARD_VERSION}"
WWW_DIR = os.path.join(os.path.dirname(__file__), "www")
CARD_FILE = os.path.join(WWW_DIR, "timini-print-card.js")

_DARKNESS_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=1, max=5))

PRINT_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_PRINTER): cv.string,
        vol.Optional(ATTR_TEXT_COLUMNS): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
        vol.Optional(ATTR_DARKNESS): _DARKNESS_SCHEMA,
        vol.Optional(ATTR_PRINTER_MODEL): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

PRINT_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_FILE_PATH): cv.string,
        vol.Optional(ATTR_PRINTER): cv.string,
        vol.Optional(ATTR_DARKNESS): _DARKNESS_SCHEMA,
        vol.Optional(ATTR_PRINTER_MODEL): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

PRINT_IMAGE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IMAGE_B64): cv.string,
        vol.Required(ATTR_FILENAME): cv.string,
        vol.Optional(ATTR_PRINTER): cv.string,
        vol.Optional(ATTR_DARKNESS): _DARKNESS_SCHEMA,
        vol.Optional(ATTR_PRINTER_MODEL): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)

SCAN_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)


def _pick_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("No TiMini Print add-on has been configured yet.")
    if entry_id:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
        raise HomeAssistantError(f"No TiMini Print config entry with id {entry_id}")
    return entries[0]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await _async_register_frontend_card(hass)

    async def handle_print_text(call: ServiceCall) -> None:
        entry_ = _pick_entry(hass, call.data.get("entry_id"))
        data = entry_.data

        def _do_print():
            return print_text(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
                text=call.data[ATTR_MESSAGE],
                printer=call.data.get(ATTR_PRINTER),
                text_columns=call.data.get(ATTR_TEXT_COLUMNS),
                darkness=call.data.get(ATTR_DARKNESS),
                printer_model=call.data.get(ATTR_PRINTER_MODEL),
            )

        try:
            await hass.async_add_executor_job(_do_print)
        except TiminiPrintError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN, SERVICE_PRINT_TEXT, handle_print_text, schema=PRINT_TEXT_SCHEMA
    )

    async def handle_print_image(call: ServiceCall) -> None:
        entry_ = _pick_entry(hass, call.data.get("entry_id"))
        data = entry_.data
        file_path = call.data[ATTR_FILE_PATH]

        if not hass.config.is_allowed_path(file_path):
            raise HomeAssistantError(
                f"'{file_path}' is not in an allowed directory for Home "
                "Assistant to read. Add its parent folder to "
                "'allowlist_external_dirs' in configuration.yaml, or use "
                "a path under /config or /media."
            )

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HomeAssistantError(
                f"Unsupported file extension '{ext}' - expected one of "
                f"{sorted(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        def _read_file() -> bytes:
            with open(file_path, "rb") as f:
                return f.read()

        try:
            image_bytes = await hass.async_add_executor_job(_read_file)
        except OSError as err:
            raise HomeAssistantError(f"Could not read '{file_path}': {err}") from err

        def _do_print():
            return print_image(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
                image_bytes=image_bytes,
                filename=os.path.basename(file_path),
                printer=call.data.get(ATTR_PRINTER),
                darkness=call.data.get(ATTR_DARKNESS),
                printer_model=call.data.get(ATTR_PRINTER_MODEL),
            )

        try:
            await hass.async_add_executor_job(_do_print)
        except TiminiPrintError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN, SERVICE_PRINT_IMAGE, handle_print_image, schema=PRINT_IMAGE_SCHEMA
    )

    async def handle_print_image_data(call: ServiceCall) -> None:
        entry_ = _pick_entry(hass, call.data.get("entry_id"))
        data = entry_.data
        filename = call.data[ATTR_FILENAME]
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HomeAssistantError(
                f"Unsupported file extension '{ext}' - expected one of "
                f"{sorted(ALLOWED_IMAGE_EXTENSIONS)}"
            )
        try:
            image_bytes = base64.b64decode(call.data[ATTR_IMAGE_B64], validate=True)
        except (ValueError, base64.binascii.Error) as err:    # type: ignore[attr-defined]
            raise HomeAssistantError(f"Invalid base64 image data: {err}") from err

        def _do_print():
            return print_image(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
                image_bytes=image_bytes,
                filename=filename,
                printer=call.data.get(ATTR_PRINTER),
                darkness=call.data.get(ATTR_DARKNESS),
                printer_model=call.data.get(ATTR_PRINTER_MODEL),
            )

        try:
            await hass.async_add_executor_job(_do_print)
        except TiminiPrintError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_PRINT_IMAGE_DATA,
        handle_print_image_data,
        schema=PRINT_IMAGE_DATA_SCHEMA,
    )

    async def handle_scan(call: ServiceCall) -> dict:
        entry_ = _pick_entry(hass, call.data.get("entry_id"))
        data = entry_.data

        def _do_scan():
            return scan_printers(host=data[CONF_HOST], port=data[CONF_PORT])

        try:
            printers = await hass.async_add_executor_job(_do_scan)
        except TiminiPrintError as err:
            raise HomeAssistantError(str(err)) from err
        return {"printers": printers}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN,
        handle_scan,
        schema=SCAN_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_list_models(call: ServiceCall) -> dict:
        entry_ = _pick_entry(hass, call.data.get("entry_id"))
        data = entry_.data

        def _do_list_models():
            return list_models(host=data[CONF_HOST], port=data[CONF_PORT])

        try:
            models = await hass.async_add_executor_job(_do_list_models)
        except TiminiPrintError as err:
            raise HomeAssistantError(str(err)) from err
        return {"models": models}

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_MODELS,
        handle_list_models,
        schema=SCAN_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_list_ha_bluetooth_devices(call: ServiceCall) -> dict:    # pylint: disable=unused-argument
        """Read whatever Bluetooth devices Home Assistant's own
        `bluetooth` integration has already (passively) discovered -
        no new scan is started, this just reads HA Core's existing
        cache. Sidesteps any contention over the physical adapter
        between HA's own Bluetooth integration and the add-on's own
        --scan, since nothing extra is requested from the hardware.
        Requires HA's `bluetooth` integration to be enabled.
        """
        try:
            from homeassistant.components import bluetooth    # pylint: disable=import-outside-toplevel
        except ImportError:
            return {"devices": [], "error": "Home Assistant's bluetooth component is not available."}

        try:
            infos = bluetooth.async_discovered_service_info(hass, connectable=False)
        except Exception as err:    # pylint: disable=broad-except
            return {"devices": [], "error": str(err)}

        devices = [
            {
                "address": info.address,
                "name": info.name or info.address,
                "rssi": info.rssi,
            }
            for info in infos
        ]
        return {"devices": devices}

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_HA_BLUETOOTH_DEVICES,
        handle_list_ha_bluetooth_devices,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )
    return True


SUPPORTED_LANGUAGES = ["en", "hu", "de", "pl"]


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Serve this integration's bundled Lovelace card (and its
    translation JSON files) and register the card so it's usable
    without the user manually adding a Lovelace resource. Only needs
    to run once, regardless of how many TiMini Print add-on
    connections are configured.

    Each file is registered individually (rather than pointing
    StaticPathConfig at the whole `www` directory) - directory-tree
    serving didn't reliably resolve nested paths like `lang/hu.json`
    in testing, while registering each exact file is proven to work.
    """
    meta = hass.data.setdefault(f"{DOMAIN}_frontend", {})
    if meta.get("registered"):
        return
    try:
        configs = [StaticPathConfig(CARD_BASE_PATH, CARD_FILE, False)]
        for lang in SUPPORTED_LANGUAGES:
            configs.append(
                StaticPathConfig(
                    f"/timini_print_frontend/lang/{lang}.json",
                    os.path.join(WWW_DIR, "lang", f"{lang}.json"),
                    False,
                )
            )
        await hass.http.async_register_static_paths(configs)
        add_extra_js_url(hass, CARD_URL_PATH)
        meta["registered"] = True
    except Exception as err:    # pylint: disable=broad-except
        # Don't block the rest of setup over the card - services still
        # work fine without it. If this fails (e.g. a Home Assistant
        # version with a different static-path API), the card can
        # still be added manually as a Lovelace resource pointing at
        # this same URL - see the integration's README.
        _LOGGER.warning(
            "Could not auto-register the TiMini Print Lovelace card: %s. "
            "You can still add it manually as a Lovelace resource: %s",
            err,
            CARD_URL_PATH,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_PRINT_TEXT)
        hass.services.async_remove(DOMAIN, SERVICE_PRINT_IMAGE)
        hass.services.async_remove(DOMAIN, SERVICE_PRINT_IMAGE_DATA)
        hass.services.async_remove(DOMAIN, SERVICE_SCAN)
        hass.services.async_remove(DOMAIN, SERVICE_LIST_MODELS)
        hass.services.async_remove(DOMAIN, SERVICE_LIST_HA_BLUETOOTH_DEVICES)
    return True
