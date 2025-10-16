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
 * @brief Subscribe to config topic for calibration updates
 * 
 * Should be called after MQTT connection is established.
 * Subscribes to: sensor/config/{device_id}
 */
void climate_monitor_subscribe_config(void);

/**
 * @brief Get the MQTT data received callback
 * 
 * @return Function pointer to on_data_received callback
 */
void* climate_monitor_get_data_callback(void);

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
