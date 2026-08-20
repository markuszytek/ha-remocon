# ha-remocon

**Unofficial Home Assistant integration for Elco heat pumps via the Remocon-Net cloud service.**

This repository is maintained by Markus Zytek: [github.com/markuszytek/ha-remocon](https://github.com/markuszytek/ha-remocon).
It was developed and tested with an **AEROTOP MONO 08.2 ODU** heat pump.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=markuszytek&repository=ha-remocon&category=integration)

Control and monitor your Elco heat pump (e.g. Aerotop SPK) through the Remocon-Net cloud API — directly in Home Assistant, no MQTT or AppDaemon needed.

> **Disclaimer:** This is an unofficial community project. It is not endorsed by or affiliated with Elco or the Ariston Thermo Group.

## Features

- **Configuration flow** — Authenticate and configure a gateway and zone in Home Assistant
- **Read-only sensors** — Room/outside temperature, zone target temperature, flow setpoint, system pressure, DHW storage temperature, error text, and quiet-mode times
- **Controls** — Plant, zone, and DHW operation modes plus heating, cooling, and DHW temperature setpoints
- **Status entities** — Error, holiday, quiet-mode, and AUTO states
- **Cloud polling** — Data is refreshed through the Remocon-Net web API

## Requirements

- Elco heat pump with a Remocon-Net gateway (connected to the internet)
- Remocon-Net account ([remocon-net.remotethermo.com](https://www.remocon-net.remotethermo.com))
- Home Assistant >= 2024.1.0
- [HACS](https://hacs.xyz/) installed

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. **≡ Menu** → **Custom Repositories**
3. Add:
   - **URL:** `https://github.com/markuszytek/ha-remocon`
   - **Category:** Integration
4. Search for **"Remocon-Net"** in HACS and install
5. Restart Home Assistant

### Manual

```bash
cd /path/to/homeassistant/config/custom_components/
git clone https://github.com/markuszytek/ha-remocon.git elco_remocon_temp
cp -r elco_remocon_temp/custom_components/elco_remocon ./
rm -rf elco_remocon_temp
```

Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Remocon-Net"**
3. Enter your credentials:
   - **Email:** Your Remocon-Net login email
   - **Password:** Your Remocon-Net login password
   - **Gateway ID:** Your system's gateway ID (see below)
   - **Zone:** Heating zone (default: 1)

### Finding your Gateway ID

1. Log in at [remocon-net.remotethermo.com](https://www.remocon-net.remotethermo.com)
2. The gateway ID is shown in the URL, e.g. `A1B2C3D4E5F6` in:
   ```
   https://www.remocon-net.remotethermo.com/R2/Plant/Index/A1B2C3D4E5F6
   ```

## Entities

After setup, entities are attached to the configured Remocon-Net device. Home Assistant may include the device name in the final entity ID.

### Sensors

- Room temperature, when a room sensor is available
- Outside temperature
- Zone target temperature
- Flow setpoint temperature
- System pressure
- DHW storage temperature
- Error text
- Quiet-mode start and end time

### Selects

- Plant operation mode: Summer, Winter, Heating only, Cooling, Off
- DHW operation mode: Disabled, Time-based, Continuous
- Zone operation mode: Off, Manual, Time program

### Number controls

- Zone comfort and reduced temperature
- Zone cooling comfort and reduced temperature
- DHW target, comfort, and reduced temperature

The currently supported ranges and steps match the values reported by the tested gateway.

### Switch and binary sensors

- `AUTO` switch for automatic thermoregulation
- Error state
- Holiday state
- Quiet-mode active state

The integration intentionally does not create a Climate entity. The individual controls above map directly to the Remocon-Net requests and avoid exposing unrelated values.

## CLI Tool

A standalone CLI tool is included for testing and debugging:

```bash
pip install -r requirements.txt

# Create config
cp config.example.json config.json
# Edit config.json with your email, password and gateway ID

# Check status with the standalone CLI
python3 remocon.py --config-file config.json status

# Raw API response (debug)
python3 remocon.py --config-file config.json raw-get
```

The CLI is a separate diagnostic client and is not used by the Home Assistant integration.

### Live polling test

For a local integration/API smoke test, set the polling interval only for that process:

```powershell
$env:ELCO_REMOCON_SCAN_INTERVAL = "10"
```

The normal default remains 120 seconds. Never commit credentials or session cookies; enter credentials interactively or provide them through a local, ignored configuration.

## Known limitations

- **Cloud-dependent:** Control goes through the Remocon-Net cloud. No control is possible during internet outages.
- **Polling:** The default refresh interval is 120 seconds and can be overridden for local testing with `ELCO_REMOCON_SCAN_INTERVAL`.
- **Optional data:** Room temperature and some DHW values depend on the capabilities reported by the gateway.

## Technical details

The Home Assistant integration uses the same web requests as the Elco Remocon-Net UI:

- **Login:** Cookie-based authentication via `/R2/Account/Login`
- **Data:** `/R2/PlantHome/GetData/`, `/R2/Plant/PlantHeader/`, and `/R2/PlantAdvancedSettings/Refresh/`
- **Control:** `/R2/PlantMenu/Submit/` and `/R2/PlantDhw/Save/`
- **Platform:** remotethermo.com (Ariston Thermo Group)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT
