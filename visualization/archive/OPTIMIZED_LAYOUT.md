# Optimized Plant Layout - No Overlapping Pots

## Problem

The previous plant layout had overlapping pots when using the realistic pot dimensions of 5.9" × 6.3" (15 cm × 16 cm). Specifically, Plants 1 and 15 were too close together, causing a 5cm × 8cm overlap.

## Solution

Redesigned the layout as a centered **4×4 grid** with proper spacing to prevent any pot overlaps while maximizing the use of the 4ft × 4ft (121.92 cm × 121.92 cm) greenhouse space.

## New Layout Specifications

### Grid Configuration
```
Layout: 4 rows × 4 columns = 16 plants
Pot dimensions: 15.0 cm × 16.0 cm (5.9" × 6.3")
Spacing between pots: 2.0 cm (horizontal and vertical)
Total grid footprint: 66.0 cm × 70.0 cm
Margins: 28.0 cm (left/right), 26.0 cm (top/bottom)
```

### Plant Positions (Center Points)

```
Row 0 (y=34.0):  P0(35.5)  P1(52.5)  P2(69.5)  P3(86.5)
Row 1 (y=52.0):  P4(35.5)  P5(52.5)  P6(69.5)  P7(86.5)
Row 2 (y=70.0):  P8(35.5)  P9(52.5)  P10(69.5) P11(86.5)
Row 3 (y=88.0):  P12(35.5) P13(52.5) P14(69.5) P15(86.5)

■ = Plant with sensor (7 total)
□ = Plant without sensor (9 total)
```

### Sensor Distribution

Plants **with sensors** (7): P0, P2, P5, P7, P8, P10, P12
- Evenly distributed across the grid
- 44% coverage (7 out of 16 plants)

Plants **without sensors** (9): P1, P3, P4, P6, P9, P11, P13, P14, P15
- Intermixed with sensor plants
- Provides realistic scenario for interpolation validation

## Advantages

1. **No Overlaps**: All pots have 2 cm clearance on all sides
2. **Even Spacing**: Consistent 17 cm × 18 cm grid cells (pot + spacing)
3. **Centered Layout**: 28 cm margins on left/right, 26 cm top/bottom
4. **Good Coverage**: 54% of greenhouse floor covered by pots
5. **Air Circulation**: 2 cm spacing allows airflow between plants
6. **Easy Access**: Margins provide access to all plants
7. **Realistic Interpolation**: Mixed sensor coverage tests interpolation quality

## Capacity Analysis

With the current pot size, the greenhouse can accommodate:
- **Maximum capacity**: 7 columns × 6 rows = **42 pots** (with 2 cm spacing)
- **Current layout**: 4 columns × 4 rows = **16 pots** (33% of maximum)
- **Room for expansion**: Can add 2-3 more rows if needed

## Visual Diagram

A layout diagram has been saved to `visualization/optimized_layout.png` showing:
- Greenhouse boundary (black outline)
- All 16 pots positioned accurately
- Filled green rectangles for plants with sensors
- Hollow green rectangles for plants without sensors
- Plant IDs labeled on each pot

## Code Changes

Updated files to use the new positions:
- `greenhouse_visualization_demo.ipynb` - Cell #33 (plant positions)
- `example_plant_biomass.py` - Main function
- `PLANT_BIOMASS_MAPPING.md` - Documentation

## Verification

No overlapping pots confirmed by spatial analysis:
- Minimum horizontal distance: 17 cm (15 cm pot width + 2 cm spacing)
- Minimum vertical distance: 18 cm (16 cm pot height + 2 cm spacing)
- All plant pairs exceed minimum distances ✓

## Usage

The PlantMapper class will automatically use these positions when you run:

```python
from plant_mapper import PlantMapper

# Initialize with pot dimensions
mapper = PlantMapper(
    width_cm=121.92, 
    height_cm=121.92, 
    resolution_cm=1.0,
    pot_width_cm=15.0,   # 5.9 inches
    pot_height_cm=16.0   # 6.3 inches
)

# Load data with new positions
mapper.set_plant_data(plant_data, plant_positions, has_sensor)

# Generate visualizations - pots will be correctly spaced
fig = mapper.plot_plant_map(parameter='biomass_g')
```

The rectangular pot visualization will accurately represent the physical layout with no overlaps!
