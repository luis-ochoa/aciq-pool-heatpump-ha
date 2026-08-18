# ACiQ inverter pool heat pump — Home Assistant integration kit

Everything I learned making an **ACiQ 150,000 BTU inverter pool heat/cool
pump** a first-class Home Assistant citizen — including true **1 °F setpoint
resolution**, which the stock integration path cannot deliver.

The Tuya radio lives in the unit's "ASL-OTA" wire controller
(`product_id 6cah7zdoj507nsz5`, category `qn`, Tuya protocol 3.4). Sold by
HVACDirect and others; the same OEM platform (Aquark) appears under several
brands, so much of this likely transfers.

## What's here

| File | What |
|---|---|
| [SETUP.md](SETUP.md) | Getting to local control: installing the device config, **obtaining the Tuya local key** (the hard part, with the failure table), adding the device, and the Err-914 survival note. Start here. |
| [tuya-local/aciq_pool_heatpump.yaml](tuya-local/aciq_pool_heatpump.yaml) | The tuya-local device config (climate with heat/cool/auto + quiet/smart/quick presets, live mode-dependent slider limits, running-%, fault-code enum sensor). **Submitted upstream as [make-all/tuya-local#5942](https://github.com/make-all/tuya-local/issues/5942)** (upstream PR creation is collaborators-only right now; a PR-ready branch sits at [luis-ochoa/tuya-local:aciq-pool-heatpump](https://github.com/luis-ochoa/tuya-local/tree/aciq-pool-heatpump)). Usable from here until it ships in a release. |
| [FIRMWARE-NOTES.md](FIRMWARE-NOTES.md) | The full DP decode and firmware behavior: every datapoint's real meaning, the °F-mode trap, the write-only C/F register, fault bitfield + retry cycle, probe placement. |
| [GUIDE.md](GUIDE.md) | The **°F keeper**: a complete HA-side solution for running the unit in °F display mode with 1 °F remote setpoint resolution, closed-loop verified — plus the dashboard card and its user manual. |
| [heater_bridge.py](heater_bridge.py) | The raw-DP bridge script the keeper uses (runs on the HA host, vendored tinytuya). |
| [ha/](ha/) | Copy-paste HA config: shell commands, command_line sensor, script, automations, template sensors (mode-proof water temp + latched fault), dashboard section. |

## Install order

[SETUP.md](SETUP.md) (local control working) → [GUIDE.md](GUIDE.md) (the °F
keeper + card). Stop after SETUP if 2 °F setpoint granularity in °C display
mode is fine for you — the plain climate entity is fully coherent there.

## Why a "keeper" is needed for °F

Short version (long version in FIRMWARE-NOTES.md): the hardware's setpoint
register is integer-°C in °C mode, so Fahrenheit setpoints collapse in pairs
(91 °F and 92 °F are the same value). The display's °F mode *does* give the
controller a real 1 °F setpoint — but in that mode the firmware never
reports the setpoint back (the module's dp2 schema is °C-range 7–40; it
silently drops out-of-range reports while accepting out-of-range writes,
so °F goes in and never comes back out) and mis-scales its temperature
reports. The keeper
makes HA the bookkeeper: HA owns the setpoint, writes it raw, and audits the
unit through a °C-flip side door the firmware forgot to close.

## License

MIT — see [LICENSE](LICENSE).

## Credits

Reverse-engineered and written with [Claude](https://claude.com)
(Anthropic): the firmware decode, the °F keeper design, and these docs
came out of live hardware sessions driven through Claude Code.
