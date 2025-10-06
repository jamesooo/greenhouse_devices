#pragma once

#include "mqtt_client.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize the climate monitor device
 * 
 * This function initializes the BME680 sensor and prepares
 * the device for operation. It should be called after WiFi
 * and MQTT are initialized.
 * 
 * @param client MQTT client handle from mqtt_client_manager
 */
void climate_monitor_init(esp_mqtt_client_handle_t client);

/**
 * @brief Start the climate monitor sensor reading task
 * 
 * Starts a task that continuously reads the BME680 sensor
 * and publishes data to MQTT when connected.
 */
void climate_monitor_start(void);

/**
 * @brief Stop the climate monitor sensor reading task
 * 
 * Stops the sensor reading task and cleans up resources.
 */
void climate_monitor_stop(void);

#ifdef __cplusplus
}
#endif
