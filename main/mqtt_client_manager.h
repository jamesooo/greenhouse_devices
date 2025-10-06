/*
 * Greenhouse Devices - Shared MQTT Client Manager
 * Copyright 2025 jamesooo
 * Dual Licensed under MIT and Apache 2.0
 * 
 * This module provides shared MQTT client infrastructure for all devices.
 * It handles WiFi connection, MQTT broker connection, and auto-reconnection.
 */

#ifndef MQTT_CLIENT_MANAGER_H
#define MQTT_CLIENT_MANAGER_H

#include "mqtt_client.h"
#include <stdbool.h>

/**
 * Callback function types for device-specific MQTT handling
 */

// Called when MQTT client successfully connects to broker
typedef void (*mqtt_connected_cb_t)(esp_mqtt_client_handle_t client);

// Called when MQTT client disconnects from broker
typedef void (*mqtt_disconnected_cb_t)(void);

// Called when MQTT message is received (for subscriber devices)
typedef void (*mqtt_data_received_cb_t)(esp_mqtt_event_handle_t event);

/**
 * Configuration for device-specific MQTT behavior
 */
typedef struct {
    mqtt_connected_cb_t on_connected;           // Called when connected
    mqtt_disconnected_cb_t on_disconnected;     // Called when disconnected
    mqtt_data_received_cb_t on_data_received;   // Called when data received (optional)
} mqtt_device_callbacks_t;

/**
 * Initialize WiFi and connect to network
 * Must be called before mqtt_client_manager_init()
 * 
 * @return ESP_OK on success
 */
esp_err_t mqtt_client_manager_init_wifi(void);

/**
 * Initialize MQTT client with device-specific callbacks
 * WiFi must be connected before calling this function.
 * 
 * @param callbacks Device-specific callback functions
 * @return ESP_OK on success
 */
esp_err_t mqtt_client_manager_init(const mqtt_device_callbacks_t *callbacks);

/**
 * Get the MQTT client handle
 * Useful for devices that need to publish messages
 * 
 * @return MQTT client handle, or NULL if not initialized
 */
esp_mqtt_client_handle_t mqtt_client_manager_get_client(void);

/**
 * Check if MQTT client is currently connected
 * 
 * @return true if connected, false otherwise
 */
bool mqtt_client_manager_is_connected(void);

/**
 * Start the MQTT client
 * This is called automatically by mqtt_client_manager_init()
 * 
 * @return ESP_OK on success
 */
esp_err_t mqtt_client_manager_start(void);

/**
 * Stop the MQTT client
 * 
 * @return ESP_OK on success
 */
esp_err_t mqtt_client_manager_stop(void);

#endif // MQTT_CLIENT_MANAGER_H
