#!/bin/bash
#
# Soil Moisture Sensor Calibration Script
# 
# This script publishes calibration values to the MQTT broker
# for a specific device's soil moisture sensor.
#
# Usage: ./calibrate_soil_sensor.sh [device_id] [dry_value] [wet_value] [broker_host]
#

set -e

# Default values
DEFAULT_DEVICE_ID="climate-01"
DEFAULT_BROKER="192.168.1.162"

# Get parameters or use defaults
DEVICE_ID="${1:-$DEFAULT_DEVICE_ID}"
DRY_VALUE="$2"
WET_VALUE="$3"
BROKER="${4:-$DEFAULT_BROKER}"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if mosquitto_pub is installed
if ! command -v mosquitto_pub &> /dev/null; then
    echo -e "${RED}Error: mosquitto_pub not found${NC}"
    echo "Install it with: brew install mosquitto"
    exit 1
fi

# Interactive mode if values not provided
if [ -z "$DRY_VALUE" ] || [ -z "$WET_VALUE" ]; then
    echo -e "${YELLOW}=== Soil Moisture Sensor Calibration ===${NC}"
    echo ""
    echo "Device ID: $DEVICE_ID"
    echo "MQTT Broker: $BROKER"
    echo ""
    echo -e "${YELLOW}Instructions:${NC}"
    echo "1. Place sensor in DRY soil and read ADC value from logs"
    echo "2. Place sensor in WET soil and read ADC value from logs"
    echo "3. Enter the values below"
    echo ""
    
    # Prompt for dry value
    if [ -z "$DRY_VALUE" ]; then
        read -p "Enter ADC value for DRY soil (default: 2800): " DRY_VALUE
        DRY_VALUE="${DRY_VALUE:-2800}"
    fi
    
    # Prompt for wet value
    if [ -z "$WET_VALUE" ]; then
        read -p "Enter ADC value for WET soil (default: 1200): " WET_VALUE
        WET_VALUE="${WET_VALUE:-1200}"
    fi
fi

# Validate inputs are numbers
if ! [[ "$DRY_VALUE" =~ ^[0-9]+$ ]] || ! [[ "$WET_VALUE" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: Values must be numbers${NC}"
    exit 1
fi

# Sanity check: dry should be higher than wet (inverted logic)
if [ "$DRY_VALUE" -le "$WET_VALUE" ]; then
    echo -e "${YELLOW}Warning: DRY value ($DRY_VALUE) should typically be higher than WET value ($WET_VALUE)${NC}"
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Calibration cancelled"
        exit 0
    fi
fi

# Build JSON payload
JSON_PAYLOAD="{\"dry_value\": $DRY_VALUE, \"wet_value\": $WET_VALUE}"
TOPIC="sensor/config/$DEVICE_ID"

# Display what we're about to send
echo ""
echo -e "${GREEN}=== Publishing Calibration ===${NC}"
echo "Device ID:  $DEVICE_ID"
echo "Broker:     $BROKER"
echo "Topic:      $TOPIC"
echo "Dry Value:  $DRY_VALUE ADC"
echo "Wet Value:  $WET_VALUE ADC"
echo "Payload:    $JSON_PAYLOAD"
echo ""

# Confirm before sending
read -p "Send calibration to device? (Y/n): " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo "Calibration cancelled"
    exit 0
fi

# Publish to MQTT
echo ""
echo -e "${YELLOW}Publishing...${NC}"
if mosquitto_pub -h "$BROKER" -t "$TOPIC" -m "$JSON_PAYLOAD"; then
    echo -e "${GREEN}✓ Calibration published successfully!${NC}"
    echo ""
    echo "The device should:"
    echo "  1. Receive the new calibration values"
    echo "  2. Save them to NVS (non-volatile storage)"
    echo "  3. Use them for all future moisture readings"
    echo ""
    echo "Check device logs to confirm receipt."
else
    echo -e "${RED}✗ Failed to publish calibration${NC}"
    exit 1
fi
