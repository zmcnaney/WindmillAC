#!/usr/bin/env python3
"""Probe Blynk virtual pins on a Windmill device.

Reads V0..V<max> via the same dashboard.windmillair.com endpoint the
integration uses and prints whatever each pin returns. The goal is to
identify which pins your device actually populates (oscillation, sleep
mode, timer, sensors, etc.) so new features can be wired up from
evidence instead of guesswork.

This is a one-shot diagnostic by default. With --watch, it polls
continuously and prints only the pins whose values change — useful for
correlating Windmill-app toggles (oscillation on/off, mode change,
timer set) to specific pins. It only READS; it never writes.

Usage:
    python scripts/discover_pins.py <TOKEN>
    python scripts/discover_pins.py <TOKEN> --max-pin 80
    python scripts/discover_pins.py <TOKEN> --watch
    python scripts/discover_pins.py <TOKEN> --watch --interval 1
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests

DEFAULT_SERVER = "https://dashboard.windmillair.com"
DEFAULT_MAX_PIN = 60
DEFAULT_INTERVAL = 2
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


def snapshot(server: str, token: str, pins: list[str]) -> dict[str, tuple[str | None, str | None]]:
    """Fetch every pin in parallel; return {pin: (value, error)}."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda p: (p, fetch(server, token, p)), pins)
    return {pin: result for pin, result in results}


def state_label(value: str | None, err: str | None) -> str:
    if err is not None:
        return f"<error: {err}>"
    if value == "":
        return "<empty>"
    return repr(value)


def print_oneshot(snap: dict[str, tuple[str | None, str | None]],
                  show_empty: bool, show_errors: bool) -> int:
    populated, empty, errored = [], [], []
    for pin, (value, err) in snap.items():
        if err is not None:
            errored.append((pin, err))
        elif value == "":
            empty.append(pin)
        else:
            populated.append((pin, value))

    print(f"\nPopulated pins ({len(populated)} of {len(snap)}):")
    print(f"  {'Pin':<5} Value")
    print(f"  {'-' * 5} {'-' * 50}")
    for pin, value in populated:
        display = value if len(value) <= 60 else value[:57] + "..."
        print(f"  {pin:<5} {display!r}")

    if show_empty and empty:
        print(f"\nEmpty pins ({len(empty)}): {', '.join(empty)}")

    if show_errors and errored:
        print(f"\nErrored pins ({len(errored)}):")
        for pin, err in errored:
            print(f"  {pin:<5} {err}")

    if not populated:
        print("\nNo pins returned data. Check the token and that the device is online.")
        return 1
    return 0


def watch(server: str, token: str, pins: list[str], interval: float) -> int:
    print(f"Taking baseline snapshot...")
    prev = snapshot(server, token, pins)
    print_oneshot(prev, show_empty=False, show_errors=False)
    print(f"\nWatching for changes every {interval}s. Toggle settings in the Windmill app; "
          f"changed pins will be printed below. Ctrl+C to stop.\n")
    print(f"  {'Time':<10} {'Pin':<5} {'Before':<25} {'After':<25}")
    print(f"  {'-' * 10} {'-' * 5} {'-' * 25} {'-' * 25}")

    try:
        while True:
            time.sleep(interval)
            curr = snapshot(server, token, pins)
            ts = datetime.now().strftime("%H:%M:%S")
            for pin in pins:
                old_value, old_err = prev[pin]
                new_value, new_err = curr[pin]
                if old_value == new_value and old_err == new_err:
                    continue
                print(f"  {ts:<10} {pin:<5} {state_label(old_value, old_err):<25} "
                      f"{state_label(new_value, new_err):<25}")
            prev = curr
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


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
    parser.add_argument("--watch", action="store_true",
                        help="Poll continuously and print only pins whose values change")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                        help="Poll interval in seconds (only used with --watch)")
    args = parser.parse_args()

    pins = [f"V{i}" for i in range(args.max_pin + 1)]

    if args.watch:
        return watch(args.server, args.token, pins, args.interval)

    snap = snapshot(args.server, args.token, pins)
    return print_oneshot(snap, args.show_empty, args.show_errors)


if __name__ == "__main__":
    sys.exit(main())
