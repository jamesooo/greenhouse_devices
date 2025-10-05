/*
 * Greenhouse Devices - Multi-Device Entry Point
 * Copyright 2025 jamesooo
 * Dual Licensed under MIT and Apache 2.0
 */

#include "esp_log.h"

// Include device headers
#include "climate_monitor/climate_monitor.h"
// Future devices:
// #include "humidifier/humidifier.h"
// #include "light_controller/light_controller.h"

static const char *TAG = "DEVICE_SELECTOR";

void app_main(void)
{
    ESP_LOGI(TAG, "Greenhouse Device Firmware");
    ESP_LOGI(TAG, "Build Date: %s %s", __DATE__, __TIME__);
    
    // Select which device to run based on compile-time configuration
    #if defined(CONFIG_DEVICE_CLIMATE_MONITOR)
        ESP_LOGI(TAG, "Starting Climate Monitor Device");
        climate_monitor_run();
    
    #elif defined(CONFIG_DEVICE_HUMIDIFIER)
        ESP_LOGI(TAG, "Starting Humidifier Device");
        // humidifier_run();  // TODO: Implement
        ESP_LOGE(TAG, "Humidifier device not yet implemented!");
    
    #elif defined(CONFIG_DEVICE_LIGHT_CONTROLLER)
        ESP_LOGI(TAG, "Starting Light Controller Device");
        // light_controller_run();  // TODO: Implement
        ESP_LOGE(TAG, "Light controller device not yet implemented!");
    
    #else
        #error "No device type selected! Run 'idf.py menuconfig' and select a device type."
    #endif
}
