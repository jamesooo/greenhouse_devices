/*
 * SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "protocol_examples_common.h"
#include "esp_log.h"
#include "mqtt_client.h"

#include <bme680.h>
#include "climate_monitor.h"

#define BME680_I2C_ADDR_0       0x76
#define BME680_I2C_ADDR_1       0x77
#define BME680_I2C_SDA_PIN      17
#define BME680_I2C_SCL_PIN      18
#define BME680_I2C_FREQ_HZ     100000

static const char *TAG = "bme680_mqtt5";

#include "env_config.h"

// Global state
static volatile bool sensor_running = false;
static TaskHandle_t sensor_task_handle = NULL;
static esp_mqtt_client_handle_t mqtt_client = NULL;
static bool sensor_initialized = false;
bme680_t sensor;  // BME680 sensor descriptor

// Forward declarations
void sensor_task(void *pvParameters);
void bme680_init(void);
void bme680_cleanup(void);

static void log_error_if_nonzero(const char *message, int error_code)
{
    if (error_code != 0) {
        ESP_LOGE(TAG, "Last error %s: 0x%x", message, error_code);
    }
}

static esp_mqtt5_user_property_item_t user_property_arr[] = {
        {"board", "esp32"},
        {"u", "user"},
        {"p", "password"}
    };

#define USE_PROPERTY_ARR_SIZE   sizeof(user_property_arr)/sizeof(esp_mqtt5_user_property_item_t)

static void print_user_property(mqtt5_user_property_handle_t user_property)
{
    if (user_property) {
        uint8_t count = esp_mqtt5_client_get_user_property_count(user_property);
        if (count) {
            esp_mqtt5_user_property_item_t *item = malloc(count * sizeof(esp_mqtt5_user_property_item_t));
            if (esp_mqtt5_client_get_user_property(user_property, item, &count) == ESP_OK) {
                for (int i = 0; i < count; i ++) {
                    esp_mqtt5_user_property_item_t *t = &item[i];
                    ESP_LOGI(TAG, "key is %s, value is %s", t->key, t->value);
                    free((char *)t->key);
                    free((char *)t->value);
                }
            }
            free(item);
        }
    }
}

/*
 * @brief Event handler registered to receive MQTT events
 *
 *  This function is called by the MQTT client event loop.
 *
 * @param handler_args user data registered to the event.
 * @param base Event base for the handler(always MQTT Base in this example).
 * @param event_id The id for the received event.
 * @param event_data The data for the event, esp_mqtt_event_handle_t.
 */
static void mqtt5_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    ESP_LOGD(TAG, "Event dispatched from event loop base=%s, event_id=%" PRIi32, base, event_id);
    esp_mqtt_event_handle_t event = event_data;
    esp_mqtt_client_handle_t client = event->client;
    int msg_id;

    ESP_LOGD(TAG, "free heap size is %" PRIu32 ", minimum %" PRIu32, esp_get_free_heap_size(), esp_get_minimum_free_heap_size());
    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
        print_user_property(event->property->user_property);
        
        // Subscribe to control topic for leave commands
        msg_id = esp_mqtt_client_subscribe(client, "sensor/control", 1);
        ESP_LOGI(TAG, "Subscribed to control topic, msg_id=%d", msg_id);
        
        // Re-initialize sensor if needed (e.g., after a leave command)
        if (!sensor_initialized) {
            bme680_init();
        }
        
        // Start sensor reading task
        if (!sensor_running && sensor_task_handle == NULL) {
            sensor_running = true;
            xTaskCreate(sensor_task, "sensor_task", 4096, NULL, 5, &sensor_task_handle);
            ESP_LOGI(TAG, "Started sensor task");
        }
        break;
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "MQTT_EVENT_DISCONNECTED");
        print_user_property(event->property->user_property);
        
        // Stop sensor reading task
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
        break;
    case MQTT_EVENT_SUBSCRIBED:
        ESP_LOGI(TAG, "MQTT_EVENT_SUBSCRIBED, msg_id=%d", event->msg_id);
        print_user_property(event->property->user_property);
        break;
    case MQTT_EVENT_UNSUBSCRIBED:
        ESP_LOGI(TAG, "MQTT_EVENT_UNSUBSCRIBED, msg_id=%d", event->msg_id);
        print_user_property(event->property->user_property);
        break;
    case MQTT_EVENT_PUBLISHED:
        ESP_LOGI(TAG, "MQTT_EVENT_PUBLISHED, msg_id=%d", event->msg_id);
        print_user_property(event->property->user_property);
        break;
    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "MQTT_EVENT_DATA");
        print_user_property(event->property->user_property);
        ESP_LOGI(TAG, "TOPIC=%.*s", event->topic_len, event->topic);
        ESP_LOGI(TAG, "DATA=%.*s", event->data_len, event->data);
        
        // Check if this is a leave command on the control topic
        if (event->topic_len >= 14 && strncmp(event->topic, "sensor/control", 14) == 0) {
            if (event->data_len >= 5 && strncmp(event->data, "leave", 5) == 0) {
                ESP_LOGI(TAG, "Received leave command, stopping sensor task and cleaning up");
                sensor_running = false;
                
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
                
                // Cleanup I2C connection
                bme680_cleanup();
            }
        }
        break;
    case MQTT_EVENT_ERROR:
        ESP_LOGI(TAG, "MQTT_EVENT_ERROR");
        print_user_property(event->property->user_property);
        ESP_LOGI(TAG, "MQTT5 return code is %d", event->error_handle->connect_return_code);
        if (event->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
            log_error_if_nonzero("reported from esp-tls", event->error_handle->esp_tls_last_esp_err);
            log_error_if_nonzero("reported from tls stack", event->error_handle->esp_tls_stack_err);
            log_error_if_nonzero("captured as transport's socket errno",  event->error_handle->esp_transport_sock_errno);
            ESP_LOGI(TAG, "Last errno string (%s)", strerror(event->error_handle->esp_transport_sock_errno));
        }
        break;
    default:
        ESP_LOGI(TAG, "Other event id:%d", event->event_id);
        break;
    }
}

static void mqtt5_app_start(void)
{
    esp_mqtt5_connection_property_config_t connect_property = {
        .session_expiry_interval = 10,
        .maximum_packet_size = 1024,
        .receive_maximum = 65535,
        .topic_alias_maximum = 2,
        .request_resp_info = true,
        .request_problem_info = true,
        .will_delay_interval = 10,
        .payload_format_indicator = true,
        .message_expiry_interval = 10,
        .response_topic = "/test/response",
        .correlation_data = "123456",
        .correlation_data_len = 6,
    };

    esp_mqtt_client_config_t mqtt5_cfg = {
        .broker.address.uri = ENV_DEVICE_MQTT_BROKER_URL,
        .session.protocol_ver = MQTT_PROTOCOL_V_5,
        .network.disable_auto_reconnect = true,
        //.credentials.username = "123",
        //.credentials.authentication.password = "456",
        .session.last_will.topic = "/topic/will",
        .session.last_will.msg = "i will leave",
        .session.last_will.msg_len = 12,
        .session.last_will.qos = 1,
        .session.last_will.retain = true,
    };

#if CONFIG_BROKER_URL_FROM_STDIN
    char line[128];

    if (strcmp(mqtt5_cfg.uri, "FROM_STDIN") == 0) {
        int count = 0;
        printf("Please enter url of mqtt broker\n");
        while (count < 128) {
            int c = fgetc(stdin);
            if (c == '\n') {
                line[count] = '\0';
                break;
            } else if (c > 0 && c < 127) {
                line[count] = c;
                ++count;
            }
            vTaskDelay(10 / portTICK_PERIOD_MS);
        }
        mqtt5_cfg.broker.address.uri = line;
        printf("Broker url: %s\n", line);
    } else {
        ESP_LOGE(TAG, "Configuration mismatch: wrong broker url");
        abort();
    }
#endif /* CONFIG_BROKER_URL_FROM_STDIN */

    esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt5_cfg);
    
    // Store client handle globally
    mqtt_client = client;

    /* Set connection properties and user properties */
    esp_mqtt5_client_set_user_property(&connect_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
    esp_mqtt5_client_set_user_property(&connect_property.will_user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
    esp_mqtt5_client_set_connect_property(client, &connect_property);

    /* If you call esp_mqtt5_client_set_user_property to set user properties, DO NOT forget to delete them.
     * esp_mqtt5_client_set_connect_property will malloc buffer to store the user_property and you can delete it after
     */
    esp_mqtt5_client_delete_user_property(connect_property.user_property);
    esp_mqtt5_client_delete_user_property(connect_property.will_user_property);

    /* The last argument may be used to pass data to the event handler, in this example mqtt_event_handler */
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt5_event_handler, NULL);
    esp_mqtt_client_start(client);
}

void bme680_init(void)
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

void bme680_cleanup(void)
{
    ESP_LOGI(TAG, "[BME680] Cleaning up I2C connection...");
    
    // Always try to delete the mutex if it exists, even if sensor_initialized is false
    // This handles the case where init partially succeeded
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

void check_bme680(esp_mqtt_client_handle_t client)
{
    // Get measurement duration (constant as long as sensor config doesn't change)
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
        // Check if sensor is properly initialized before attempting operations
        if (!sensor_initialized) {
            ESP_LOGW(TAG, "Sensor not initialized, attempting initialization...");
            bme680_cleanup(); // Clean up any partial state
            vTaskDelay(pdMS_TO_TICKS(2000)); // Wait before reinit
            bme680_init();
            
            if (!sensor_initialized) {
                reinit_attempts++;
                if (reinit_attempts >= MAX_REINIT_ATTEMPTS) {
                    ESP_LOGE(TAG, "Failed to initialize sensor after %d attempts, waiting longer...", reinit_attempts);
                    vTaskDelay(pdMS_TO_TICKS(10000)); // Wait 10 seconds before trying again
                    reinit_attempts = 0;
                } else {
                    vTaskDelay(pdMS_TO_TICKS(3000)); // Wait 3 seconds before next attempt
                }
                continue;
            }
            
            // Successfully initialized, reset counters and recalculate duration
            consecutive_errors = 0;
            reinit_attempts = 0;
            bme680_get_measurement_duration(&sensor, &duration);
            ESP_LOGI(TAG, "Sensor initialized successfully, resuming measurements");
        }
        
        bme680_set_ambient_temperature(&sensor, temperature);
        
        // trigger the sensor to start one TPHG measurement cycle
        esp_err_t err = bme680_force_measurement(&sensor);
        if (err != ESP_OK)
        {
            ESP_LOGW(TAG, "Failed to force measurement: %s", esp_err_to_name(err));
            consecutive_errors++;
            
            if (consecutive_errors >= MAX_CONSECUTIVE_ERRORS) {
                ESP_LOGE(TAG, "Too many consecutive errors (%d), reinitializing sensor...", consecutive_errors);
                bme680_cleanup();
                consecutive_errors = 0;
                // Loop will check sensor_initialized on next iteration
            } else {
                vTaskDelay(pdMS_TO_TICKS(500)); // Short delay before retry
            }
            continue;
        }

        // passive waiting until measurement results are available
        vTaskDelay(duration);

        // get the results and do something with them
        err = bme680_get_results_float(&sensor, &values);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Failed to get results: %s", esp_err_to_name(err));
            consecutive_errors++;
            
            if (consecutive_errors >= MAX_CONSECUTIVE_ERRORS) {
                ESP_LOGE(TAG, "Too many consecutive errors (%d), reinitializing sensor...", consecutive_errors);
                bme680_cleanup();
                consecutive_errors = 0;
                // Loop will check sensor_initialized on next iteration
            } else {
                vTaskDelay(pdMS_TO_TICKS(500)); // Short delay before retry
            }
            continue;
        }
        
        // Success - reset error counters
        consecutive_errors = 0;
        reinit_attempts = 0;
        
        printf("BME680 Sensor: %.2f °C, %.2f %%, %.2f hPa, %.2f Ohm\n",
               values.temperature, values.humidity, values.pressure, values.gas_resistance);
        
        // Create JSON payload with all sensor readings
        char json_payload[256];
        snprintf(json_payload, sizeof(json_payload),
                "{\"temperature\":%.2f,\"humidity\":%.2f,\"pressure\":%.2f,\"gas_resistance\":%.2f}",
                values.temperature, values.humidity, values.pressure, values.gas_resistance);
        
        // Publish as single JSON message
        esp_mqtt_client_publish(client, "sensor/climate", json_payload, 0, 1, 0);
        
        // Publish heartbeat as JSON
        esp_mqtt_client_publish(client, "sensor/heartbeat", "{\"status\":\"alive\"}", 0, 1, 0);
        
        // use temperature value to change ambient temperature for next measurement
        temperature = values.temperature;
        
        // passive waiting until 1 second is over
        vTaskDelayUntil(&last_wakeup, pdMS_TO_TICKS(1000));
    }
    
    ESP_LOGI(TAG, "Sensor reading loop stopped");
}

// Task wrapper for sensor reading
void sensor_task(void *pvParameters)
{
    check_bme680(mqtt_client);
    sensor_task_handle = NULL;
    vTaskDelete(NULL);
}

void climate_monitor_run(void)
{

    ESP_LOGI(TAG, "[APP] Startup..");
    ESP_LOGI(TAG, "[APP] Free memory: %" PRIu32 " bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "[APP] IDF version: %s", esp_get_idf_version());

    esp_log_level_set("*", ESP_LOG_INFO);
    esp_log_level_set("mqtt_client", ESP_LOG_VERBOSE);
    esp_log_level_set("mqtt_example", ESP_LOG_VERBOSE);
    esp_log_level_set("transport_base", ESP_LOG_VERBOSE);
    esp_log_level_set("esp-tls", ESP_LOG_VERBOSE);
    esp_log_level_set("transport", ESP_LOG_VERBOSE);
    esp_log_level_set("outbox", ESP_LOG_VERBOSE);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(i2cdev_init());

    /* This helper function configures Wi-Fi or Ethernet, as selected in menuconfig.
     * Read "Establishing Wi-Fi or Ethernet Connection" section in
     * examples/protocols/README.md for more information about this function.
     */
    ESP_ERROR_CHECK(example_connect());

    mqtt5_app_start();
}
