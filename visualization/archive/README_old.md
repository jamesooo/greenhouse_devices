# Greenhouse Environmental Data Visualization Tool

A Python-based visualization tool for mapping greenhouse environmental sensor data with high-resolution spatial interpolation.

## Features

- **High-Resolution Mapping**: Generate interpolated maps at 1cm resolution for a 4ft x 4ft greenhouse floor
- **Multiple Environmental Parameters**: Visualize temperature, humidity, atmospheric pressure, and gas resistance
- **Plant Biomass Mapping**: Map fresh biomass across all plants (including those without sensors)
- **Mixed Sensor Coverage**: Handle scenarios with 6-8 measured plants among 12-15 total plants
- **Statistical Analysis**: Automatic calculation of R², RMSE, and other quality metrics
- **GeoPandas Integration**: Spatial data handling and analysis
- **TimescaleDB Support**: Query time-series sensor data directly from your database
- **Flexible Sensor Placement**: Auto-position sensors or specify custom locations
- **Export Capabilities**: Save interpolated data to CSV for further analysis

## Installation

1. Navigate to the visualization directory:
```bash
cd visualization
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

```python
from greenhouse_mapper import GreenhouseMapper

# Create mapper for 4ft x 4ft greenhouse at 1cm resolution
mapper = GreenhouseMapper(width_cm=121.92, height_cm=121.92, resolution_cm=1.0)

# Add sensor data
sensor_data = [
    {'temperature': 23.90, 'humidity': 48.43, 'pressure': 1009.11, 'resistance': 78424.00},
    # ... more sensors
]

# Set data (auto-positions sensors if positions not provided)
mapper.set_sensor_data(sensor_data)

# Create interpolated map with statistics
fig = mapper.plot_map('temperature', cmap='RdYlBu_r', show_stats=True)

# Or plot all parameters at once
fig_all = mapper.plot_all_parameters(figsize=(20, 16))
```

## Usage with Jupyter Notebook

See `greenhouse_visualization_demo.ipynb` for a complete interactive demonstration with:
- Sample 8-sensor test data
- Individual parameter visualizations
- Combined multi-parameter views
- Statistical analysis
- TimescaleDB integration examples
- **Plant biomass mapping** with mixed sensor coverage (14 plants, 7 with sensors)

## Plant Biomass Mapping

The `PlantMapper` class extends the base functionality to handle realistic scenarios where you have more plants than sensors:

```python
from plant_mapper import PlantMapper

# 14 plants total, 7 with sensors
plant_positions = [(15, 15), (45, 20), ...]  # x, y in cm
has_sensor = [True, False, True, False, ...]  # which plants have sensors

# Plant data includes biomass for ALL plants, environmental data for some
plant_data = [
    {'biomass_g': 32.5, 'temperature': 23.90, 'humidity': 48.43, ...},  # with sensor
    {'biomass_g': 28.3},  # without sensor - biomass only
    ...
]

# Create mapper and visualize
mapper = PlantMapper()
mapper.set_plant_data(plant_data, plant_positions, has_sensor)

# Map biomass across all plants
fig = mapper.plot_plant_map('biomass_g', show_plants=True, show_stats=True)

# Combined view: biomass + environmental conditions
fig_all = mapper.plot_plant_comparison()
```

## Using with TimescaleDB

```python
from db_connector import TimescaleDBConnector

# Connect to database
db = TimescaleDBConnector(
    host='localhost',
    port=5432,
    database='greenhouse',
    user='postgres',
    password='your_password'
)

db.connect()

# Query latest readings
df_latest = db.query_latest_readings()

# Get sensor positions (requires sensor_positions table)
df_positions = db.get_sensor_positions()

# Prepare for mapper
sensor_data, positions = db.prepare_data_for_mapper(df_latest, df_positions)

# Create visualization
mapper = GreenhouseMapper()
mapper.set_sensor_data(sensor_data, positions)
fig = mapper.plot_all_parameters()
```

## API Reference

### GreenhouseMapper

#### `__init__(width_cm=121.92, height_cm=121.92, resolution_cm=1.0)`
Initialize the mapper with greenhouse dimensions and grid resolution.

#### `set_sensor_data(sensor_data, sensor_positions=None)`
Set sensor data with optional positions. Auto-positions if positions not provided.

**Parameters:**
- `sensor_data`: List of dicts with keys: temperature, humidity, pressure, resistance
- `sensor_positions`: List of (x, y) tuples in cm (optional)

#### `interpolate(parameter, method='cubic')`
Interpolate sensor data across the floor.

**Parameters:**
- `parameter`: One of 'temperature', 'humidity', 'pressure', 'resistance'
- `method`: 'linear', 'cubic', or 'rbf'

**Returns:** 2D numpy array of interpolated values

#### `plot_map(parameter, figsize=(12,10), cmap='viridis', show_sensors=True, show_stats=True, title=None, save_path=None)`
Plot a single parameter heatmap.

#### `plot_all_parameters(figsize=(20,16), cmap='viridis', save_path=None)`
Plot all four parameters in a 2x2 grid.

#### `get_statistics(parameter=None)`
Get statistics for one or all parameters.

**Returns:** Dictionary with keys: mean, std, min, max, range, r_squared, rmse, num_sensors

#### `export_interpolated_data(parameter, filepath, format='csv')`
Export interpolated data to file.

### PlantMapper

Extension of GreenhouseMapper for plant growth and biomass analysis with mixed sensor coverage.

#### `__init__(width_cm=121.92, height_cm=121.92, resolution_cm=1.0)`
Initialize the plant mapper.

#### `set_plant_data(plant_data, plant_positions, has_sensor=None)`
Set plant data including biomass and sensor information.

**Parameters:**
- `plant_data`: List of dicts with keys: biomass_g (required), temperature, humidity, etc. (optional)
- `plant_positions`: List of (x, y) tuples in cm
- `has_sensor`: List of booleans indicating which plants have sensors (auto-detected if None)

#### `interpolate_biomass(method='cubic')`
Interpolate biomass across the greenhouse floor using data from all plants.

**Returns:** 2D numpy array of interpolated biomass values

#### `plot_plant_map(parameter='biomass_g', figsize=(14,12), cmap='YlGn', show_plants=True, show_stats=True, title=None, save_path=None)`
Plot interpolated map with plant locations clearly marked.

- Measured plants (with sensors): Filled circles with white borders
- Unmeasured plants (biomass only): Hollow circles
- Plant IDs and values overlaid

#### `plot_plant_comparison(figsize=(20,10), save_path=None)`
Create 2x2 comparison: biomass + temperature + humidity + pressure.

**Returns:** Matplotlib Figure showing all parameters with plant locations

#### `get_plant_summary()`
Get DataFrame summary of all plants.

**Returns:** DataFrame with columns: plant_id, x, y, has_sensor, biomass_g, etc.

### TimescaleDBConnector

#### `__init__(host='localhost', port=5432, database='greenhouse', user='postgres', password='postgres')`
Initialize database connector.

#### `query_latest_readings(sensor_ids=None, table_name='sensor_data')`
Get the latest reading from each sensor.

#### `query_time_averaged(start_time=None, end_time=None, sensor_ids=None, interval='5 minutes', table_name='sensor_data')`
Query time-averaged sensor data.

#### `get_sensor_positions(table_name='sensor_positions')`
Get sensor positions from database.

#### `prepare_data_for_mapper(sensor_data_df, sensor_positions_df=None)`
Convert database results to mapper format.

## Database Schema

### Expected sensor_data table structure:
```sql
CREATE TABLE sensor_data (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    pressure DOUBLE PRECISION,
    gas_resistance DOUBLE PRECISION
);

SELECT create_hypertable('sensor_data', 'time');
```

### Optional sensor_positions table:
```sql
CREATE TABLE sensor_positions (
    sensor_id TEXT PRIMARY KEY,
    x_position_cm DOUBLE PRECISION NOT NULL,
    y_position_cm DOUBLE PRECISION NOT NULL,
    description TEXT
);
```

## Interpolation Methods

- **Linear**: Fast, simple interpolation. Best for dense sensor networks.
- **Cubic**: Smoother results, default method. Good balance of speed and quality.
- **RBF**: Radial Basis Function. Smoothest results, slower. Best for sparse sensors.

## Statistics Explained

- **R² (R-squared)**: Interpolation quality via leave-one-out cross-validation. Values closer to 1.0 indicate better fit.
- **RMSE**: Root Mean Square Error of predictions vs actual sensor readings.
- **Mean/Std**: Average and standard deviation across the entire interpolated surface.
- **Range**: Difference between min and max values.

## Requirements

- Python >= 3.8
- geopandas >= 0.14.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- matplotlib >= 3.7.0
- scipy >= 1.11.0
- psycopg2-binary >= 2.9.0 (for database connectivity)
- sqlalchemy >= 2.0.0

## License

Same as parent project (MIT/Apache-2.0)

## Contributing

Feel free to submit issues or pull requests for improvements!
