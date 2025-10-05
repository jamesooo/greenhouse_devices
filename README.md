| Supported Targets | ESP32 | ESP32-C2 | ESP32-C3 | ESP32-C5 | ESP32-C6 | ESP32-C61 | ESP32-H2 | ESP32-P4 | ESP32-S2 | ESP32-S3 |
| ----------------- | ----- | -------- | -------- | -------- | -------- | --------- | -------- | -------- | -------- | -------- |

Currently developed on ESP32-S3

# ESP-MQTT Environment Management System
A system for monitoring and responding to changes in the environment.

Currently the project supports publishing of climate metrics from a BME680 to a Grafana dashboard. In the future this will include many of these monitors, light, humidity, ventiliation controls, and a lot more.

This project is built on top of ESP-IDF's MQTT example device.

It uses ESP-MQTT library which implements mqtt client to connect to mqtt broker with MQTT version 5.

The more details about MQTT v5, please refer to [official website](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)

## How to use example

### Hardware Required

This example can be executed on any ESP32 board, the only required interface is WiFi and connection to internet.

### Configure the project

* Open the project configuration menu (`idf.py menuconfig`)
* Configure Wi-Fi or Ethernet under "Example Connection Configuration" menu. See "Establishing Wi-Fi or Ethernet Connection" section in [examples/protocols/README.md](../../README.md) for more details.
* MQTT v5 protocol (`CONFIG_MQTT_PROTOCOL_5`) under "ESP-MQTT Configurations" menu is enabled by `sdkconfig.defaults`.

### Build, Flash, and Monitor

Build the project and flash it to the board, then run monitor tool to view serial output:

```
./script/build_flash_monitor
```
