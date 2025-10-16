# Greenhouse Microclimate Analysis Toolkit

**Streamlined visualization and statistical analysis tools for VPD-biomass experiments**

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Core packages:**
- NumPy, Pandas, Matplotlib, Seaborn, SciPy
- GeoPandas 0.14.0+ (for spatial operations)
- statsmodels, libpysal, esda, pykrige (for statistical analysis)

### 2. Run the Demo Notebook

```bash
jupyter notebook greenhouse_analysis_report.ipynb
```

The notebook demonstrates the **complete analysis workflow** using synthetic sample data. Simply replace the data loading section with your real experimental data when ready.

---

## File Structure

### Core Modules

| File | Purpose | Key Functions |
|------|---------|---------------|
| **data_generator.py** | Generate synthetic test data | `generate_sample_data()` |
| **statistical_plots.py** | All publication-quality visualizations | `plot_biomass_vs_vpd()`, `plot_spatial_heatmap()`, `plot_baseline_vs_treatment()`, `plot_morans_i_scatter()`, `plot_model_diagnostics()`, `create_summary_figure()` |
| **greenhouse_mapper.py** | Environmental interpolation (base class) | `interpolate()`, `plot_map()` |
| **plant_mapper.py** | Plant biomass mapping with rectangular pots | Extends `GreenhouseMapper` |
| **db_connector.py** | TimescaleDB interface | Database queries for real data |

### Interactive Notebooks

| File | Description |
|------|-------------|
| **greenhouse_analysis_report.ipynb** | **Main analysis workflow** - Run this with your data! |

### Utilities

| File | Purpose |
|------|---------|
| **setup_check.py** | Verify Python environment and dependencies |
| **setup_database.py** | Configure TimescaleDB connection (if using database) |

### Archive

Historical development files (old docs, example scripts, outdated visualizations) are in `archive/` for reference.

---

## Usage Examples

### Using Sample Data (Testing)

```python
from data_generator import generate_sample_data
from statistical_plots import plot_biomass_vs_vpd, plot_spatial_heatmap

# Generate synthetic data
data = generate_sample_data(seed=42)
final_data = data['plant_measurements'][data['plant_measurements']['week'] == 6]

# Create biomass vs VPD plot
fig = plot_biomass_vs_vpd(
    final_data,
    vpd_col='avg_vpd',
    biomass_col='biomass_g',
    save_path='biomass_vpd.png'
)
```

### Using Real Data (Production)

```python
from db_connector import GreenhouseDB
from statistical_plots import plot_spatial_heatmap

# Load data from database
db = GreenhouseDB()
env_data = db.query_environmental_data(start_week=3, end_week=6)
plant_data = db.query_plant_measurements()

# Create spatial heatmap
positions = list(zip(plant_data['position_x'], plant_data['position_y']))
fig = plot_spatial_heatmap(
    plant_positions=positions,
    values=plant_data['biomass_g'],
    parameter_name='Final Biomass (g)',
    humidifier_pos=(18, 18),
    save_path='biomass_heatmap.png'
)
```

---

## Data Requirements

### Environmental Data

**Format:** Pandas DataFrame or TimescaleDB table

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime | Recording time |
| `sensor_id` | int | Sensor identifier (1-7) |
| `temperature` | float | Temperature (°C) |
| `humidity` | float | Relative humidity (%) |
| `pressure` | float | Atmospheric pressure (hPa) |
| `vpd_kpa` | float | Vapor Pressure Deficit (kPa) |
| `position_x` | float | X coordinate (cm) |
| `position_y` | float | Y coordinate (cm) |
| `week` | int | Experiment week (0-6) |
| `period` | str | 'baseline' or 'treatment' |

### Plant Measurement Data

**Format:** Pandas DataFrame or CSV

| Column | Type | Description |
|--------|------|-------------|
| `plant_id` | int | Plant identifier (1-16) |
| `week` | int | Measurement week (0-6) |
| `height_cm` | float | Plant height (cm) |
| `leaf_count` | int | Number of leaves |
| `spad` | float | Chlorophyll content (SPAD units) |
| `biomass_g` | float | Fresh biomass (g) |
| `position_x` | float | X coordinate (cm) |
| `position_y` | float | Y coordinate (cm) |
| `avg_vpd` | float | Average VPD during period (kPa) |
| `has_sensor` | bool | True if plant has sensor |

---

## Visualization Gallery

### Primary Outcome: Biomass vs VPD
- **Function:** `plot_biomass_vs_vpd()`
- **Shows:** Quadratic relationship, optimal VPD, R² statistics
- **Use case:** Main research question visualization

### Spatial Heatmap
- **Function:** `plot_spatial_heatmap()`
- **Shows:** Interpolated environmental or biomass distribution
- **Use case:** Gradient validation, spatial pattern visualization

### Baseline vs Treatment Comparison
- **Function:** `plot_baseline_vs_treatment()`
- **Shows:** Dual panel - boxplot comparison + change vs VPD scatter
- **Use case:** Temporal effect demonstration

### Spatial Autocorrelation
- **Function:** `plot_morans_i_scatter()`
- **Shows:** Moran's I plot with spatial lag
- **Use case:** Test for spatial clustering

### Model Diagnostics
- **Function:** `plot_model_diagnostics()`
- **Shows:** 4-panel diagnostic (Q-Q, residuals, scale-location, histogram)
- **Use case:** Validate statistical model assumptions

### Summary Figure
- **Function:** `create_summary_figure()`
- **Shows:** Multi-panel comprehensive figure (6 panels)
- **Use case:** Publication-ready summary

---

## Workflow Overview

```
Collect Data → Load Data → Environmental Validation → Interpolation Quality Check →
Primary Analysis: Biomass vs VPD → Spatial Autocorrelation → Temporal Comparison →
Secondary Outcomes → Model Diagnostics → Generate Summary Report → Export Figures
```

**Follow this workflow in `greenhouse_analysis_report.ipynb`**

---

## Key Features

✅ **Geospatial Analysis** - Moran's I, spatial interpolation, kriging  
✅ **Statistical Rigor** - Quadratic regression, mixed models, repeated measures  
✅ **Publication Quality** - Customizable matplotlib settings, export to PNG/PDF  
✅ **Sample Data** - Test entire pipeline before real experiment  
✅ **Modular Design** - Use functions standalone or in notebooks  
✅ **Database Integration** - Direct TimescaleDB queries (optional)  

---

## Configuration

### Greenhouse Dimensions
- **Size:** 122 cm × 122 cm
- **Plants:** 16 total (7 with sensors)
- **Pot size:** 15 cm × 16 cm (rectangular)
- **Humidifier position:** (18, 18) cm

### Experiment Timeline
- **Baseline:** Weeks 0-2 (3 weeks)
- **Treatment:** Weeks 3-6 (4 weeks)
- **Measurements:** Weekly height, biomass, SPAD, leaf count

### Sensor Specifications
- **Model:** BME680 (Bosch)
- **Precision:** ±0.003°C temp, ±0.02% RH humidity
- **Sampling:** 1 Hz → 30s Telegraf averaging → TimescaleDB

---

## Troubleshooting

### Import Errors
```bash
# Verify environment
python setup_check.py

# Install missing packages
pip install -r requirements.txt
```

### Database Connection Issues
```bash
# Test database connectivity
python setup_database.py
```

### Interpolation Warnings
- Check sensor coverage (need ≥7 sensors)
- Verify coordinate ranges (0-122 cm)
- Use `method='linear'` for sparse data

---

## Documentation References

| Document | Location | Purpose |
|----------|----------|---------|
| **Protocol** | `docs/protocol.md` | Complete 6-week experimental procedure |
| **Statistical Plan** | `docs/STATISTICAL_ANALYSIS_PLAN.md` | Comprehensive analysis framework |
| **Precision Analysis** | `docs/SENSOR_PRECISION_ANALYSIS.md` | Sensor accuracy quantification |
| **Project Status** | `docs/PROJECT_STATUS.md` | Timeline and checklist |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2025-10-11 | Streamlined structure, created analysis notebook, archived WIP files |
| 0.9 | 2025-10-10 | Added statistical_plots.py, data_generator.py |
| 0.8 | 2025-10-09 | Updated for 16 plants, rectangular pots |
| 0.7 | 2025-10-08 | Initial microclimate layout |

---

## Support

For questions about experimental design, see `docs/critical.md`  
For statistical methods, see `docs/STATISTICAL_ANALYSIS_PLAN.md`  
For protocol details, see `docs/protocol.md`

---

**Ready to analyze your greenhouse data? Start with `greenhouse_analysis_report.ipynb`**
