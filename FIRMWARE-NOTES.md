# ASL-OTA wire controller — firmware notes

Everything below was verified on live hardware (2026-08), most of it twice.
Device: ACiQ 150k BTU inverter pool heat/cool pump, Tuya module in the
"ASL-OTA" wire controller, `product_id 6cah7zdoj507nsz5`, category `qn`,
protocol 3.4. The OEM platform is Aquark (the `warm/cool/smart` vocabulary
matches tuya-local's `aquark_heatpump`).

## Datapoints — complete vocabulary

A full `updatedps` sweep over indices 1–255 confirmed these are ALL the DPs
the module speaks:

| DP | Meaning | Notes |
|---|---|---|
| 1 | power switch | refuses remote ON while latched in fault protection |
| 2 | target temp | **integer °C in °C mode** (°F setpoints collapse in pairs); interpreted as **integer °F in °F mode** (writes only — see the °F story) |
| 3 | temperature | probe sits **at the heat exchanger**: equals inlet/pool water with the compressor idle, drifts toward (in cooling, below) the outlet stream under load. The display's own inlet/outlet probes are never published. |
| 4 | mode enum | `warm` / `cool` / `smart` (= auto changeover). Cloud spec lies (declares only `["smart"]`). |
| 5 | gear enum | `silence` / `smart` / `booster` — inverter aggressiveness. Near target the inverter throttles regardless; far from target: silence caps ~60 %, smart reaches 100 %, booster ramps fastest. **A mode change resets gear to silence.** |
| 12 | "Current Power" | fake — static 25688 with brief flickers at state transitions. Not power. |
| 13 | temp unit c/f | **WRITE-ONLY.** Never appears in status (looks dead) but writing `'c'`/`'f'` flips the whole unit including the wall display. See the °F story. |
| 21 | fault bitfield | E1..E8 = bits 0..7. **E3 (no water flow) = 4, captured live.** Pulses code↔0 every ~4 s while retrying; flow re-test on a ~240 s cycle produces ~55 s quiet windows that look like recovery but aren't. A solid flow-switch closure clears instantly. |
| 102 | "Malfunction 2" | mislabeled by the OEM — it's a **heating-mode flag**: cool → "0", warm/smart → "1", gear irrelevant (verified across the full mode×gear matrix, including while actively cooling in auto). |
| 105 | running % | compressor output; **exceeds 100 in booster** (103 observed). Ramps ±2 % every 2–4 s. |
| 108 | min setpoint limit | **mode-dependent, pushed live**: cool 7, warm 15, auto 7 (°C) |
| 109 | max setpoint limit | cool 35, warm 40, auto 40 (°C) |
| 111 | "dp_super_mode" | read-only, never left 0 through every state incl. live faults. Defrost-flag hypothesis, unconfirmed. |

Fault bits per the manual's table: 1=E1 high pressure · 2=E2 low pressure ·
4=E3 no water · 8=E4 phase · 16=E5 power range · 32=E6 in/out ΔT · 64=E7
outlet temp · 128=E8 exhaust temp.

## The °F story

With the display set to °F the firmware becomes a trap for integrations:

- dp3/108/109 **rescale to °F** but carry no unit signal; anything reading
  them as °C shows garbage (93 °F water renders as 199 °F).
- dp2 **writes are interpreted as °F integers** — true 1 °F resolution!
  Values below the °F floor (59) are silently discarded.
- dp2 **reads are broken**: setpoint edits made at the display are *never*
  published, and the module's cache echoes only schema-legal (≤40) writes,
  so it reports stale values while the controller runs something else.
- The controller genuinely runs on its private °F setpoint (it stops
  heating when the water passes it).

**Mode-flip conversions are asymmetric**, and both are firmware-buggy:

- **°F→°C publishes** the converted setpoint to dp2 — the only moment the
  firmware ever reveals the °F-mode setpoint. Rounding is inconsistent
  (observed both floor and round) → treat reads as ±1 °C.
- **°C→°F uses the approximation F = 2C + 27** (32 °C → 91 °F, not 89.6)
  and does not refresh dp2.
- Net: every flip can corrupt the setpoint by ~1.5 °F. Always re-write the
  intended setpoint after flipping.

**dp13 is the side door.** It looks dead — absent from status and
`updatedps`, the Smart Life app's °F selector visibly snaps back, and
writes appear ignored when the unit is already in °C (an invisible no-op).
But `set_value(13, 'f')` / `set_value(13, 'c')` genuinely flips the unit
both directions, remotely. Combined with flip-publish, that yields a
working **read cycle** for the °F setpoint: flip `'c'` → read dp2 (truth
±1 °F) → flip `'f'` → re-write the intended value. ~10 s; the display
blinks °C. [GUIDE.md](GUIDE.md) builds a complete HA solution on it.

Also °F-related: the Tuya app is broken in °F mode too (shows mixed units),
and the wall display's own °F selection works fine locally — the breakage
is purely in what the Tuya module reports.

## Practical warnings

- **Err 914 (invalid key) after the device has worked**: a module-side
  local-session lockout, not a key problem. Power-cycle at the breaker;
  don't re-pair (re-pairing rotates the local key).
- tuya-local pins the device by IP — give it a **DHCP reservation**.
- The module tolerates concurrent local sessions (tuya-local + a script).
- Protocol is 3.4 (many same-brand lights are 3.5).

## Why °F never reads back — the schema-firewall theory

Every °F observation above unifies under one mechanism: dp2's Tuya
product schema is **integer 7–40, °C-space**, and the WiFi module
validates MCU→module *reports* against it, silently dropping
out-of-range values — while module→MCU *writes* forward with little
validation. That single rule predicts: wall °F edits never publish
(dropped at the module); local °F writes work but never echo; the
F→C flip publishes its result (32-ish, in-schema) while the C→F flip
cannot (result ~90, out-of-schema); and dp3/108/109 pass °F-space
values because their schema ranges are wider. Even Tuya's own app
can't read the °F state — it reads the same DP table.

Consequence: the °F setpoint is unreachable from software, full stop
(the dp sweep proves no hidden DP carries it). The only paths left are
hardware: a UART tap on the MCU↔module serial line (would prove the
drop), or replacing the module with an ESP32 speaking the Tuya MCU
protocol (native °F both ways, no schema firewall — at the cost of
leaving tuya-local). The keeper in this repo is the software-side
optimum: 1 °F writes, ±2 °F closed-loop audit.
