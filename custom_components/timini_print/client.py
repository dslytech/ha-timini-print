"""Minimal, dependency-free HTTP client for the TiMini Print Server
add-on's own wrapper API (see the add-on's wrapper.py / README):

    GET  /scan               -> {"returncode", "stdout", "stderr"}
    POST /print {"text", "printer"?} -> {"returncode", "stdout", "stderr"}

This talks to the add-on's wrapper, never to TiMini-Print's own CLI or
Bluetooth stack directly - the add-on is what actually shells out to
`timiniprint_command_line.py`.
"""
from __future__ import annotations

import http.client
import json
import socket
from dataclasses import dataclass


class TiminiPrintError(Exception):
    """Raised when the TiMini Print add-on can't be reached, or the
    underlying CLI call it made failed."""


@dataclass
class TiminiResult:
    returncode: int | None
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _request(host: str, port: int, method: str, path: str, body: dict | None, timeout: float):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
    except (OSError, socket.timeout, http.client.HTTPException) as err:
        raise TiminiPrintError(f"Could not reach TiMini Print add-on at {host}:{port}: {err}") from err
    finally:
        conn.close()

    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as err:
        raise TiminiPrintError(f"Unexpected non-JSON response from TiMini Print add-on: {err}") from err

    if response.status >= 400 and "error" in data:
        raise TiminiPrintError(f"TiMini Print add-on rejected the request: {data['error']}")

    return TiminiResult(
        returncode=data.get("returncode"),
        stdout=data.get("stdout", ""),
        stderr=data.get("stderr", ""),
    )


def scan(host: str, port: int, timeout: float = 35.0) -> TiminiResult:
    return _request(host, port, "GET", "/scan", None, timeout)


def scan_printers(host: str, port: int, timeout: float = 35.0) -> list[dict]:
    """Scan and parse the raw CLI output into a simple printer list.

    Each item is ``{"id": <first token, e.g. name/address>, "label":
    <full line as shown by the scan>}``. The exact line format comes
    from TiMini-Print's own --scan output and isn't formally
    documented, so this is a best-effort split on the first whitespace
    - matching what the add-on's own web UI does with the same data.
    """
    result = scan(host, port, timeout)
    printers = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        printer_id = line.split()[0]
        printers.append({"id": printer_id, "label": line})
    return printers


def print_text(
    host: str,
    port: int,
    text: str,
    printer: str | None = None,
    text_columns: int | None = None,
    darkness: int | None = None,
    timeout: float = 95.0,
) -> TiminiResult:
    body = {"text": text}
    if printer:
        body["printer"] = printer
    if text_columns:
        body["text_columns"] = text_columns
    if darkness:
        body["darkness"] = darkness
    result = _request(host, port, "POST", "/print", body, timeout)
    if not result.ok:
        raise TiminiPrintError(
            result.stderr.strip() or f"Print failed (exit code {result.returncode})"
        )
    return result


def print_image(
    host: str,
    port: int,
    image_bytes: bytes,
    filename: str,
    printer: str | None = None,
    darkness: int | None = None,
    timeout: float = 125.0,
) -> TiminiResult:
    import base64    # pylint: disable=import-outside-toplevel

    body = {
        "image_b64": base64.b64encode(image_bytes).decode("ascii"),
        "filename": filename,
    }
    if printer:
        body["printer"] = printer
    if darkness:
        body["darkness"] = darkness
    result = _request(host, port, "POST", "/print_image", body, timeout)
    if not result.ok:
        raise TiminiPrintError(
            result.stderr.strip() or f"Print failed (exit code {result.returncode})"
        )
    return result
