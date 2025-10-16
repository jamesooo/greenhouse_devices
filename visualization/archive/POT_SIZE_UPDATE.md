# Rectangular Pot Visualization Update

## Summary

Updated the PlantMapper visualization to represent each plant as a rectangular pot instead of circular markers. The pot dimensions are configurable and default to **5.9" × 6.3"** (converted to **15.0 cm × 16.0 cm** in metric).

## Changes Made

### 1. PlantMapper Class (`plant_mapper.py`)

#### Constructor Update
- Added `pot_width_cm` parameter (default: 15.0 cm = 5.9")
- Added `pot_height_cm` parameter (default: 16.0 cm = 6.3")
- Stores pot dimensions as instance variables for use in plotting

#### Import Update
- Added `Rectangle` to matplotlib.patches imports

#### Plotting Methods Updated
Two methods were updated to use rectangular patches instead of circular scatter plots:

**`plot_plant_map()` method:**
- Measured plants (with sensors): Filled green rectangles with white borders
- Unmeasured plants (without sensors): Hollow rectangles with green borders
- Rectangles are centered on plant positions
- Legend entries use square markers (`marker='s'`) to match rectangular visualization

**`plot_plant_comparison()` method:**
- Updated to use same rectangular patch approach
- Maintains visual consistency across all plot types

### 2. Jupyter Notebook (`greenhouse_visualization_demo.ipynb`)

Updated the PlantMapper initialization cell to include pot size parameters:

```python
# Initialize PlantMapper with pot dimensions
# Pot size: 5.9" x 6.3" = 15.0 cm x 16.0 cm
plant_mapper = PlantMapper(
    width_cm=121.92, 
    height_cm=121.92, 
    resolution_cm=1.0,
    pot_width_cm=15.0,   # 5.9 inches
    pot_height_cm=16.0   # 6.3 inches
)
```

### 3. Example Script (`example_plant_biomass.py`)

Updated the PlantMapper initialization to match the notebook:
- Added pot dimension parameters with comments explaining the conversion from inches

### 4. Documentation (`PLANT_BIOMASS_MAPPING.md`)

Updated documentation to reflect rectangular pot visualization:
- Added pot size to feature list
- Updated configuration section to show pot dimensions
- Changed ASCII diagram to use filled squares (■) and hollow squares (□) instead of circles
- Updated code examples to show pot size parameters

## Visualization Changes

### Before
- Plants shown as circles (filled for measured, hollow for unmeasured)
- Size based on `s` parameter in scatter plot
- Harder to see actual pot footprint

### After
- Plants shown as rectangles matching actual pot dimensions
- Measured plants: Filled green rectangles with white borders
- Unmeasured plants: Hollow rectangles with green borders
- True-to-scale representation of pot footprint on greenhouse floor
- Better visualization of spatial coverage and plant density

## Technical Details

### Metric Conversion
- **5.9 inches** = 14.986 cm ≈ **15.0 cm**
- **6.3 inches** = 16.002 cm ≈ **16.0 cm**

### Rectangle Positioning
Rectangles are drawn from their lower-left corner, so the code offsets by half the pot width and height to center them on the plant position coordinates:

```python
Rectangle(
    (x - pot_width_cm / 2, y - pot_height_cm / 2),  # Lower-left corner
    pot_width_cm,                                     # Width
    pot_height_cm,                                    # Height
    ...
)
```

### Customization
Users can customize pot sizes when creating a PlantMapper:

```python
# Example: Smaller 4" × 4" pots
mapper = PlantMapper(
    width_cm=121.92,
    height_cm=121.92,
    pot_width_cm=10.16,   # 4 inches
    pot_height_cm=10.16   # 4 inches
)

# Example: Larger 7" × 8" pots
mapper = PlantMapper(
    width_cm=121.92,
    height_cm=121.92,
    pot_width_cm=17.78,   # 7 inches
    pot_height_cm=20.32   # 8 inches
)
```

## Backward Compatibility

The changes are **fully backward compatible**:
- Default values are provided for `pot_width_cm` and `pot_height_cm`
- Existing code without pot parameters will work with default 15cm × 16cm pots
- All previous functionality remains unchanged

## Files Modified

1. `/visualization/plant_mapper.py` - Core class updates
2. `/visualization/greenhouse_visualization_demo.ipynb` - Notebook demonstration
3. `/visualization/example_plant_biomass.py` - Standalone example script
4. `/visualization/PLANT_BIOMASS_MAPPING.md` - Documentation updates

## Usage Example

```python
from plant_mapper import PlantMapper

# Initialize with custom pot size
mapper = PlantMapper(
    width_cm=121.92,
    height_cm=121.92,
    resolution_cm=1.0,
    pot_width_cm=15.0,   # 5.9"
    pot_height_cm=16.0   # 6.3"
)

# Load plant data
mapper.set_plant_data(plant_data, plant_positions, has_sensor)

# Create visualizations - rectangles are automatically used
fig = mapper.plot_plant_map('biomass_g')
fig_comparison = mapper.plot_plant_comparison()
```

## Next Steps

To see the new rectangular pot visualization:
1. Re-run the notebook cells starting from the PlantMapper initialization
2. Or run `python example_plant_biomass.py`
3. The plots will now show rectangular pots instead of circular markers

The rectangular visualization provides a more realistic representation of the actual greenhouse layout and helps users better understand spatial relationships between plants and pot coverage.
