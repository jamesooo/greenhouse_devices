/*
 * Greenhouse Devices - Multi-Device Entry Point
 * Copyright 2025 jamesooo
 * Dual Licensed under MIT and Apache 2.0
 */

#include "esp_log.h"
#include "mqtt_client_manager.h"

// Include device headers
#include "climate_monitor/climate_monitor.h"
// Future devices:
// #include "humidifier/humidifier.h"
// #include "light_controller/light_controller.h"

static const char *TAG = "DEVICE_SELECTOR";

// MQTT connection callback - called when connected to broker
static void on_mqtt_connected(esp_mqtt_client_handle_t client)
{
    ESP_LOGI(TAG, "Device connected to MQTT broker");
    
    #if defined(CONFIG_DEVICE_CLIMATE_MONITOR)
        climate_monitor_subscribe_config();
        climate_monitor_start();
    #endif
}

// MQTT disconnection callback - called when disconnected from broker
static void on_mqtt_disconnected(void)
{
    ESP_LOGI(TAG, "Device disconnected from MQTT broker");
    
    #if defined(CONFIG_DEVICE_CLIMATE_MONITOR)
        // Stop the climate monitor sensor task
        climate_monitor_stop();
    #endif
}

void app_main(void)
{
    ESP_LOGI(TAG, "Greenhouse Device Firmware");
    ESP_LOGI(TAG, "Build Date: %s %s", __DATE__, __TIME__);
    
    // Initialize WiFi first
    ESP_ERROR_CHECK(mqtt_client_manager_init_wifi());
    
    // Set up device-specific MQTT callbacks
    mqtt_device_callbacks_t callbacks = {
        .on_connected = on_mqtt_connected,
        .on_disconnected = on_mqtt_disconnected,
        #if defined(CONFIG_DEVICE_CLIMATE_MONITOR)
            .on_data_received = (mqtt_data_received_cb_t)climate_monitor_get_data_callback(),
        #else
            .on_data_received = NULL,
        #endif
    };
    
    // Initialize MQTT client manager
    ESP_ERROR_CHECK(mqtt_client_manager_init(&callbacks));
    
    // Select and initialize device based on compile-time configuration
    #if defined(CONFIG_DEVICE_CLIMATE_MONITOR)
        ESP_LOGI(TAG, "Initializing Climate Monitor Device");
        climate_monitor_init(mqtt_client_manager_get_client());
    
    #elif defined(CONFIG_DEVICE_HUMIDIFIER)
        ESP_LOGI(TAG, "Initializing Humidifier Device");
        // humidifier_init(mqtt_client_manager_get_client());  // TODO: Implement
        ESP_LOGE(TAG, "Humidifier device not yet implemented!");
    
    #elif defined(CONFIG_DEVICE_LIGHT_CONTROLLER)
        ESP_LOGI(TAG, "Initializing Light Controller Device");
        // light_controller_init(mqtt_client_manager_get_client());  // TODO: Implement
        ESP_LOGE(TAG, "Light controller device not yet implemented!");
    
    #else
        #error "No device type selected! Run 'idf.py menuconfig' and select a device type."
    #endif
    
    // Start MQTT client (will auto-connect and trigger on_mqtt_connected callback)
    ESP_ERROR_CHECK(mqtt_client_manager_start());
    
    ESP_LOGI(TAG, "Device initialization complete");
}
