# Update Summary: Added 2 More Sensorless Plants

## Changes Made

### Plant Count Updated
- **Previous**: 14 total plants (7 with sensors, 7 without)
- **Updated**: 16 total plants (7 with sensors, 9 without)
- **Sensor Coverage**: 44% (down from 50%, more realistic scenario)

## New Plant Positions

### Added Plants:
1. **Plant 13** (NEW): Position (60, 108) cm - Row 4, between plants 12 and 14
2. **Plant 15** (NEW): Position (35, 28) cm - Between rows 1 and 2, filling a gap

### Strategic Placement:
- Plant 13 fills out the bottom row more evenly
- Plant 15 is positioned in a gap area to help improve interpolation coverage
- Both plants are **without sensors** (biomass measurements only)
- Placement simulates realistic greenhouse spacing with some irregularity

## Updated Distribution Pattern

```
Row 1:  P0●   P1○   P2●   P3○
              P15○(NEW)
Row 2:  P4○   P5●   P6○   P7●

Row 3:  P8●   P9○   P10●  P11○

Row 4:  P12●  P13○(NEW)  P14○

● = Plant with sensor (7 plants)
○ = Plant without sensor (9 plants)
```

## Files Updated

### 1. Jupyter Notebook
**File**: `greenhouse_visualization_demo.ipynb`

**Updated Cells**:
- Cell #33 (Plant Layout): Changed description from "14 plants" to "16 plants"
- Cell #34 (Plant Positions): Added 2 new plant positions
- Cell #34 (Sensor Flags): Added 2 new False entries for sensorless plants
- Cell #44 (Comparison View): Updated output text from "14 plants" to "16 plants"
- Cell #46 (Summary): Updated from "14 plants" to "16 plants" and added sensor coverage percentage

### 2. Example Script
**File**: `example_plant_biomass.py`

**Changes**:
- Updated plant_positions list: Added 2 new positions
- Updated has_sensor list: Added 2 False entries
- Updated plot title: "14 Plants" → "16 Plants"
- Updated comments: "14 plants" → "16 plants", "7 out of 14" → "7 out of 16"

### 3. Documentation
**File**: `PLANT_BIOMASS_MAPPING.md`

**Changes**:
- Typical Configuration: Updated from 14 to 16 plants, 7 to 9 without sensors
- Added sensor coverage percentage (44%)
- Recommended Setup: Updated range from "12-15" to "12-16" plants
- Updated coverage recommendation from "50-60%" to "40-50%"

## Impact on Analysis

### Benefits of Additional Sensorless Plants:

1. **Better Interpolation Coverage**: 
   - Plant 15 fills a gap between rows 1 and 2
   - Helps improve spatial interpolation accuracy in that region

2. **More Realistic Biomass Data**:
   - 16 data points instead of 14 for biomass interpolation
   - Better captures spatial variation

3. **Lower Sensor Coverage (More Realistic)**:
   - 44% coverage is more typical of real-world scenarios
   - Demonstrates tool's capability with sparser sensor networks
   - Shows interpolation works well even with <50% coverage

4. **More Statistical Power**:
   - Additional data points improve R² calculation
   - Better RMSE estimates
   - More robust correlation analysis

### Expected Changes in Results:

When you re-run the notebook cells, you should see:
- **R² value**: May improve slightly due to additional biomass data points
- **RMSE**: Might decrease with better spatial coverage
- **Visual**: Two additional plant markers on the maps
- **Statistics**: Updated plant counts in summary boxes

## How to Use the Updates

### Re-run the Notebook:
1. Execute cell #34 (plant positions) - will show "Total plants: 16"
2. Execute cell #35 (plant data generation) - will generate biomass for 16 plants
3. Execute cell #36 (PlantMapper setup)
4. Execute remaining cells to see updated visualizations

### Run the Updated Script:
```bash
cd visualization
python example_plant_biomass.py
```

Expected output:
- "Total plants: 16"
- "Plants with sensors: 7"
- "Plants without sensors: 9"
- Maps showing 16 plant locations

## Validation

To verify the changes are correct:

```python
# In the notebook, after running the setup cells:
print(f"Total plants: {len(plant_positions)}")  # Should be 16
print(f"With sensors: {sum(has_sensor)}")        # Should be 7
print(f"Without sensors: {len(has_sensor) - sum(has_sensor)}")  # Should be 9
print(f"Coverage: {sum(has_sensor)/len(has_sensor)*100:.1f}%")  # Should be ~43.8%
```

## Visual Changes

When you view the plots, you'll now see:
- **16 plant markers** instead of 14
- **7 filled circles** (dark green with white borders) - plants with sensors
- **9 hollow circles** (green outlines) - plants without sensors
- Plant 13 in the bottom row
- Plant 15 in the gap area between rows 1 and 2

All visualizations will automatically adjust to include the new plants!
