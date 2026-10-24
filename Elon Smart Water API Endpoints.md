# Elon Smart Water API Endpoints

Oct 24, 2026 · @Ruan

## Overview

This is the full endpoint map for the Elon Smart Water app `com.poweroptimal.elon.mobile` 2.0.1 (build 10000550), a Flutter app whose logic is compiled Dart in `libapp.so` (Dart 3.11.4, Android arm64).

The app talks to its water heaters two ways: a **cloud REST API** at `api.elonsmartwater.com` (used when you are away), and a **local HTTP API** on the thermostat itself over your home Wi-Fi or the device's own hotspot. Both speak the same `/V1/...` verb set; the local one is what the Home Assistant integration should drive for direct control.

**How this was recovered.** `libapp.so` was decompiled with [blutter](https://github.com/worawit/blutter) against a locally-built Dart 3.11.4 VM. blutter only recovered \~6,800 of \~24,600 function bodies on this Dart version, so the request builders were missing. I disassembled the whole `.text` section directly (capstone) and resolved each function's object-pool references. Every HTTP method, path and JSON field below was read out of the actual request-builder function for that endpoint, so method and body shapes are **confirmed from code**, not guessed. What is still unverified is marked in the last section.

## Authentication

There are two separate auth systems: one for the cloud API (AWS Cognito), one for the local device API (an on-device challenge handshake). They are unrelated.

### Cloud: AWS Cognito via Amplify

The Amplify config is embedded in `libapp.so`. The app signs in through Cognito and sends the resulting access token as `Authorization: Bearer <token>` on every cloud call, plus a `PowerOptimal-Provider-ID` header.

| Setting | Value |
| --- | --- |
| Region | `eu-west-1` |
| User pool | `eu-west-1_Or01hl4KQ` |
| App client id | `4e147nsc50m4mntdiekm41fg8g` (public, no secret) |
| Hosted UI domain | `smartwaterv2-production.auth.eu-west-1.amazoncognito.com` |
| OAuth | `/oauth2/authorize`, `/oauth2/token`, scopes `email openid profile`, `response_type=code` |
| Social IdPs | Google, Sign in with Apple |
| Redirects | `https://portal.elonsmartwater.com/auth/social`, `elon://callback` |
| MFA | optional (SMS, TOTP) |

### Local: on-device challenge handshake

The thermostat does **not** use Cognito. Instead, the app registers itself with each device and then signs every request. The handshake, in order:

1. `GET /V1/ApplicationVerification/PublicKey` — fetch the device's RSA public key (PEM). A hard-coded server public key is also bundled in the app as a fallback.
2. `PUT /V1/ApplicationVerification/ApplicationId/Request` with body `{ "secret": <RSA-OAEP/SHA-256 encrypted blob> }` — the app generates key material, encrypts it under the device's public key, and the device returns an integer **`applicationId`**.
3. `PUT /V1/ApplicationVerification/Authenticate` with body `{ "applicationId": <int>, "timestamp": <int>, "signed": <signature> }` — the device verifies the signature over the timestamp and returns an **`authId`** plus the list of `devices` the app may control.
4. `PUT /V1/ApplicationVerification/Device/Add` with `{ applicationId, authId, timestamp, deviceSerial, signed }` — associates a specific `deviceSerial`.

After the handshake, **every** local `/V1/...` request carries three integers in its JSON body: `applicationId`, `authId`, and (for device-specific calls) `deviceSerial`. These are the local equivalent of a session token. The crypto is PointyCastle (RSA with OAEP/SHA-256 padding; SHA-256 digests; the app also bundles AES-CBC and a Fortuna PRNG).

The practical consequence for Home Assistant is in the integration section: the existing read-only integration reaches `/V1/DeviceStatus/Query` with no auth at all, so the device's enforcement of these fields on the local port is the one thing that must be checked on real hardware before local *control* can be trusted.

## Cloud endpoints

Base URL `https://api.elonsmartwater.com`, JSON body, `Authorization: Bearer <Cognito token>`. These are the paths found as string constants. Paths with `{id}` are per-device sub-resources under `/portal/v1/device/{id}/...`; the pattern `^/portal/v1/device/[^/]+/heating_properties$` is confirmed by a regex in the binary, the rest follow the same shape.

| Area | Method | Path |
| --- | --- | --- |
| Version | GET | `/portal/version` |
| User | — | `/portal/v1/user/me` |
| User | — | `/portal/v1/user/me/legal/{id}` |
| Invites | — | `/portal/v1/user/invite_with_device` |
| Invites | — | `/portal/v1/redeem_invite` |
| Devices | — | `/portal/v1/device/list` |
| Devices | — | `/portal/v1/device/{id}` |
| Devices | PATCH | `/portal/v1/device/set_label` |
| Devices | — | `/portal/v1/device/{id}/claim` |
| Devices | DELETE | `/portal/v1/device/{id}/iot_access` |
| Heating | — | `/portal/v1/device/{id}/heating_properties` |
| Heating | — | `/portal/v1/device/{id}/heat_now` |
| Heating | — | `/portal/v1/device/{id}/cancel_grid_heating` |
| Timers | — | `/portal/v1/device/{id}/timer_profiles` |
| Timers | — | `/portal/v1/device/{id}/active_timer_profile` |
| Alarms | — | `/portal/v1/device/{id}/alarms` |
| Measurements | — | `/portal/v1/device/{id}/measurements/{...}` |
| Energy | — | `/portal/v1/device/{id}/energy/{...}` |
| Wi-Fi | — | `/portal/v1/device/{id}/wifi_properties` |
| Access | — | `/portal/v1/device/{id}/users` |
| Access | — | `/portal/v1/device/access/types`, `/requests`, `/pending`, `/grant`, `/request/{id}` |
| Address | — | `/portal/v1/address`, `/address/{id}`, `/address/reverse_geocode` |
| Link | — | `/portal/v1/link/{id}` |

A dash in Method means the verb wasn't in a recovered request builder (most cloud calls go through a generic client that wasn't fully disassembled). Other cloud hosts: `portal.elonsmartwater.com` (web portal, OAuth redirects, deep links), two AWS IoT MQTT brokers (`a17rzcsmvoauwr-ats` and `a3nh7x0o5lv96v-ats.iot.eu-west-1.amazonaws.com`), and `elonsmartiot.com`.

## Local endpoints

This is the direct-to-device API and the one that matters for local control. Transport is plain **HTTP on port 80** using the Dio client, JSON body, headers `Accept: application/json` and `Content-Type: application/json`. (The cloud variant of the same client uses HTTPS on 443.)

**Finding the device.** On your home Wi-Fi the app resolves the thermostat by mDNS at `Elon-<serial>.local` (hence the Wi-Fi multicast lock in `MainActivity`). During first-time pairing the device runs a hotspot and answers at `192.168.4.1`. Either way it is an HTTP server on port 80.

**Body fields.** Unless noted, every body is `{ applicationId, authId, deviceSerial }` as integers, plus the extra fields listed. All methods/paths/fields below were read from the request-builder functions.

| Group | Method | Path | Extra body fields |
| --- | --- | --- | --- |
| Pairing | — | `/V1/ApplicationVerification/ServerAvailable` | — |
| Pairing | GET | `/V1/ApplicationVerification/PublicKey` | — |
| Pairing | PUT | `/V1/ApplicationVerification/ApplicationId/Request` | `secret` |
| Pairing | PUT | `/V1/ApplicationVerification/Authenticate` | `applicationId, timestamp, signed` |
| Pairing | PUT | `/V1/ApplicationVerification/Device/Add` | `timestamp, signed` |
| Pairing | PUT | `/V1/ApplicationVerification/Device/Remove` | — |
| Ownership | POST | `/V1/Device/Claim` | `claimId` |
| Status | PUT | `/V1/DeviceStatus/Query` | `deviceSerials` (array) |
| Status | — | `/V1/Software/QueryActual` | — |
| Status | — | `/V1/ActiveAlarms/Query` | — |
| Status | PUT | `/V1/Measurements/Query` | `sensorId, startWhen, endWhen, maximumSegmentLength, startOffset` |
| **Heating** | **PUT** | **`/V1/Thermostat/ForceReheat`** | — (grid boost / heat now) |
| **Heating** | **PUT** | **`/V1/Thermostat/CancelGridHeating`** | — |
| **Config** | **PUT** | **`/V1/DeviceConfiguration/Property/Update`** | **`name, value`** |
| Config | PUT | `/V1/DeviceConfiguration/Property/Query` | `properties` (array) |
| Config | PUT | `/V1/DeviceConfiguration/AssignedAddress/Query` | — |
| Config | PUT | `/V1/DeviceConfiguration/AssignedAddress/Update` | `address{...}` |
| Config | PUT | `/V1/DeviceConfiguration/AssignedAddress/Clear` | — |
| Config | PUT | `/V1/DeviceConfiguration/Reset` | — (factory reset) |
| **Timers** | **POST** | **`/V1/TimerProfiles/Update`** | **`activeProfile, profiles`** |
| **Timers** | **POST** | **`/V1/TimerProfiles/Active/Update`** | **`profileName`** |
| Timers | POST | `/V1/TimerProfiles/Query` | — |
| Wi-Fi | POST | `/V1/Wifi/Scan/Start` | — |
| Wi-Fi | POST | `/V1/Wifi/Status/Query` | — |
| Wi-Fi | POST | `/V1/Wifi/Network/Update` | `networkSSID, password` |
| Cloud | POST | `/V1/MQTT/Broker/Update` | `broker` |
| Time | PUT | `/V1/Time/Update` | `timestamp, offset` |
| Location | POST | `/V1/Location/Address/Add` | `address{...}` |
| Location | PUT | `/V1/Location/Address/Lookup` | `latitude, longitude` |
| Events | POST | `/V1/Events/DeviceEvents/Post` | `events[]` |

The bold rows are the ones a local geyser-control integration needs. **`Property/Update`** is the workhorse: `name` is one of `HeatingPolicy`, `SolarSetPoint`, `GridSetPoint`, `DeviceLabel`, `IsSolarInstalled`; `value` is the new setting. `HeatingPolicy` values seen in the app's own debug screen are **SolarOnly = 1** and **GridOnly = 5**. **`ForceReheat`** is the "boost / heat now" action and takes no extra fields. Responses are wrapped as `{ statusCode, message, data }` or carry an `OK`/`seqNo`.

## Data model

### Device status (`/V1/DeviceStatus/Query` → `deviceStatuses[]`)

This is what the current integration already reads. Confirmed against a real device: the thermostat answers a plain \`GET /V1/DeviceStatus/Query\` (no body, no auth) as well as the app's \`PUT\` form, so the local server is lenient about method and credentials. Fields confirmed in the response parser:

| Field | Meaning |
| --- | --- |
| `device` | device serial (integer) |
| `waterTemperature` | current temp, °C |
| `powerSource` | 1 = Solar, 2 = Grid (enum also has unknown/0) |
| `hasOpenAlarms` | boolean |
| `acNotPresent` | boolean (grid power missing) |
| `reheatTime` | minutes |
| `lastComms` | last contact timestamp |
| `logicalName` | user label |
| `streetAddress` | address string |

### Heating configuration (Property names)

`Property/Update` and `Property/Query` use these `name` values. `HeatingPolicy`: SolarOnly = 1, GridOnly = 5. Setpoints `SolarSetPoint` / `GridSetPoint` are target temperatures in °C. `IsSolarInstalled` is a boolean the device coerces from `true/yes/y/on/1`.

### Measurements / energy

Time-series reads use `sensorId`, `startWhen`, `endWhen`, `maximumSegmentLength`, `startOffset`, and page with `nextOffset`. Known sensor fields elsewhere in the app: `water_temp`, `ac_power`, `dc_power`, `ac_energy`, `dc_energy`, `rx_power`.

### Alarm codes

`geyser_empty`, `element_faulty`, `element_disconnect`, `earth_strap_not_connected`, `insulation_failure`, `insulation_self_test_failure`, `thermal_fuse_blown`, `thermal_regulation`, `lightning_damage`, `ambient_temperature_exceeded`, `max_panel_voltage_exceeded`, `dc_reverse_wired`, `dc_wired_to_ac_input`, `ac_wired_to_dc_input`, `dc_disconnect_failed`, `ac_not_present`, `dc_not_present`, `power_unstable`, `measurement_failure`, `water_temperature_measurement_failure`, `rtc_failed`, `switch_failed`, `no_route_to_server`.

## Home Assistant integration

The existing integration was read-only: it polled `/V1/DeviceStatus/Query` and exposed sensors. I added **local control** on the `add-local-control` branch, built directly on the recovered local API. New files: `api.py` (the local client), `entity.py` (shared base), and `button.py`, `number.py`, `select.py` (the control platforms).

**New entities, per device:**

| Entity | Platform | Local call |
| --- | --- | --- |
| Boost (Force Reheat) | button | `PUT /V1/Thermostat/ForceReheat` |
| Cancel Grid Heating | button | `PUT /V1/Thermostat/CancelGridHeating` |
| Heating Policy (Solar Only / Grid Only) | select | `PUT /V1/DeviceConfiguration/Property/Update` name=`HeatingPolicy` |
| Solar Setpoint (°C) | number | `Property/Update` name=`SolarSetPoint` |
| Grid Setpoint (°C) | number | `Property/Update` name=`GridSetPoint` |

Each control sends the exact method, path and JSON body recovered from the app, then refreshes the coordinator so the status sensors update. The `deviceSerial` is the integer `device` already present in each status row, so no extra configuration is needed to target a device.

**Auth handling.** The status read already works with no credentials, so `applicationId` and `authId` default to `0`. Two **optional** fields were added to the integration's Options (`application_id`, `auth_id`) for the case where a device enforces the handshake on its local port — a user can capture their own values and enter them. The request format is identical either way.

**What to verify on real hardware** (I can't test against a device here):

1. Whether the thermostat accepts control calls with `applicationId=0`/`authId=0`, or requires real handshake values.
2. The JSON type of `value` for `HeatingPolicy` — the app's debug screen sent it as a **string** (`"1"`, `"5"`) while the production enum holds integers; the setpoints' exact type is likewise unconfirmed. If a call is rejected, flipping `value` between int and string in `api.py` is a one-line change.
3. That `ForceReheat`/`CancelGridHeating` need no body beyond the three auth fields (confirmed in code, but device behaviour unverified).

The code is structured so these are isolated, low-risk adjustments. Nothing in the control path blocks the existing read-only sensors.

## Open questions and unverified items

- **Local control auth enforcement.** Unknown whether the thermostat validates `applicationId`/`authId` on its local port or (like the status read) ignores them. This is the single most important thing to confirm on a real device.
- **`value` JSON type** for `HeatingPolicy` and the setpoints — int vs string (see the HA section).
- **Full handshake wire format.** The sequence and signing scheme (RSA-OAEP/SHA-256, PointyCastle) are recovered, but the exact byte layout of the `secret` blob and what the `signed` field signs would need more work (or a packet capture) to reproduce the pairing from scratch rather than reusing captured IDs.
- **Cloud HTTP methods.** Most cloud `/portal/...` verbs weren't in a recovered request builder; only `set_label` (PATCH), `iot_access` (DELETE) and `version` (GET) are confirmed.
- **Measurements/energy query parameters.** Field names are known; the exact time encoding and `sensorId` values are not.
- **Capture to confirm everything at once.** A mitmproxy capture of the app against a device (past the cert pinning / RootBeer root checks, e.g. with reFlutter or a Frida hook) would validate every method, body type and the auth behaviour in one pass.

### Artefacts

- Decompiler output: `APK/blutter_out/` (`asm/`, `pp.txt`, `objs.txt`, `blutter_frida.js`, `ida_script/`).
- Whole-binary pool scanner and per-function disassembler used for this map: in the session scratchpad.
- Integration changes: branch `add-local-control` in `APK/homeassistant-elon-smart-water`.
