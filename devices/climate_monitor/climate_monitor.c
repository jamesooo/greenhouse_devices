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
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include <bme680.h>
#include <cJSON.h>
#include "nvs_flash.h"
#include "nvs.h"
#include "climate_monitor.h"
#include "mqtt_client_manager.h"
#include "env_config.h"

#define BME680_I2C_ADDR_1       0x77
#define BME680_I2C_SDA_PIN      4
#define BME680_I2C_SCL_PIN      5
#define BME680_I2C_FREQ_HZ     100000

// LM393 Soil Moisture Sensor (Analog Output)
// GPIO mapping is chip-specific due to different ADC channel layouts
#if CONFIG_IDF_TARGET_ESP32C3
    // ESP32-C3: ADC1_CHANNEL_1 = GPIO 1
    #define SOIL_MOISTURE_ADC_CHANNEL   ADC_CHANNEL_1
    #define SOIL_MOISTURE_GPIO_PIN      1
#elif CONFIG_IDF_TARGET_ESP32S3
    // ESP32-S3: ADC1_CHANNEL_0 = GPIO 1 (same physical pin!)
    #define SOIL_MOISTURE_ADC_CHANNEL   ADC_CHANNEL_0
    #define SOIL_MOISTURE_GPIO_PIN      1
#else
    #error "Unsupported target for soil moisture sensor"
#endif

#define SOIL_MOISTURE_ADC_ATTEN     ADC_ATTEN_DB_12  // 0-3100mV range
#define SOIL_MOISTURE_DRY_DEFAULT   2800  // Default ADC value when completely dry
#define SOIL_MOISTURE_WET_DEFAULT   1200  // Default ADC value when fully wet

static const char *TAG = "climate_monitor";

// Global state
static volatile bool sensor_running = false;
static TaskHandle_t sensor_task_handle = NULL;
static esp_mqtt_client_handle_t mqtt_client = NULL;
static bool sensor_initialized = false;
bme680_t sensor;  // BME680 sensor descriptor

// ADC for soil moisture
static adc_oneshot_unit_handle_t adc_handle = NULL;
static adc_cali_handle_t adc_cali_handle = NULL;

// NVS storage for calibration
#define NVS_NAMESPACE "soil_cal"
#define NVS_KEY_DRY_VALUE "dry_value"
#define NVS_KEY_WET_VALUE "wet_value"

// Soil moisture calibration values (can be updated via MQTT and persisted to NVS)
static int soil_moisture_dry_value = SOIL_MOISTURE_DRY_DEFAULT;
static int soil_moisture_wet_value = SOIL_MOISTURE_WET_DEFAULT;

// Forward declarations
static void sensor_task(void *pvParameters);
static void bme680_init(void);
static void bme680_cleanup(void);
static void bme680_read_and_publish(void);
static void soil_moisture_init(void);
static int soil_moisture_read_percent(void);

/**
 * Load soil moisture calibration values from NVS
 * Returns true if values were loaded, false if defaults are used
 */
static bool load_soil_calibration(void)
{
    nvs_handle_t nvs_handle;
    esp_err_t err;

    // Open NVS
    err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "[NVS] No calibration found, using defaults (dry=%d, wet=%d)", 
                 SOIL_MOISTURE_DRY_DEFAULT, SOIL_MOISTURE_WET_DEFAULT);
        soil_moisture_dry_value = SOIL_MOISTURE_DRY_DEFAULT;
        soil_moisture_wet_value = SOIL_MOISTURE_WET_DEFAULT;
        return false;
    }

    // Read dry value
    int32_t dry_val = SOIL_MOISTURE_DRY_DEFAULT;
    err = nvs_get_i32(nvs_handle, NVS_KEY_DRY_VALUE, &dry_val);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "[NVS] Failed to read dry_value, using default");
        dry_val = SOIL_MOISTURE_DRY_DEFAULT;
    }

    // Read wet value
    int32_t wet_val = SOIL_MOISTURE_WET_DEFAULT;
    err = nvs_get_i32(nvs_handle, NVS_KEY_WET_VALUE, &wet_val);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "[NVS] Failed to read wet_value, using default");
        wet_val = SOIL_MOISTURE_WET_DEFAULT;
    }

    nvs_close(nvs_handle);

    soil_moisture_dry_value = dry_val;
    soil_moisture_wet_value = wet_val;

    ESP_LOGI(TAG, "[NVS] Loaded calibration from storage (dry=%d, wet=%d)", 
             soil_moisture_dry_value, soil_moisture_wet_value);
    return true;
}

/**
 * Save soil moisture calibration values to NVS
 */
static esp_err_t save_soil_calibration(void)
{
    nvs_handle_t nvs_handle;
    esp_err_t err;

    // Open NVS in read-write mode
    err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[NVS] Failed to open NVS for writing: %s", esp_err_to_name(err));
        return err;
    }

    // Write dry value
    err = nvs_set_i32(nvs_handle, NVS_KEY_DRY_VALUE, soil_moisture_dry_value);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[NVS] Failed to write dry_value: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    // Write wet value
    err = nvs_set_i32(nvs_handle, NVS_KEY_WET_VALUE, soil_moisture_wet_value);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[NVS] Failed to write wet_value: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    // Commit changes
    err = nvs_commit(nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[NVS] Failed to commit: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    nvs_close(nvs_handle);

    ESP_LOGI(TAG, "[NVS] Saved calibration to storage (dry=%d, wet=%d)", 
             soil_moisture_dry_value, soil_moisture_wet_value);
    return ESP_OK;
}

/**
 * Initialize LM393 soil moisture sensor (Analog mode)
 */
static void soil_moisture_init(void)
{
    ESP_LOGI(TAG, "[LM393] Initializing soil moisture sensor in ANALOG mode");
    ESP_LOGI(TAG, "[LM393] Connect sensor A0 pin to GPIO %d", SOIL_MOISTURE_GPIO_PIN);
    
    // Configure ADC
    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = ADC_UNIT_1,
    };
    
    esp_err_t err = adc_oneshot_new_unit(&init_config, &adc_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[LM393] Failed to initialize ADC unit: %s", esp_err_to_name(err));
        return;
    }
    
    // Configure ADC channel
    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = SOIL_MOISTURE_ADC_ATTEN,
    };
    
    err = adc_oneshot_config_channel(adc_handle, SOIL_MOISTURE_ADC_CHANNEL, &config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[LM393] Failed to configure ADC channel: %s", esp_err_to_name(err));
        return;
    }
    
    // Set up ADC calibration for voltage reading (chip-specific)
#if CONFIG_IDF_TARGET_ESP32C3
    adc_cali_curve_fitting_config_t cali_config = {
        .unit_id = ADC_UNIT_1,
        .atten = SOIL_MOISTURE_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    
    err = adc_cali_create_scheme_curve_fitting(&cali_config, &adc_cali_handle);
#elif CONFIG_IDF_TARGET_ESP32S3
    adc_cali_line_fitting_config_t cali_config = {
        .unit_id = ADC_UNIT_1,
        .atten = SOIL_MOISTURE_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    
    err = adc_cali_create_scheme_line_fitting(&cali_config, &adc_cali_handle);
#else
    #error "Unsupported target for ADC calibration"
#endif
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "[LM393] ADC calibration failed, will use raw values: %s", esp_err_to_name(err));
        adc_cali_handle = NULL;
    }
    
    // Load calibration from NVS (or use defaults)
    load_soil_calibration();
    
    ESP_LOGI(TAG, "[LM393] Soil moisture sensor initialized successfully");
    ESP_LOGI(TAG, "[LM393] Calibration: Dry=%d, Wet=%d", 
             soil_moisture_dry_value, soil_moisture_wet_value);
}

/**
 * Read soil moisture sensor as percentage
 * @return Moisture percentage (0-100): 0=dry, 100=wet
 */
static int soil_moisture_read_percent(void)
{
    if (adc_handle == NULL) {
        ESP_LOGW(TAG, "[LM393] ADC not initialized");
        return -1;
    }
    
    int adc_raw = 0;
    esp_err_t err = adc_oneshot_read(adc_handle, SOIL_MOISTURE_ADC_CHANNEL, &adc_raw);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "[LM393] Failed to read ADC: %s", esp_err_to_name(err));
        return -1;
    }
    
    // Convert to voltage if calibration available
    int voltage = 0;
    if (adc_cali_handle != NULL) {
        adc_cali_raw_to_voltage(adc_cali_handle, adc_raw, &voltage);
        ESP_LOGD(TAG, "[LM393] ADC Raw: %d, Voltage: %d mV", adc_raw, voltage);
    }
    
    // Map ADC value to percentage (higher ADC = drier soil, so we invert)
    // Clamp values to calibration range
    if (adc_raw >= soil_moisture_dry_value) {
        return 0;  // Completely dry
    }
    if (adc_raw <= soil_moisture_wet_value) {
        return 100;  // Fully wet
    }
    
    // Linear interpolation: higher ADC value = drier soil = lower percentage
    int moisture_percent = 100 - ((adc_raw - soil_moisture_wet_value) * 100 / 
                                   (soil_moisture_dry_value - soil_moisture_wet_value));
    
    return moisture_percent;
}

/**
 * Initialize BME680 sensor
 */
static void bme680_init(void)
{
    ESP_LOGI(TAG, "[BME680] Initializing...");
    ESP_LOGI(TAG, "[BME680] Using I2C pins: SDA=GPIO%d, SCL=GPIO%d", BME680_I2C_SDA_PIN, BME680_I2C_SCL_PIN);
    ESP_LOGW(TAG, "[BME680] ⚠️  Check your wiring:");
    ESP_LOGW(TAG, "[BME680]    BME680 VCC → ESP32-C3 3.3V");
    ESP_LOGW(TAG, "[BME680]    BME680 GND → ESP32-C3 GND");
    ESP_LOGW(TAG, "[BME680]    BME680 SDA → ESP32-C3 GPIO %d", BME680_I2C_SDA_PIN);
    ESP_LOGW(TAG, "[BME680]    BME680 SCL → ESP32-C3 GPIO %d", BME680_I2C_SCL_PIN);
    
    memset(&sensor, 0, sizeof(bme680_t));
    int i2c_master_port = I2C_NUM_0;
    
    // Try address 0x77 first
    ESP_LOGI(TAG, "[BME680] Trying address 0x77...");
    esp_err_t err = bme680_init_desc(&sensor, BME680_I2C_ADDR_1, i2c_master_port, BME680_I2C_SDA_PIN, BME680_I2C_SCL_PIN);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "[BME680] Failed to init descriptor at 0x77: %s", esp_err_to_name(err));
        
        // Try address 0x76
        ESP_LOGI(TAG, "[BME680] Trying address 0x76...");
        memset(&sensor, 0, sizeof(bme680_t));
        err = bme680_init_desc(&sensor, 0x76, i2c_master_port, BME680_I2C_SDA_PIN, BME680_I2C_SCL_PIN);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "[BME680] Failed to init descriptor at 0x76: %s", esp_err_to_name(err));
            return;
        }
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
    
    // Configure sensor settings for maximum precision
    // OSR_16X = 16× oversampling (maximum) for temperature, humidity, and pressure
    // IIR_SIZE_127 = heaviest filtering for temporal smoothing
    // Expected precision: ±0.25°C temp, ±1.5% RH, ±0.3 hPa pressure
    bme680_set_oversampling_rates(&sensor, BME680_OSR_16X, BME680_OSR_16X, BME680_OSR_16X);
    bme680_set_filter_size(&sensor, BME680_IIR_SIZE_127);
    bme680_set_heater_profile(&sensor, 0, 200, 100);
    bme680_use_heater_profile(&sensor, 0);
    
    sensor_initialized = true;
    ESP_LOGI(TAG, "[BME680] Initialization successful (OSR_16X + IIR_127)");
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

        printf("BME680 Sensor: %.4f °C, %.4f %%, %.4f hPa, %.4f Ohm\n",
               values.temperature, values.humidity, values.pressure, values.gas_resistance);
        
        // Read soil moisture sensor (0-100%)
        int soil_moisture_percent = soil_moisture_read_percent();
        
        // Only publish if MQTT is connected
        if (mqtt_client_manager_is_connected() && mqtt_client) {
            // Create JSON payload with all sensor readings, soil moisture percentage, and device ID
            char json_payload[512];
            snprintf(json_payload, sizeof(json_payload),
                    "{\"device_id\":\"%s\",\"temperature\":%.2f,\"humidity\":%.2f,\"pressure\":%.2f,\"gas_resistance\":%.2f,\"soil_moisture\":%d,\"location_x\":%d,\"location_y\":%d}",
                    CONFIG_DEVICE_ID,
                    values.temperature, values.humidity, values.pressure, values.gas_resistance,
                    soil_moisture_percent,
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
 * Handle MQTT config message to update calibration values
 */
static void handle_config_message(const char *data, int data_len)
{
    ESP_LOGI(TAG, "[MQTT] Received config message: %.*s", data_len, data);
    
    // Parse JSON: {"dry_value": 2800, "wet_value": 1200}
    cJSON *json = cJSON_ParseWithLength(data, data_len);
    if (json == NULL) {
        ESP_LOGW(TAG, "[MQTT] Failed to parse config JSON");
        return;
    }
    
    bool updated = false;
    
    cJSON *dry_item = cJSON_GetObjectItem(json, "dry_value");
    if (cJSON_IsNumber(dry_item)) {
        soil_moisture_dry_value = dry_item->valueint;
        ESP_LOGI(TAG, "[MQTT] Updated dry_value=%d", soil_moisture_dry_value);
        updated = true;
    }
    
    cJSON *wet_item = cJSON_GetObjectItem(json, "wet_value");
    if (cJSON_IsNumber(wet_item)) {
        soil_moisture_wet_value = wet_item->valueint;
        ESP_LOGI(TAG, "[MQTT] Updated wet_value=%d", soil_moisture_wet_value);
        updated = true;
    }
    
    cJSON_Delete(json);
    
    // Save to NVS if values were updated
    if (updated) {
        esp_err_t err = save_soil_calibration();
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "[MQTT] Calibration saved to NVS");
        } else {
            ESP_LOGE(TAG, "[MQTT] Failed to save calibration to NVS");
        }
    }
}

/**
 * MQTT data received callback
 */
static void on_data_received(esp_mqtt_event_handle_t event)
{
    // Check if this is a config message for our device
    char topic[128];
    snprintf(topic, sizeof(topic), "sensor/config/%s", CONFIG_DEVICE_ID);
    
    if (event->topic_len == strlen(topic) && 
        strncmp(event->topic, topic, event->topic_len) == 0) {
        handle_config_message(event->data, event->data_len);
    }
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
    
    // Initialize soil moisture sensor
    soil_moisture_init();
    
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

/**
 * Subscribe to config topic for this device
 */
void climate_monitor_subscribe_config(void)
{
    if (mqtt_client == NULL) {
        ESP_LOGW(TAG, "[MQTT] Cannot subscribe - MQTT client not initialized");
        return;
    }
    
    char topic[128];
    snprintf(topic, sizeof(topic), "sensor/config/%s", CONFIG_DEVICE_ID);
    
    esp_mqtt_client_subscribe(mqtt_client, topic, 1);
    ESP_LOGI(TAG, "[MQTT] Subscribed to config topic: %s", topic);
}

/**
 * Get the MQTT data received callback
 */
void* climate_monitor_get_data_callback(void)
{
    return (void*)on_data_received;
}
