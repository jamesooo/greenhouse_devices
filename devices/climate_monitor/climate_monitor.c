/*
 * Climate Monitor Device - BME680 Sensor Reader
 * Copyright 2025 jamesooo
 * Dual Licensed under MIT and Apache 2.0
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "esp_system.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <bme680.h>
#include "climate_monitor.h"
#include "mqtt_client_manager.h"
#include "env_config.h"

#define BME680_I2C_ADDR_1       0x77
#define BME680_I2C_SDA_PIN      17
#define BME680_I2C_SCL_PIN      18
#define BME680_I2C_FREQ_HZ     100000

static const char *TAG = "climate_monitor";

// Global state
static volatile bool sensor_running = false;
static TaskHandle_t sensor_task_handle = NULL;
static esp_mqtt_client_handle_t mqtt_client = NULL;
static bool sensor_initialized = false;
bme680_t sensor;  // BME680 sensor descriptor

// Forward declarations
static void sensor_task(void *pvParameters);
static void bme680_init(void);
static void bme680_cleanup(void);
static void bme680_read_and_publish(void);

/**
 * Initialize BME680 sensor
 */
static void bme680_init(void)
{
    ESP_LOGI(TAG, "[BME680] Initializing...");
    
    memset(&sensor, 0, sizeof(bme680_t));
    int i2c_master_port = I2C_NUM_0;
    
    // Enable pullup resistors on SDA and SCL lines
    esp_err_t err = bme680_init_desc(&sensor, BME680_I2C_ADDR_1, i2c_master_port, BME680_I2C_SDA_PIN, BME680_I2C_SCL_PIN);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[BME680] Failed to init descriptor: %s", esp_err_to_name(err));
        return;
    }
    
    sensor.i2c_dev.cfg.scl_pullup_en = 1; // Enable internal pull-up for SCL
    sensor.i2c_dev.cfg.sda_pullup_en = 1; // Enable internal pull-up for SDA
    sensor.i2c_dev.cfg.master.clk_speed = BME680_I2C_FREQ_HZ;
    
    // Perform a soft reset to ensure sensor is in a known state
    err = bme680_init_sensor(&sensor);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[BME680] Failed to init sensor: %s", esp_err_to_name(err));
        // Clean up the descriptor
        i2c_dev_delete_mutex(&sensor.i2c_dev);
        return;
    }
    
    // Wait a bit for sensor to stabilize after reset
    vTaskDelay(pdMS_TO_TICKS(100));
    
    // Configure sensor settings
    bme680_set_oversampling_rates(&sensor, BME680_OSR_4X, BME680_OSR_2X, BME680_OSR_2X);
    bme680_set_filter_size(&sensor, BME680_IIR_SIZE_7);
    bme680_set_heater_profile(&sensor, 0, 200, 100);
    bme680_use_heater_profile(&sensor, 0);
    
    sensor_initialized = true;
    ESP_LOGI(TAG, "[BME680] Initialization successful");
}

/**
 * Cleanup BME680 sensor
 */
static void bme680_cleanup(void)
{
    ESP_LOGI(TAG, "[BME680] Cleaning up I2C connection...");
    
    // Always try to delete the mutex if it exists
    if (sensor.i2c_dev.mutex != NULL) {
        esp_err_t err = i2c_dev_delete_mutex(&sensor.i2c_dev);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "[BME680] Failed to cleanup I2C device: %s", esp_err_to_name(err));
        } else {
            ESP_LOGI(TAG, "[BME680] I2C connection cleaned up successfully");
        }
    }
    
    sensor_initialized = false;
    memset(&sensor, 0, sizeof(bme680_t));
}

/**
 * Read sensor and publish to MQTT if connected
 */
static void bme680_read_and_publish(void)
{
    // Get measurement duration
    uint32_t duration;
    bme680_get_measurement_duration(&sensor, &duration);

    TickType_t last_wakeup = xTaskGetTickCount();
    float temperature = 10;
    bme680_values_float_t values;
    int consecutive_errors = 0;
    const int MAX_CONSECUTIVE_ERRORS = 3;
    int reinit_attempts = 0;
    const int MAX_REINIT_ATTEMPTS = 5;
    
    ESP_LOGI(TAG, "Starting sensor reading loop");
    
    while (sensor_running) {
        // Check if sensor is properly initialized
        if (!sensor_initialized) {
            ESP_LOGW(TAG, "Sensor not initialized, attempting initialization...");
            bme680_cleanup(); // Clean up any partial state
            vTaskDelay(pdMS_TO_TICKS(2000));
            bme680_init();
            
            if (!sensor_initialized) {
                reinit_attempts++;
                if (reinit_attempts >= MAX_REINIT_ATTEMPTS) {
                    ESP_LOGE(TAG, "Failed to initialize sensor after %d attempts, waiting longer...", reinit_attempts);
                    vTaskDelay(pdMS_TO_TICKS(10000));
                    reinit_attempts = 0;
                } else {
                    vTaskDelay(pdMS_TO_TICKS(3000));
                }
                continue;
            }
            
            consecutive_errors = 0;
            reinit_attempts = 0;
            bme680_get_measurement_duration(&sensor, &duration);
            ESP_LOGI(TAG, "Sensor initialized successfully, resuming measurements");
        }
        
        bme680_set_ambient_temperature(&sensor, temperature);
        
        // Trigger measurement
        esp_err_t err = bme680_force_measurement(&sensor);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Failed to force measurement: %s", esp_err_to_name(err));
            consecutive_errors++;
            
            if (consecutive_errors >= MAX_CONSECUTIVE_ERRORS) {
                ESP_LOGE(TAG, "Too many consecutive errors (%d), reinitializing sensor...", consecutive_errors);
                bme680_cleanup();
                consecutive_errors = 0;
            } else {
                vTaskDelay(pdMS_TO_TICKS(500));
            }
            continue;
        }

        // Wait for measurement
        vTaskDelay(duration);

        // Get results
        err = bme680_get_results_float(&sensor, &values);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Failed to get results: %s", esp_err_to_name(err));
            consecutive_errors++;
            
            if (consecutive_errors >= MAX_CONSECUTIVE_ERRORS) {
                ESP_LOGE(TAG, "Too many consecutive errors (%d), reinitializing sensor...", consecutive_errors);
                bme680_cleanup();
                consecutive_errors = 0;
            } else {
                vTaskDelay(pdMS_TO_TICKS(500));
            }
            continue;
        }
        
        // Success - reset error counters
        consecutive_errors = 0;
        reinit_attempts = 0;
        
        printf("BME680 Sensor: %.2f °C, %.2f %%, %.2f hPa, %.2f Ohm\n",
               values.temperature, values.humidity, values.pressure, values.gas_resistance);
        
        // Only publish if MQTT is connected
        if (mqtt_client_manager_is_connected() && mqtt_client) {
            // Create JSON payload with all sensor readings and device ID
            char json_payload[512];
            snprintf(json_payload, sizeof(json_payload),
                    "{\"device_id\":\"%s\",\"temperature\":%.2f,\"humidity\":%.2f,\"pressure\":%.2f,\"gas_resistance\":%.2f,\"location_x\":%d,\"location_y\":%d}",
                    CONFIG_DEVICE_ID,
                    values.temperature, values.humidity, values.pressure, values.gas_resistance,
                    CONFIG_DEVICE_LOCATION_X, CONFIG_DEVICE_LOCATION_Y);
            
            // Publish climate data
            int msg_id = esp_mqtt_client_publish(mqtt_client, "sensor/climate", json_payload, 0, 1, 0);
            if (msg_id < 0) {
                ESP_LOGW(TAG, "Failed to publish climate data, will retry on next reading");
            }
            
            // Publish heartbeat
            char heartbeat_payload[128];
            snprintf(heartbeat_payload, sizeof(heartbeat_payload),
                    "{\"device_id\":\"%s\",\"status\":\"alive\"}",
                    CONFIG_DEVICE_ID);
            esp_mqtt_client_publish(mqtt_client, "sensor/heartbeat", heartbeat_payload, 0, 1, 0);
        } else {
            ESP_LOGD(TAG, "MQTT not connected, dropping reading (temp: %.2f °C)", values.temperature);
        }
        
        // Use temperature for next measurement
        temperature = values.temperature;
        
        // Wait 1 second between readings
        vTaskDelayUntil(&last_wakeup, pdMS_TO_TICKS(1000));
    }
    
    ESP_LOGI(TAG, "Sensor reading loop stopped");
}

/**
 * Sensor task wrapper
 */
static void sensor_task(void *pvParameters)
{
    bme680_read_and_publish();
    sensor_task_handle = NULL;
    vTaskDelete(NULL);
}

/**
 * Initialize climate monitor
 */
void climate_monitor_init(esp_mqtt_client_handle_t client)
{
    ESP_LOGI(TAG, "Initializing climate monitor device");
    ESP_LOGI(TAG, "Device ID: %s", CONFIG_DEVICE_ID);
    ESP_LOGI(TAG, "Location: (%d, %d)", CONFIG_DEVICE_LOCATION_X, CONFIG_DEVICE_LOCATION_Y);
    
    mqtt_client = client;
    
    // Initialize I2C device library
    ESP_ERROR_CHECK(i2cdev_init());
    
    // Initialize BME680 sensor
    bme680_init();
}

/**
 * Start climate monitor task
 */
void climate_monitor_start(void)
{
    if (!sensor_running && sensor_task_handle == NULL) {
        sensor_running = true;
        xTaskCreate(sensor_task, "sensor_task", 4096, NULL, 5, &sensor_task_handle);
        ESP_LOGI(TAG, "Started sensor task");
    }
}

/**
 * Stop climate monitor task
 */
void climate_monitor_stop(void)
{
    if (sensor_running) {
        sensor_running = false;
        ESP_LOGI(TAG, "Stopping sensor task");
        
        // Wait for the task to finish (up to 2 seconds)
        int wait_count = 0;
        while (sensor_task_handle != NULL && wait_count < 20) {
            vTaskDelay(pdMS_TO_TICKS(100));
            wait_count++;
        }
        
        if (sensor_task_handle == NULL) {
            ESP_LOGI(TAG, "Sensor task stopped successfully");
        } else {
            ESP_LOGW(TAG, "Sensor task did not stop in time");
        }
    }
    
    // Cleanup I2C connection
    bme680_cleanup();
}
