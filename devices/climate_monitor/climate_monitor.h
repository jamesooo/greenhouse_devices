#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize and run the climate monitor device
 * 
 * This function starts the climate monitor main loop which:
 * - Connects to WiFi
 * - Connects to MQTT broker
 * - Reads BME680 sensor data
 * - Publishes sensor data via MQTT
 */
void climate_monitor_run(void);

#ifdef __cplusplus
}
#endif
