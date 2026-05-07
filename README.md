# Elon Smart Water – Home Assistant Integration

A custom Home Assistant integration that discovers Elon Smart Water heaters on your local network and exposes their status as sensor entities.

## Features

- **Network scan** – automatically scans a given subnet (CIDR) for Elon Smart Water controllers
- **Manual entry** – optionally enter the controller IP address directly
- **Per-device entities** – each water heater reported by the controller becomes its own Home Assistant device
- **Sensors** per device:
  - Water Temperature (°C)
  - Power Source
  - Reheat Time (min)
  - Last Communication
- **Binary sensors** per device:
  - Open Alarms (problem class)
  - AC Not Present (problem class)
- Polling interval: 60 seconds

## Device API

The integration queries the Elon Smart Water controller at:

```
GET http://<controller-ip>/V1/DeviceStatus/Query
```

Example response:
```json
{
  "deviceStatuses": [
    {
      "device": 1234,
      "lastComms": 200310972,
      "waterTemperature": 30.0,
      "hasOpenAlarms": false,
      "acNotPresent": false,
      "powerSource": 1,
      "logicalName": "Unit 1",
      "streetAddress": "1 Road",
      "reheatTime": 0
    }
  ]
}
```

## Installation

### HACS (recommended)

1. Open **HACS** → **Integrations** → the three-dot menu → **Custom repositories**.
2. Add `https://github.com/RuanBritz/homeassistant-elon-smart-water` as an **Integration**.
3. Search for **Elon Smart Water** and install it.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/elon_smart_water` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Elon Smart Water**.
3. Choose **Enter device IP manually** or **Scan network for devices**.
   - For the network scan, enter the subnet in CIDR notation (e.g. `192.168.3.0/24`). The integration will pre-fill a value based on the Home Assistant host IP.
4. Once a controller is found, confirm to complete the setup.
