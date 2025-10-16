# Plant Biomass Mapping - Feature Documentation

## Overview

The `PlantMapper` class extends the base `GreenhouseMapper` to handle realistic greenhouse scenarios where you have more plants than sensors. This is particularly useful for research and production settings where installing sensors on every plant is impractical or expensive.

## Use Case

**Scenario**: You have 12-15 plants in your greenhouse, but only 6-8 have environmental sensors (BME680 devices). However, you measure fresh biomass for ALL plants periodically.

**Question**: How can you create spatial maps showing biomass distribution across the entire greenhouse floor?

**Answer**: Use PlantMapper to interpolate biomass from all plants while also mapping environmental conditions from the subset with sensors.

## Key Features

### 1. Mixed Sensor Coverage
- **Measured Plants**: Have both environmental sensors AND biomass measurements
- **Unmeasured Plants**: Have ONLY biomass measurements (no sensors)
- Both types contribute to the biomass interpolation

### 2. Visual Distinction
- **Measured plants**: Displayed as filled dark green circles with white borders
- **Unmeasured plants**: Displayed as hollow circles with dark green borders
- Plant IDs and biomass values are overlaid on each plant location

### 3. Comprehensive Analysis
- Biomass distribution map using data from ALL plants
- Environmental maps (temp, humidity, pressure) using data from plants with sensors
- Correlation analysis between biomass and environmental factors
- Statistical quality metrics (R², RMSE) for interpolation validation
- Configurable rectangular pot visualization (default: 5.9" × 6.3" / 15.0 cm × 16.0 cm)

## Example Setup

### Typical Configuration

```
Total Plants: 16
├── With Sensors: 7 (measures: biomass, temp, humidity, pressure, resistance)
└── Without Sensors: 9 (measures: biomass only)

Greenhouse: 4ft × 4ft (121.92 cm × 121.92 cm)
Resolution: 1 cm (14,884 interpolation points)
Sensor Coverage: 44% (7 out of 16 plants)
Pot Size: 5.9" × 6.3" (15.0 cm × 16.0 cm) - configurable
```

### Plant Distribution Pattern

```
P0■ ---- P1□ ---- P2■ ---- P3□
 |        |        |        |
P4■ ---- P5□ ---- P6■ ---- P7□
 |        |        |        |
P8■ ---- P9□ ---- P10■ --- P11□
 |        |        |        |
P12■ ------------ P13□

■ = Plant with sensor (filled rectangle)
□ = Plant without sensor (hollow rectangle)
```

## Code Example

### Basic Usage

```python
from plant_mapper import PlantMapper

# Define plant positions (x, y in cm)
plant_positions = [
    (15, 15),   # Plant 0
    (45, 20),   # Plant 1
    (75, 18),   # Plant 2
    # ... more positions
]

# Indicate which plants have sensors
has_sensor = [
    True,   # Plant 0 - has sensor
    False,  # Plant 1 - no sensor
    True,   # Plant 2 - has sensor
    # ... etc
]

# Plant data
plant_data = [
    # Plant 0: with sensor
    {
        'biomass_g': 32.5,
        'temperature': 23.90,
        'humidity': 48.43,
        'pressure': 1009.11,
        'resistance': 78424.00
    },
    # Plant 1: without sensor (biomass only)
    {
        'biomass_g': 28.3
    },
    # ... more plants
]

# Create mapper with pot dimensions
# Pot size: 5.9" x 6.3" = 15.0 cm x 16.0 cm
mapper = PlantMapper(
    width_cm=121.92, 
    height_cm=121.92, 
    resolution_cm=1.0,
    pot_width_cm=15.0,   # 5.9 inches
    pot_height_cm=16.0   # 6.3 inches
)
mapper.set_plant_data(plant_data, plant_positions, has_sensor)

# Generate biomass map
fig = mapper.plot_plant_map(
    parameter='biomass_g',
    cmap='YlGn',
    show_plants=True,
    show_stats=True
)
plt.show()
```

### Advanced: Comprehensive Analysis

```python
# Combined view: biomass + environmental conditions
fig_comparison = mapper.plot_plant_comparison(figsize=(20, 10))
plt.savefig('greenhouse_analysis.png', dpi=300)

# Get statistics
stats = mapper.get_statistics('biomass_g')
print(f"Biomass R²: {stats['r_squared']:.4f}")
print(f"RMSE: {stats['rmse']:.2f} g")

# Get plant summary
summary = mapper.get_plant_summary()
print(summary)

# Analyze correlations (for plants with sensors)
measured = mapper.measured_plants
corr = measured[['biomass_g', 'temperature']].corr()
print(f"Biomass-Temperature correlation: {corr.iloc[0,1]:.3f}")
```

## Data Requirements

### Minimum Requirements
- **Total plants**: 3+ (for interpolation)
- **Biomass data**: Required for ALL plants
- **Sensor data**: Optional, only for plants with sensors

### Recommended Setup
- **Total plants**: 12-16 plants
- **Plants with sensors**: 6-8 (40-50% coverage)
- **Spatial distribution**: Spread sensors across the greenhouse area
- **Regular measurements**: Take biomass readings consistently

## Interpolation Quality

### Factors Affecting R²

1. **Number of plants**: More plants = better interpolation
2. **Spatial distribution**: Evenly spread plants give better coverage
3. **Data quality**: Accurate biomass measurements are critical
4. **Biomass variation**: Greater spatial variation is easier to interpolate

### Expected R² Values

| Scenario | Expected R² | Interpretation |
|----------|-------------|----------------|
| 14 plants, well-distributed | 0.85 - 0.95 | Excellent |
| 10 plants, clustered | 0.65 - 0.80 | Good |
| 6 plants, well-distributed | 0.70 - 0.85 | Good |
| < 5 plants | 0.40 - 0.70 | Marginal |

## Practical Applications

### 1. Growth Monitoring
Track how biomass changes across the greenhouse over time:
- Weekly or bi-weekly biomass measurements
- Create time-series of spatial biomass maps
- Identify areas of poor/excellent growth

### 2. Treatment Effects
Compare biomass distribution under different treatments:
- Different fertilizer zones
- Varying light conditions
- Temperature gradients

### 3. Environmental Optimization
Correlate biomass with environmental conditions:
- Find optimal temperature range
- Identify humidity-biomass relationships
- Detect microclimates

### 4. Sensor Placement Optimization
Use interpolation quality to optimize sensor placement:
- Low R² in certain areas → add more sensors there
- High R² with current sensors → no additional sensors needed
- Identify redundant sensor locations

## Visualization Options

### Single Parameter Maps

```python
# Biomass distribution
mapper.plot_plant_map('biomass_g', cmap='YlGn')

# Temperature (plants with sensors only)
mapper.plot_plant_map('temperature', cmap='RdYlBu_r')

# Humidity
mapper.plot_plant_map('humidity', cmap='YlGnBu')
```

### Comparison View

```python
# 2x2 grid: biomass, temperature, humidity, pressure
mapper.plot_plant_comparison()
```

### Custom Visualization

```python
# Access interpolated data directly
biomass_grid = mapper.interpolated_data['biomass_g']

# Create custom plots
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
im = ax.imshow(biomass_grid, cmap='YlGn', origin='lower')
plt.colorbar(im, label='Biomass (g)')
plt.show()
```

## Database Integration

The PlantMapper works seamlessly with TimescaleDB:

```python
from db_connector import TimescaleDBConnector
from plant_mapper import PlantMapper

# Query latest data
db = TimescaleDBConnector()
db.connect()

# Get sensor data (for plants with sensors)
df_sensors = db.query_latest_readings()

# Get all plant biomass from a separate table
# (You would create a plants/biomass table in your database)
df_biomass = pd.read_sql("SELECT plant_id, biomass_g, x, y FROM plant_biomass", db.engine)

# Merge and prepare
# ... combine sensor and biomass data

# Visualize
mapper = PlantMapper()
mapper.set_plant_data(plant_data, positions, has_sensor)
mapper.plot_plant_comparison()
```

## Tips and Best Practices

### 1. Sensor Placement
- Distribute sensors across the greenhouse (not clustered)
- Place sensors in areas representing different microclimates
- Include sensors at edges and center

### 2. Biomass Measurement
- Measure at consistent times (same time of day)
- Use fresh biomass immediately after harvest
- Be consistent with measurement technique
- Record measurements in grams with 0.1g precision

### 3. Data Quality
- Check for outliers before interpolation
- Ensure accurate plant positioning (±1 cm)
- Validate sensor readings regularly
- Document any anomalies or plant issues

### 4. Interpolation Method
- **Cubic** (default): Best for most cases
- **Linear**: Use if plants are very close together
- **RBF**: Use for very sparse plant coverage

### 5. Analysis
- Always check R² value to validate interpolation quality
- Look for spatial patterns in biomass distribution
- Correlate with environmental data when available
- Track changes over time

## Limitations

1. **Interpolation Accuracy**: Decreases between plants that are far apart
2. **Edge Effects**: Less reliable near greenhouse edges with no plants
3. **Minimum Plants**: Need at least 3-4 plants for meaningful interpolation
4. **Assumes Continuity**: Works best when biomass changes gradually, not abruptly

## Future Enhancements

Potential additions to PlantMapper:

1. **Temporal Analysis**: Track biomass changes over time
2. **Growth Rate Maps**: Calculate and visualize growth rates
3. **Prediction**: Use environmental data to predict biomass
4. **3D Visualization**: Include plant height for 3D biomass volume
5. **Multi-species**: Handle different plant types with different growth patterns

## Example Outputs

When you run `example_plant_biomass.py`, you'll get:

1. **plant_biomass_map.png**: 
   - High-resolution biomass interpolation
   - Plant locations with IDs
   - Statistics overlay
   - Contour lines showing gradients

2. **plant_comprehensive_analysis.png**:
   - 2x2 grid showing biomass + temp + humidity + pressure
   - All with plant locations marked
   - Correlation patterns visible

3. **Console output**:
   - Plant summary table
   - Interpolation statistics (R², RMSE)
   - Correlation coefficients
   - Quality assessment

## Summary

The PlantMapper class provides a practical solution for mapping plant biomass in greenhouse environments where full sensor coverage is impractical. By combining biomass measurements from all plants with environmental data from a subset of sensor-equipped plants, you can:

- Generate high-resolution spatial maps
- Identify growth patterns and microclimates
- Optimize environmental conditions
- Make data-driven decisions about sensor placement
- Track plant performance over time

This approach balances cost (fewer sensors needed) with data quality (all plants contribute biomass data), making it ideal for research and commercial greenhouse operations.
