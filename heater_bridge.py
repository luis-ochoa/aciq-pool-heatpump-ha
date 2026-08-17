#!/usr/bin/env python3
"""Pool heater °F bridge — raw dp2/dp13 access for the °F-mode keeper.

The ASL-OTA wire controller in °F display mode interprets dp2 writes as
integer °F but never publishes setpoint state back (full decode in
FIRMWARE-NOTES.md, "The °F story"). This bridge is HA's raw write/verify path.

Verbs:
  status         raw dps dump (JSON)
  flip c|f       switch the unit's UOM (dp13 — write-only but works)
  set_f N        write integer °F setpoint (59..104) raw into dp2
  verify N       closed-loop check against intended °F setpoint N:
                   flip 'c'  -> the °F->°C flip publishes the controller's
                                true setpoint to dp2 as floor((F-32)/1.8)
                   read dp2  -> compare with floor((N-32)/1.8)
                   flip 'f'  -> (corrupts the register via the firmware's
                                2C+27 shortcut, so always...)
                   re-assert -> N if in sync, else the wall's inferred °F
                 Writes verdict JSON to last_verify.json and stdout.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import yaml
import tinytuya

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_verify.json")


def dev():
    # secrets.yaml carries: tuya_pool_heater_id, tuya_pool_heater_key,
    # tuya_pool_heater_host (give the device a DHCP reservation!)
    sec = yaml.safe_load(open("/config/secrets.yaml"))
    d = tinytuya.Device(sec["tuya_pool_heater_id"], sec["tuya_pool_heater_host"],
                        sec["tuya_pool_heater_key"], version=3.4)
    d.set_socketTimeout(5)
    return d


def dps(d):
    r = d.status()
    return r.get("dps", {}) if isinstance(r, dict) else {}


def in_c_mode(s):
    # dp108 heating/auto min limit: 7 or 15 in deg C space, 44/59 in deg F space.
    # dp3 water temp: ~34 in C space, ~93 in F space. Use both, limits first.
    lim = s.get("108")
    if lim is not None:
        return lim < 44
    t = s.get("3")
    return t is not None and t < 60


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else "status"
    d = dev()

    if verb == "status":
        print(json.dumps(dps(d)))
        return

    if verb == "flip":
        d.set_value(13, sys.argv[2])
        time.sleep(2)
        print(json.dumps(dps(d)))
        return

    if verb == "set_f":
        n = int(sys.argv[2])
        if not 59 <= n <= 104:
            raise SystemExit("set_f out of range 59..104: %d" % n)
        d.set_value(2, n)
        print(json.dumps({"written_f": n}))
        return

    if verb == "verify":
        intended = int(sys.argv[2])
        d.set_value(13, "c")
        time.sleep(3)
        s = dps(d)
        if not in_c_mode(s):          # flip may have been lost — one retry
            d.set_value(13, "c")
            time.sleep(3)
            s = dps(d)
        c = s.get("2") if in_c_mode(s) else None
        d.set_value(13, "f")
        time.sleep(2)

        if c is None:
            result, adopted, assert_f = "read_failed", None, intended
            in_sync = False
        else:
            # The firmware's degF->degC flip conversion has been observed both
            # flooring (89->31) and rounding (91->33), and the channel only
            # carries integer degC anyway — accept either plausible conversion
            # of the intended value. Net drift-detection resolution: +/-2 degF.
            plausible = {int((intended - 32) / 1.8), int(round((intended - 32) / 1.8))}
            in_sync = c in plausible
            if in_sync:
                result, adopted, assert_f = "in_sync", None, intended
            else:
                adopted = int(round(c * 1.8 + 32))
                result, assert_f = "drift_adopted", adopted
        d.set_value(2, int(assert_f))

        verdict = {
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "intended_f": intended,
            "published_c": c,
            "in_sync": bool(in_sync),
            "adopted_f": adopted,
            "result": result,
        }
        tmp = OUT + ".tmp"
        open(tmp, "w").write(json.dumps(verdict))
        os.replace(tmp, OUT)
        print(json.dumps(verdict))
        return

    raise SystemExit("unknown verb: %s" % verb)


main()
