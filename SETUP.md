# Setup — from a cloud-tethered heater to local HA control

Do this before [GUIDE.md](GUIDE.md). At the end the heater runs fully local
(no Tuya cloud dependency) with a rich climate entity in Home Assistant.

## 1. Install tuya-local and the device config

1. Install [tuya-local](https://github.com/make-all/tuya-local) via HACS.
2. Copy [tuya-local/aciq_pool_heatpump.yaml](tuya-local/aciq_pool_heatpump.yaml)
   into `/config/custom_components/tuya_local/devices/`.
   - This config has been submitted upstream; once it ships in a tuya-local
     release you can delete the copy (same filename → zero migration).
   - Until then: **a HACS update of tuya-local wipes the devices folder** —
     re-copy the file after every update.

## 2. Get the device's local key

The hard part. The local key is **not obtainable from Home Assistant or the
Smart Life app** — it requires a (free) Tuya IoT developer project:

1. Create a project on [iot.tuya.com](https://iot.tuya.com). Pick the data
   center that matches where your Smart Life **account** is provisioned
   (US accounts are typically "Western America") — not your timezone.
2. Subscribe to the **IoT Core** service AND authorize it for your project
   (two separate actions).
3. Project → Devices → **Link App Account** → scan the QR with Smart Life.
4. Read the key: the project's Device List shows it, or run
   `tinytuya wizard` with the project's Access ID/Secret.

Four different failures all present as "0 devices" — check the underlying
error:

| Error | Cause | Fix |
|---|---|---|
| `Err 911 ... don't have access` | calling IP not allowlisted | project → Authorization Key → IP Allowlist (watch dual-stack: your host may egress IPv6 while only its IPv4 is listed) |
| `code 28841002` | IoT Core subscription expired | re-subscribe and re-authorize for the project |
| `success:true, total:0` | app account not linked | step 3 above |
| devices returned | working | — |

Warnings that cost something to learn:

- The Smart Life app's "User Code" is **not** a local key.
- **Do not re-pair the device** in Smart Life — that rotates the local key.
- Local keys often contain YAML-significant characters — quote carefully in
  `secrets.yaml` (or write them programmatically).

## 3. Add the device

- Give the heater a **DHCP reservation** first — tuya-local pins it by IP,
  and a lease change breaks it silently (`error 901`).
- tuya-local usually auto-discovers Tuya devices and parks a discovery flow
  per device (Settings → Devices & Services). Configure it with: the device
  ID, IP, local key, protocol **3.4**, poll_only off. The config scores
  this device 101 % and should rank first.
- Optional but recommended: once local control works, remove the Tuya
  *cloud* integration entirely — cloud round-trips are what make grouped
  Tuya devices flaky, and this device advertises `support_local: true`.

## 4. Know this before your first fault

- **`Err 914` (invalid key) on a device that worked before is usually NOT
  a key problem** — it's a module-side local-session lockout. Power-cycle
  the heater at the breaker and try again before touching the key.
- The unit refuses remote switch-on while latched in fault protection
  (e.g. E3 with the pool pump off) — that's the hardware, not the config.

Then continue with [GUIDE.md](GUIDE.md) for the °F keeper and the card.
