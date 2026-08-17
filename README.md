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
| [FIRMWARE-NOTES.md](FIRMWARE-NOTES.md) | The full DP decode and firmware behavior: every datapoint's real meaning, the °F-mode trap, the write-only C/F register, fault bitfield + retry cycle, probe placement. |
| [GUIDE.md](GUIDE.md) | The **°F keeper**: a complete HA-side solution for running the unit in °F display mode with 1 °F remote setpoint resolution, closed-loop verified — plus the dashboard card and its user manual. |
| [heater_bridge.py](heater_bridge.py) | The raw-DP bridge script the keeper uses (runs on the HA host, vendored tinytuya). |
| [ha/](ha/) | Copy-paste HA config: shell commands, command_line sensor, script, automations, template sensor, dashboard section. |

## The device config (prerequisite)

The unit runs on [tuya-local](https://github.com/make-all/tuya-local) with a
device config for this product id — submitted upstream as
`aciq_pool_heatpump.yaml` (climate entity with heat/cool/auto +
quiet/smart/quick presets, live mode-dependent slider limits, running-%,
fault-code enum sensor, and more). Until it ships in a tuya-local release,
drop the file into `custom_components/tuya_local/devices/` (re-copy after
every tuya-local update — HACS wipes the folder).

## Why a "keeper" is needed for °F

Short version (long version in FIRMWARE-NOTES.md): the hardware's setpoint
register is integer-°C in °C mode, so Fahrenheit setpoints collapse in pairs
(91 °F and 92 °F are the same value). The display's °F mode *does* give the
controller a real 1 °F setpoint — but in that mode the firmware never
reports the setpoint back and mis-scales its temperature reports. The keeper
makes HA the bookkeeper: HA owns the setpoint, writes it raw, and audits the
unit through a °C-flip side door the firmware forgot to close.

## License

MIT — see [LICENSE](LICENSE).
