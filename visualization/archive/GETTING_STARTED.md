# Getting Started with the Greenhouse Visualization Tool

## Installation Steps

### 1. Install Python Dependencies

Navigate to the visualization directory and install requirements:

```bash
cd visualization
pip install -r requirements.txt
```

### 2. Verify Installation

Run the setup check script to ensure everything is installed correctly:

```bash
python setup_check.py
```

You should see output confirming all packages are installed and basic tests pass.

## Quick Start Guide

### Option 1: Using the Jupyter Notebook (Recommended)

1. Launch Jupyter Notebook:
```bash
jupyter notebook greenhouse_visualization_demo.ipynb
```

2. Run through the cells to see examples of:
   - Creating interpolated maps
   - Viewing statistics
   - Working with the 8-sensor test data
   - Database integration (when ready)

### Option 2: Python Script

Create a simple Python script:

```python
from greenhouse_mapper import GreenhouseMapper

# Your 8-sensor test data
sensor_data = [
    {'temperature': 23.90, 'humidity': 48.43, 'pressure': 1009.11, 'resistance': 78424.00},
    {'temperature': 23.92, 'humidity': 48.44, 'pressure': 1009.15, 'resistance': 78773.00},
    {'temperature': 23.91, 'humidity': 48.44, 'pressure': 1009.11, 'resistance': 78773.00},
    {'temperature': 23.93, 'humidity': 48.44, 'pressure': 1009.11, 'resistance': 78703.00},
    {'temperature': 23.92, 'humidity': 48.45, 'pressure': 1009.11, 'resistance': 78493.00},
    {'temperature': 23.86, 'humidity': 48.46, 'pressure': 1009.13, 'resistance': 78843.00},
    {'temperature': 23.93, 'humidity': 48.46, 'pressure': 1009.13, 'resistance': 78354.00},
    {'temperature': 23.92, 'humidity': 48.47, 'pressure': 1009.11, 'resistance': 78633.00},
]

# Initialize mapper for 4ft x 4ft greenhouse at 1cm resolution
mapper = GreenhouseMapper(width_cm=121.92, height_cm=121.92, resolution_cm=1.0)

# Set sensor data (auto-positions sensors in a grid)
mapper.set_sensor_data(sensor_data)

# Create visualizations
import matplotlib.pyplot as plt

# Single parameter with statistics
fig1 = mapper.plot_map('temperature', cmap='RdYlBu_r', show_stats=True)
plt.savefig('temperature_map.png', dpi=300)

# All parameters
fig2 = mapper.plot_all_parameters(figsize=(20, 16))
plt.savefig('all_parameters.png', dpi=300)

plt.show()

# Get statistics
stats = mapper.get_statistics()
print("Statistics:", stats)
```

## Database Setup (Optional)

If you want to use TimescaleDB integration:

### 1. Ensure TimescaleDB is Running

From your docker-compose setup:
```bash
docker-compose up -d timescaledb
```

### 2. Create Database Schema

Run the database setup script:

```bash
python setup_database.py
```

This will:
- Create the `sensor_data` hypertable
- Create the `sensor_positions` table
- Insert sample data for testing

### 3. Update Database Credentials

Edit the connection parameters in your scripts or notebook:

```python
from db_connector import TimescaleDBConnector

db = TimescaleDBConnector(
    host='localhost',
    port=5432,
    database='greenhouse',
    user='postgres',
    password='your_password'  # Update this!
)
```

### 4. Query and Visualize

```python
# Connect
db.connect()

# Get latest readings
df_latest = db.query_latest_readings()

# Get sensor positions
df_positions = db.get_sensor_positions()

# Prepare for mapper
sensor_data, positions = db.prepare_data_for_mapper(df_latest, df_positions)

# Visualize
mapper = GreenhouseMapper()
mapper.set_sensor_data(sensor_data, positions)
fig = mapper.plot_all_parameters()
plt.show()

# Disconnect
db.disconnect()
```

## Customization

### Custom Sensor Positions

If you know the exact positions of your sensors:

```python
# Positions in cm from corner (x, y)
custom_positions = [
    (20, 20),    # Sensor 0
    (60, 20),    # Sensor 1
    (100, 20),   # Sensor 2
    (20, 60),    # Sensor 3
    (60, 60),    # Sensor 4
    (100, 60),   # Sensor 5
    (20, 100),   # Sensor 6
    (60, 100),   # Sensor 7
]

mapper.set_sensor_data(sensor_data, custom_positions)
```

### Different Interpolation Methods

```python
# Linear (fastest, less smooth)
mapper.interpolate('temperature', method='linear')

# Cubic (default, good balance)
mapper.interpolate('temperature', method='cubic')

# RBF (smoothest, slower)
mapper.interpolate('temperature', method='rbf')
```

### Adjust Resolution

For faster processing or larger areas:

```python
# Coarser resolution (faster, less detail)
mapper = GreenhouseMapper(resolution_cm=5.0)

# Finer resolution (slower, more detail)
mapper = GreenhouseMapper(resolution_cm=0.5)
```

### Different Colormaps

```python
# Temperature: Red-Yellow-Blue (reversed)
mapper.plot_map('temperature', cmap='RdYlBu_r')

# Humidity: Yellow-Green-Blue
mapper.plot_map('humidity', cmap='YlGnBu')

# Other options: 'viridis', 'plasma', 'inferno', 'coolwarm', etc.
```

## Exporting Data

Save interpolated data to CSV:

```python
# Export temperature grid
mapper.export_interpolated_data('temperature', 'temp_grid.csv', format='csv')

# This creates a CSV with columns: x, y, temperature
# Each row represents a grid point
```

## Troubleshooting

### Import Errors

If you see import errors, ensure all packages are installed:
```bash
pip install -r requirements.txt
```

### Database Connection Issues

1. Check TimescaleDB is running: `docker ps`
2. Verify connection parameters (host, port, database, user, password)
3. Check firewall/network settings

### Interpolation Warnings

If you have too few sensors (< 3), some interpolation methods won't work. The tool needs at least 3 valid sensor readings per parameter.

### Memory Issues with High Resolution

If 1cm resolution is too memory-intensive, try:
- Increase resolution to 2cm or 5cm
- Reduce greenhouse dimensions
- Process parameters one at a time

## Next Steps

1. **Test with sample data**: Run the notebook with the provided 8-sensor test data
2. **Connect to your database**: Set up TimescaleDB schema and connect
3. **Define sensor positions**: Create your actual sensor layout
4. **Automate visualization**: Set up scheduled reports or monitoring dashboards
5. **Analyze trends**: Use time-averaged queries to study environmental changes

## Support

For issues or questions:
- Check the README.md for detailed API documentation
- Review the example notebook for usage patterns
- Ensure all dependencies are properly installed
