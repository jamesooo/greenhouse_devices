#!/usr/bin/env python3
"""
Plant Biomass Mapping Example

Demonstrates mapping fresh biomass across 14 plants where only 7 have sensors.
This is a realistic greenhouse scenario with mixed measured/unmeasured plants.
"""

from plant_mapper import PlantMapper
import matplotlib.pyplot as plt
import numpy as np

def main():
    print("=" * 80)
    print("Plant Biomass Mapping - Greenhouse Example")
    print("Microclimate Study: Non-Uniform Distribution")
    print("=" * 80)
    
    # Plant positions - spread across full greenhouse for microclimate sampling
    # Non-uniform spacing to capture environmental gradients
    plant_positions = [
        # Bottom zone
        ( 18,  18), ( 38,  25), ( 25,  45),
        ( 88,  22), (108,  38),
        # Center zone
        ( 95,  55), ( 42,  62), ( 65,  68), ( 85,  78),
        # Top zone
        ( 15,  80), ( 35,  92), ( 22, 108),
        ( 58,  95), ( 75, 100), ( 95, 105), (112, 115),
    ]
    
    # Which plants have sensors (7 out of 16)
    # IMPROVED DISTRIBUTION: Better left-right balance, covers all zones
    # Sensors measure: temperature, humidity, pressure, gas resistance
    # Non-sensors measure: biomass only
    has_sensor = [
        True, False, False,  # Bottom-left: P0=sensor
        True, False, True,   # Bottom-right: P3,P5=sensors
        False, True, False,  # Center: P7=sensor
        False, True, False,  # Upper-left: P10=sensor
        True, False, True, False  # Upper-right: P12,P14=sensors
    ]
    
    print(f"\nSetup:")
    print(f"  Total plants: {len(plant_positions)}")
    print(f"  Plants with sensors: {sum(has_sensor)}")
    print(f"  Plants without sensors: {len(has_sensor) - sum(has_sensor)}")
    
    # Environmental readings from BME680 sensors (for the 7 plants with sensors)
    env_readings = [
        {'temperature': 23.90, 'humidity': 48.43, 'pressure': 1009.11, 'resistance': 78424.00},
        {'temperature': 23.92, 'humidity': 48.44, 'pressure': 1009.15, 'resistance': 78773.00},
        {'temperature': 23.91, 'humidity': 48.44, 'pressure': 1009.11, 'resistance': 78773.00},
        {'temperature': 23.93, 'humidity': 48.44, 'pressure': 1009.11, 'resistance': 78703.00},
        {'temperature': 23.92, 'humidity': 48.45, 'pressure': 1009.11, 'resistance': 78493.00},
        {'temperature': 23.86, 'humidity': 48.46, 'pressure': 1009.13, 'resistance': 78843.00},
        {'temperature': 23.93, 'humidity': 48.46, 'pressure': 1009.13, 'resistance': 78354.00},
    ]
    
    # Generate biomass data for all plants
    # Simulate spatial gradient (better growth in upper-right area)
    np.random.seed(42)
    
    plant_data = []
    sensor_idx = 0
    
    for i, (pos, has_sens) in enumerate(zip(plant_positions, has_sensor)):
        x, y = pos
        
        # Spatial gradient: plants at different positions grow differently
        spatial_factor = (x + y) / 240.0  # 0-1 normalized
        base_biomass = 25 + spatial_factor * 15  # 25-40g base range
        
        # Add random variation
        random_variation = np.random.normal(0, 3)
        biomass = base_biomass + random_variation
        
        # Plant data
        data = {
            'biomass_g': round(biomass, 1),
            'height_cm': round(15 + biomass * 0.8, 1),
            'leaf_area_cm2': round(biomass * 12, 1),
        }
        
        # Add environmental data for plants with sensors
        if has_sens:
            data.update(env_readings[sensor_idx])
            sensor_idx += 1
        
        plant_data.append(data)
    
    print(f"\nBiomass Range: {min(d['biomass_g'] for d in plant_data):.1f} - {max(d['biomass_g'] for d in plant_data):.1f} g")
    
    # Create PlantMapper with pot dimensions
    print("\nInitializing PlantMapper...")
    # Pot size: 5.9" x 6.3" = 15.0 cm x 16.0 cm
    mapper = PlantMapper(
        width_cm=121.92, 
        height_cm=121.92, 
        resolution_cm=1.0,
        pot_width_cm=15.0,   # 5.9 inches
        pot_height_cm=16.0   # 6.3 inches
    )
    mapper.set_plant_data(plant_data, plant_positions, has_sensor)
    
    # Generate biomass interpolation map
    print("\nGenerating biomass interpolation map...")
    fig1 = mapper.plot_plant_map(
        parameter='biomass_g',
        figsize=(14, 12),
        cmap='YlGn',
        show_plants=True,
        show_stats=True,
        title='Fresh Biomass Distribution - 16 Plants (7 with sensors)'
    )
    
    output_file = 'plant_biomass_map.png'
    fig1.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to: {output_file}")
    
    # Create comprehensive comparison
    print("\nGenerating comprehensive comparison (biomass + environmental)...")
    fig2 = mapper.plot_plant_comparison(figsize=(20, 10))
    
    output_file2 = 'plant_comprehensive_analysis.png'
    fig2.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to: {output_file2}")
    
    # Statistics
    print("\n" + "=" * 80)
    print("BIOMASS INTERPOLATION STATISTICS")
    print("=" * 80)
    
    stats = mapper.get_statistics('biomass_g')
    print(f"  Mean biomass:       {stats['mean']:.2f} g")
    print(f"  Std Dev:            {stats['std']:.2f} g")
    print(f"  Range:              {stats['range']:.2f} g ({stats['min']:.2f} - {stats['max']:.2f})")
    print(f"  R² (quality):       {stats['r_squared']:.4f}")
    print(f"  RMSE:               {stats['rmse']:.2f} g")
    print(f"  Plants measured:    {stats['num_sensors']}")
    
    print("\n" + "=" * 80)
    print("Interpretation:")
    print(f"  - R² = {stats['r_squared']:.4f} indicates {'excellent' if stats['r_squared'] > 0.9 else 'good' if stats['r_squared'] > 0.7 else 'moderate'} interpolation quality")
    print(f"  - The model predicts biomass with ±{stats['rmse']:.2f}g average error")
    print(f"  - {len(plant_data)} total plants mapped with data from {sum(has_sensor)} sensors")
    
    # Correlations for plants with sensors
    print("\n" + "=" * 80)
    print("ENVIRONMENTAL CORRELATIONS (Plants with sensors only)")
    print("=" * 80)
    
    measured = mapper.measured_plants
    if len(measured) > 2:
        import pandas as pd
        temp_corr = measured[['biomass_g', 'temperature']].corr().iloc[0, 1]
        hum_corr = measured[['biomass_g', 'humidity']].corr().iloc[0, 1]
        pres_corr = measured[['biomass_g', 'pressure']].corr().iloc[0, 1]
        
        print(f"  Biomass vs Temperature: {temp_corr:+.3f}")
        print(f"  Biomass vs Humidity:    {hum_corr:+.3f}")
        print(f"  Biomass vs Pressure:    {pres_corr:+.3f}")
    
    print("\n" + "=" * 80)
    print("✓ Analysis complete! Check the generated PNG files.")
    print("=" * 80)
    
    # Show plots
    plt.show()

if __name__ == '__main__':
    main()
