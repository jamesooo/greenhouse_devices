# Microclimate-Optimized Plant Layout for Spinach Growth Study

## Research Objective

**Question**: How do microclimate variations across a 4×4 foot greenhouse affect spinach growth rates?

**Approach**: Deploy 16 spinach plants with non-uniform spacing across the full greenhouse to sample different environmental zones. Use 7 BME680 sensors (44% coverage) to measure temperature, humidity, pressure, and gas resistance gradients.

## Layout Design Philosophy

### Traditional Approach (REJECTED)
- ❌ Uniform grid (4×4 with tight spacing)
- ❌ Compact clustering in center
- ❌ Limited spatial coverage (~54% of greenhouse)
- ❌ Uniform microclimate conditions
- ❌ Poor gradient measurement

### Microclimate Study Approach (IMPLEMENTED)
- ✅ **Non-uniform distribution** - realistic spacing variation
- ✅ **80% greenhouse coverage** - X and Y spans ~97 cm each
- ✅ **Strategic sensor placement** - corners, edges, center
- ✅ **Zone sampling** - bottom (cool), center (warm), top (warmest)
- ✅ **Gradient capture** - measures environmental variation

## Final Layout Specifications

### Spatial Configuration

```
Greenhouse: 121.92 cm × 121.92 cm (4 ft × 4 ft)
Pot Size: 15.0 cm × 16.0 cm (5.9" × 6.3")
Spacing: Non-uniform (17-47 cm between plants)

Coverage:
  X-axis: 15 → 112 cm (span: 97 cm = 79.6%)
  Y-axis: 18 → 115 cm (span: 97 cm = 79.6%)

Plant Count: 16 total
  - 7 with BME680 sensors (44%)
  - 9 with biomass only (56%)
```

### Plant Positions

```python
plant_positions = [
    # BOTTOM ZONE (cooler, less convection)
    ( 18,  18),    # P0  - sensor (bottom-left corner)
    ( 38,  25),    # P1  - no sensor
    ( 25,  45),    # P2  - sensor (left edge)
    ( 88,  22),    # P3  - sensor (bottom-right)
    (108,  38),    # P4  - no sensor (right edge)
    
    # CENTER ZONE (warmer, stratified air)
    ( 95,  55),    # P5  - no sensor
    ( 42,  62),    # P6  - sensor (center-left)
    ( 65,  68),    # P7  - no sensor (center)
    ( 85,  78),    # P8  - no sensor (center-right)
    
    # TOP ZONE (warmest, rising air)
    ( 15,  80),    # P9  - sensor (left edge, upper)
    ( 35,  92),    # P10 - no sensor
    ( 22, 108),    # P11 - sensor (top-left corner)
    ( 58,  95),    # P12 - no sensor (upper-center)
    ( 75, 100),    # P13 - sensor (upper-right interior)
    ( 95, 105),    # P14 - no sensor
    (112, 115),    # P15 - no sensor (top-right corner)
]
```

### Sensor Distribution Strategy

**7 sensors strategically placed to capture gradients:**

1. **3 Corner Sensors** - measure boundary conditions
   - P0: Bottom-left corner (coolest, near floor)
   - P3: Bottom-right corner (cooler, side ventilation)
   - P11: Top-left corner (warm, near ceiling)

2. **2 Edge Sensors** - measure heat loss zones
   - P2: Left edge, lower (boundary layer effects)
   - P9: Left edge, upper (rising air column)

3. **2 Interior Sensors** - measure core conditions
   - P6: Center-left (transition zone)
   - P13: Upper-right interior (warmest stable zone)

## Microclimate Zones

### Zone 1: Bottom (Cooler, 18-55 cm height)
**Plants**: P0, P1, P2, P3, P4 (5 plants, 3 with sensors)

**Expected conditions:**
- Cooler temperatures (heat rises)
- Higher humidity (moisture settles)
- Less air movement
- More stable conditions

**Research value**: Baseline growth rates in cooler microclimate

### Zone 2: Center (Warmer, 55-80 cm height)
**Plants**: P5, P6, P7, P8 (4 plants, 1 with sensor)

**Expected conditions:**
- Moderate warming
- Stratified air layers
- Transition between bottom and top
- Variable airflow

**Research value**: Gradient measurements between zones

### Zone 3: Top (Warmest, 80-115 cm height)
**Plants**: P9, P10, P11, P12, P13, P14, P15 (7 plants, 3 with sensors)

**Expected conditions:**
- Warmest temperatures (heat accumulation)
- Lower humidity (warm air holds more moisture)
- More air movement
- Greater variability

**Research value**: Maximum growth potential in optimal warmth

### Edge vs Interior

**Edge plants** (near walls): P0, P2, P4, P9, P11, P15
- Greater heat loss through walls
- Drafts and air infiltration
- Variable microclimates
- 4 sensors on edges (67% of sensor coverage)

**Interior plants**: P1, P5, P6, P7, P8, P10, P12, P13, P14
- More stable conditions
- Less heat loss
- Protected from drafts
- 3 sensors interior (43% of sensor coverage)

## Expected Environmental Gradients

### Temperature Gradient
```
Bottom → Top: ~0.5-2.0°C increase expected
Edge → Interior: ~0.2-0.8°C difference expected

Measurement strategy: 
- 3 bottom sensors (P0, P2, P3)
- 1 center sensor (P6)
- 3 top sensors (P9, P11, P13)
```

### Humidity Gradient
```
Bottom → Top: ~2-5% RH decrease expected
Edge → Interior: ~1-3% RH variation expected

Measurement strategy:
- Edge sensors capture boundary effects
- Interior sensors measure stable core
```

### Airflow Patterns
```
Expected: Rising air column (convection)
Effect: Nutrients/CO2 distribution varies
Impact: Growth rate differences 10-30% possible

Measurement strategy:
- Gas resistance sensor (BME680) proxy for air quality
- Correlation with plant biomass
```

## Research Benefits

### 1. Microclimate Characterization
- **80% greenhouse coverage** ensures complete spatial sampling
- **Non-uniform spacing** mimics real-world greenhouse conditions
- **Multi-zone measurement** captures vertical and horizontal gradients
- **Edge + interior** comparison shows boundary effects

### 2. Growth Correlation
- **All 16 plants** measured for fresh biomass
- **7 plants** with full environmental data
- **9 plants** test interpolation quality
- **Statistical analysis**: Correlation between microclimate and growth

### 3. Interpolation Validation
- **44% sensor coverage** tests sparse network performance
- **Non-uniform distribution** challenges interpolation algorithms
- **Known gradients** validate interpolated surfaces
- **Leave-one-out validation** (R², RMSE) quantifies accuracy

### 4. Practical Applications
- **Optimal placement zones** - where to grow spinach
- **Sensor network design** - minimum sensors for coverage
- **Climate control targets** - temperature/humidity setpoints
- **Harvest prediction** - biomass from environmental data

## Data Collection Requirements

### Environmental Parameters (from BME680)
- Temperature: ±0.5°C accuracy
- Humidity: ±3% RH accuracy
- Pressure: ±1 hPa accuracy
- Gas Resistance: VOC/air quality proxy

### Plant Measurements
- Fresh biomass (g): All 16 plants
- Height (cm): Optional
- Leaf area (cm²): Optional
- Days to harvest: Optional

### Sampling Frequency
- Environmental: Every 1-15 minutes
- Biomass: Weekly or at harvest
- Correlation: Time-averaged environmental vs growth

## Interpolation Strategy

### Method Selection
```python
# For 16 plants with 7 sensors, recommended:
method = 'cubic'  # Smooth gradients, good for sparse data

# Alternative for very sparse regions:
method = 'rbf'    # Radial Basis Function, flexible

# Avoid for this layout:
method = 'linear' # Too jagged with non-uniform spacing
```

### Validation Approach
```python
# Leave-one-out cross-validation
for each sensor:
    1. Remove sensor from dataset
    2. Interpolate using remaining 6 sensors
    3. Compare interpolated vs actual value
    4. Calculate RMSE, R²

# Expected performance:
# R² > 0.85 for temperature (strong gradients)
# R² > 0.75 for humidity (moderate gradients)
# R² > 0.60 for biomass (weaker correlations)
```

## Visualization Capabilities

The PlantMapper class will generate:

1. **Individual parameter maps** - temperature, humidity, pressure, resistance, biomass
2. **Multi-parameter comparison** - 2×2 grids showing all factors
3. **Plant location overlay** - rectangular pots (15×16 cm) on heatmaps
4. **Statistical overlays** - R², RMSE, mean, std dev
5. **Correlation analysis** - biomass vs environmental factors

## File Locations

- **Layout diagram**: `visualization/microclimate_layout.png`
- **Notebook**: `visualization/greenhouse_visualization_demo.ipynb`
- **Example script**: `visualization/example_plant_biomass.py`
- **Documentation**: `visualization/MICROCLIMATE_LAYOUT.md` (this file)

## Next Steps

1. **Deploy sensors** at the 7 specified positions
2. **Plant spinach** at all 16 positions with correct pot size
3. **Collect data** for 4-6 weeks (spinach growth cycle)
4. **Measure biomass** at harvest
5. **Run analysis** using the visualization tools
6. **Interpret results**:
   - Which zones had best growth?
   - How strong are temperature/growth correlations?
   - Is 44% sensor coverage sufficient?
   - Can we predict biomass from environmental data?

## Success Criteria

✅ **Layout verified**: No overlapping pots (15×16 cm)  
✅ **Coverage achieved**: 80% of greenhouse area  
✅ **Sensors distributed**: Corners, edges, center  
✅ **Zones represented**: Bottom, center, top sampled  
✅ **Non-uniform spacing**: Realistic microclimate variation  
✅ **Interpolation tested**: R² validation implemented  
✅ **Visualization ready**: PlantMapper configured for rectangular pots  

**The layout is optimized for measuring how microclimate influences spinach growth across a 4×4 foot greenhouse! 🌱**
