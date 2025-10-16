# Conditionally compile device sources based on menuconfig selection
set(DEVICE_SRCS "")
set(DEVICE_INCLUDES "")

if(CONFIG_DEVICE_CLIMATE_MONITOR)
    list(APPEND DEVICE_SRCS "climate_monitor/climate_monitor.c")
    message(STATUS "Building Climate Monitor device")
endif()

if(CONFIG_DEVICE_HUMIDIFIER)
    list(APPEND DEVICE_SRCS "humidifier/humidifier.c")
    message(STATUS "Building Humidifier device")
endif()

if(CONFIG_DEVICE_LIGHT_CONTROLLER)
    list(APPEND DEVICE_SRCS "light_controller/light_controller.c")
    message(STATUS "Building Light Controller device")
endif()

idf_component_register(
    SRCS ${DEVICE_SRCS}
    INCLUDE_DIRS "."
    REQUIRES esp_wifi mqtt esp_netif nvs_flash esp_event driver i2cdev bme680 esp_adc protocol_examples_common
    PRIV_REQUIRES main json
)

