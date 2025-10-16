# Quick Reference - Greenhouse Visualization Tool

## Installation
```bash
cd visualization
pip install -r requirements.txt
python setup_check.py  # Verify installation
```

## Basic Usage

### Import
```python
from greenhouse_mapper import GreenhouseMapper
from plant_mapper import PlantMapper  # For biomass mapping
import matplotlib.pyplot as plt
```

### Create Mapper
```python
# 4ft x 4ft greenhouse, 1cm resolution
mapper = GreenhouseMapper(width_cm=121.92, height_cm=121.92, resolution_cm=1.0)
```

### Load Data
```python
# Your 8 sensors
sensor_data = [
    {'temperature': 23.90, 'humidity': 48.43, 'pressure': 1009.11, 'resistance': 78424.00},
    # ... more sensors
]

# Auto-position sensors
mapper.set_sensor_data(sensor_data)

# Or specify positions (x, y in cm)
positions = [(20, 20), (60, 20), (100, 20), ...]
mapper.set_sensor_data(sensor_data, positions)
```

### Visualize Single Parameter
```python
fig = mapper.plot_map('temperature', 
                     cmap='RdYlBu_r',      # Colormap
                     show_sensors=True,    # Show sensor markers
                     show_stats=True)      # Show statistics box
plt.show()
```

### Visualize All Parameters
```python
fig = mapper.plot_all_parameters(figsize=(20, 16))
plt.savefig('greenhouse_map.png', dpi=300)
plt.show()
```

### Get Statistics
```python
stats = mapper.get_statistics('temperature')
print(f"R²: {stats['r_squared']:.4f}")
print(f"RMSE: {stats['rmse']:.4f}")
```

### Export Data
```python
mapper.export_interpolated_data('temperature', 'temp_grid.csv')
```

## Database Usage

### Connect
```python
from db_connector import TimescaleDBConnector

db = TimescaleDBConnector(
    host='localhost',
    database='greenhouse',
    user='postgres',
    password='your_password'
)
db.connect()
```

### Query Data
```python
# Latest readings
df_latest = db.query_latest_readings()

# Time-averaged (last hour, 5-min intervals)
df_avg = db.query_time_averaged(interval='5 minutes')

# Sensor positions
df_pos = db.get_sensor_positions()
```

### Use with Mapper
```python
# Convert to mapper format
sensor_data, positions = db.prepare_data_for_mapper(df_latest, df_pos)

# Create visualization
mapper = GreenhouseMapper()
mapper.set_sensor_data(sensor_data, positions)
fig = mapper.plot_all_parameters()
plt.show()

db.disconnect()
```

## Customization

### Interpolation Methods
```python
mapper.interpolate('temperature', method='linear')  # Fast
mapper.interpolate('temperature', method='cubic')   # Default, smooth
mapper.interpolate('temperature', method='rbf')     # Smoothest, slower
```

### Colormaps
- Temperature: `'RdYlBu_r'` (red-yellow-blue reversed)
- Humidity: `'YlGnBu'` (yellow-green-blue)
- Pressure: `'viridis'` (perceptually uniform)
- Resistance: `'plasma'` (vibrant)
- Others: `'coolwarm'`, `'inferno'`, `'jet'`, etc.

### Resolution
```python
# Faster, less detail
mapper = GreenhouseMapper(resolution_cm=5.0)

# Slower, more detail
mapper = GreenhouseMapper(resolution_cm=0.5)
```

## Common Patterns

### Plant Biomass Mapping (Mixed Sensor Coverage)
```python
from plant_mapper import PlantMapper

# 14 plants, 7 with sensors, 7 without
plant_positions = [(15,15), (45,20), ...]
has_sensor = [True, False, True, False, ...]

plant_data = [
    {'biomass_g': 32.5, 'temperature': 23.90, ...},  # with sensor
    {'biomass_g': 28.3},  # without sensor
    ...
]

mapper = PlantMapper()
mapper.set_plant_data(plant_data, plant_positions, has_sensor)

# Biomass map
fig = mapper.plot_plant_map('biomass_g')

# Comprehensive view
fig_all = mapper.plot_plant_comparison()
plt.show()
```

### Save All Maps
```python
params = ['temperature', 'humidity', 'pressure', 'resistance']
for param in params:
    fig = mapper.plot_map(param, show_stats=True)
    plt.savefig(f'{param}_map.png', dpi=300)
    plt.close()
```

### Compare Two Time Points
```python
# Time 1
mapper1 = GreenhouseMapper()
mapper1.set_sensor_data(data_morning)

# Time 2
mapper2 = GreenhouseMapper()
mapper2.set_sensor_data(data_afternoon)

# Plot side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
# ... custom plotting
```

### Automated Reporting
```python
from datetime import datetime

# Get latest data from DB
db.connect()
df = db.query_latest_readings()
sensor_data, pos = db.prepare_data_for_mapper(df)

# Create visualization
mapper = GreenhouseMapper()
mapper.set_sensor_data(sensor_data, pos)

# Save with timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
fig = mapper.plot_all_parameters()
plt.savefig(f'greenhouse_report_{timestamp}.png', dpi=300)

db.disconnect()
```

## Troubleshooting

### Import errors
```bash
pip install -r requirements.txt
```

### Too few sensors
Need at least 3 sensors per parameter for interpolation.

### Database connection failed
Check: TimescaleDB running, credentials, network access

### Memory issues
Increase `resolution_cm` from 1.0 to 2.0 or 5.0

## Files

- `example_simple.py` - Run this first! (8 sensors, environmental data)
- `example_plant_biomass.py` - Plant biomass mapping (14 plants, 7 sensors)
- `greenhouse_visualization_demo.ipynb` - Interactive tutorial with both examples
- `README.md` - Full API documentation
- `GETTING_STARTED.md` - Detailed guide
- `PROJECT_SUMMARY.md` - Complete overview

## Quick Test

```bash
# Test environmental mapping
python example_simple.py

# Test plant biomass mapping
python example_plant_biomass.py

# Or open notebook
jupyter notebook greenhouse_visualization_demo.ipynb
```

## Parameters Reference

| Parameter | Units | Typical Range | Sensor |
|-----------|-------|---------------|--------|
| temperature | °C | 15-35 | BME680 |
| humidity | % RH | 30-80 | BME680 |
| pressure | hPa | 950-1050 | BME680 |
| resistance | Ω | 10k-200k | BME680 |

## Statistics Interpretation

- **R² > 0.9**: Excellent interpolation quality
- **R² 0.7-0.9**: Good quality
- **R² < 0.7**: Consider adding more sensors or check data quality
- **RMSE**: In parameter units; lower is better
