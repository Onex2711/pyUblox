#!/usr/bin/env python
"""Read position from a u-blox receiver after entering a token.

The token is intentionally logged in masked form only and can be entered
interactively or provided via --token.
"""

from __future__ import print_function

import optparse
import sys
import time

import ublox


def _prompt_token():
    try:
        # py3
        return input("u-blox token eingeben: ").strip()
    except NameError:
        # py2
        return raw_input("u-blox token eingeben: ").strip()


def _mask_token(token):
    if len(token) <= 4:
        return "*" * len(token)
    return "%s...%s" % (token[:2], token[-2:])


def _get_field(msg, names, default=None):
    for name in names:
        if hasattr(msg, name):
            return getattr(msg, name)
    return default


def main():
    parser = optparse.OptionParser("ublox_token_position.py [options]")
    parser.add_option("--port", default="/dev/ttyACM0", help="serial port (default: %default)")
    parser.add_option("--baudrate", type="int", default=38400, help="baudrate (default: %default)")
    parser.add_option("--token", default=None, help="u-blox token (wenn nicht gesetzt: interaktive Eingabe)")
    parser.add_option("--timeout", type="float", default=60.0, help="max. Wartezeit in Sekunden (default: %default)")
    parser.add_option("--debug", action="store_true", default=False, help="Debug-Ausgaben einschalten")
    opts, _args = parser.parse_args()

    token = opts.token or _prompt_token()
    if not token:
        print("Fehler: Es wurde kein Token eingegeben.")
        return 2

    if opts.debug:
        print("[DEBUG] Token erkannt: %s" % _mask_token(token))
        print("[DEBUG] Öffne Empfänger auf %s @ %d baud" % (opts.port, opts.baudrate))

    dev = ublox.UBlox(opts.port, baudrate=opts.baudrate, timeout=0.2)

    # NAV_POSLLH für periodische Positionsausgabe aktivieren.
    dev.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_POSLLH, 1)

    start = time.time()
    while True:
        if (time.time() - start) > opts.timeout:
            print("Timeout: Keine Position innerhalb von %.1f Sekunden erhalten." % opts.timeout)
            return 1

        try:
            msg = dev.receive_message()
        except ublox.UBloxError as ex:
            if opts.debug:
                print("[DEBUG] Parserfehler: %s" % ex)
            continue

        if msg is None:
            continue

        msg_name = None
        try:
            msg_name = msg.name()
        except ublox.UBloxError:
            msg_name = "<unknown>"

        if opts.debug:
            print("[DEBUG] Nachricht: %s" % msg_name)

        if msg.msg_type() != (ublox.CLASS_NAV, ublox.MSG_NAV_POSLLH):
            continue

        # Manche pyublox-Versionen verwenden unterschiedliche Feldnamen.
        lon_raw = _get_field(msg, ["Longitude", "lon", "Lon"])
        lat_raw = _get_field(msg, ["Latitude", "lat", "Lat"])
        hmsl_raw = _get_field(msg, ["hMSL", "height", "Height", "alt"], 0)

        if lon_raw is None or lat_raw is None:
            print("Position empfangen, aber Feldnamen unerwartet. Rohdaten:\n%s" % msg)
            return 3

        lon = float(lon_raw) / 1.0e7
        lat = float(lat_raw) / 1.0e7
        alt_m = float(hmsl_raw) / 1000.0

        print("Position: lat=%.7f lon=%.7f alt=%.2f m" % (lat, lon, alt_m))
        if opts.debug:
            print("[DEBUG] raw lat=%s lon=%s hMSL=%s" % (lat_raw, lon_raw, hmsl_raw))
        return 0


if __name__ == "__main__":
    sys.exit(main())
