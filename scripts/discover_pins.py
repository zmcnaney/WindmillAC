#!/usr/bin/env python3
"""Probe Blynk virtual pins on a Windmill device.

Reads V0..V<max> via the same dashboard.windmillair.com endpoint the
integration uses and prints whatever each pin returns. The goal is to
identify which pins your device actually populates (oscillation, sleep
mode, timer, sensors, etc.) so new features can be wired up from
evidence instead of guesswork.

This is a one-shot diagnostic. It only READS; it never writes.

Usage:
    python scripts/discover_pins.py <TOKEN>
    python scripts/discover_pins.py <TOKEN> --max-pin 80
    python scripts/discover_pins.py <TOKEN> --server https://dashboard.windmillair.com
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

DEFAULT_SERVER = "https://dashboard.windmillair.com"
DEFAULT_MAX_PIN = 60
TIMEOUT_SECONDS = 5


def fetch(server: str, token: str, pin: str) -> tuple[str | None, str | None]:
    """Return (value, error). Exactly one is non-None."""
    url = f"{server}/external/api/get?token={token}&{pin}"
    try:
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return None, f"request failed: {exc}"

    body = resp.text.strip()
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {body[:60]}"
    return body, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe Blynk pins on a Windmill device.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("token", help="Blynk auth token from the Windmill dashboard")
    parser.add_argument("--max-pin", type=int, default=DEFAULT_MAX_PIN,
                        help="Highest V-pin index to probe")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Blynk server base URL")
    parser.add_argument("--show-empty", action="store_true",
                        help="Include pins that returned an empty body")
    parser.add_argument("--show-errors", action="store_true",
                        help="Include pins that errored (likely undefined)")
    args = parser.parse_args()

    pins = [f"V{i}" for i in range(args.max_pin + 1)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda p: (p, *fetch(args.server, args.token, p)), pins))

    populated = []
    empty = []
    errored = []
    for pin, value, err in results:
        if err is not None:
            errored.append((pin, err))
        elif value == "":
            empty.append(pin)
        else:
            populated.append((pin, value))

    print(f"\nPopulated pins ({len(populated)} of {len(pins)}):")
    print(f"  {'Pin':<5} Value")
    print(f"  {'-' * 5} {'-' * 50}")
    for pin, value in populated:
        display = value if len(value) <= 60 else value[:57] + "..."
        print(f"  {pin:<5} {display!r}")

    if args.show_empty and empty:
        print(f"\nEmpty pins ({len(empty)}): {', '.join(empty)}")

    if args.show_errors and errored:
        print(f"\nErrored pins ({len(errored)}):")
        for pin, err in errored:
            print(f"  {pin:<5} {err}")

    if not populated:
        print("\nNo pins returned data. Check the token and that the device is online.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
