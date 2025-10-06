idf_component_register(SRCS "app_main.c" "mqtt_client_manager.c"
                    PRIV_REQUIRES mqtt nvs_flash esp_netif devices
                    INCLUDE_DIRS ".")

# Generate env_config.h from .env file when .env changes
set(ENV_FILE "${CMAKE_SOURCE_DIR}/.env")
set(ENV_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/env_config.h")
set(GENERATE_SCRIPT "${CMAKE_SOURCE_DIR}/scripts/generate_env_header.py")
set(ENV_DEFAULT_FILE "${CMAKE_SOURCE_DIR}/.env.default")

# Custom command to generate the header file
# This only runs when:
# - env_config.h doesn't exist
# - .env changes
# - .env.default changes
# - generate_env_header.py changes
add_custom_command(
    OUTPUT ${ENV_HEADER}
    COMMAND ${PYTHON} ${GENERATE_SCRIPT} ${ENV_FILE} ${ENV_HEADER}
    DEPENDS ${ENV_FILE} ${ENV_DEFAULT_FILE} ${GENERATE_SCRIPT}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating env_config.h from .env file"
    VERBATIM
)

# Create a custom target that the component depends on
add_custom_target(generate_env_header DEPENDS ${ENV_HEADER})

# Get the component library
idf_component_get_property(component_lib ${COMPONENT_NAME} COMPONENT_LIB)

# Make the component depend on the generated header
add_dependencies(${component_lib} generate_env_header)
