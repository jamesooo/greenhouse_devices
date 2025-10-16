#!/usr/bin/env python3
"""
Simple example script demonstrating the greenhouse visualization tool.
This uses the 8-sensor test data provided by the user.
"""

from greenhouse_mapper import GreenhouseMapper
import matplotlib.pyplot as plt

def main():
    print("Greenhouse Environmental Data Visualization - Simple Example")
    print("=" * 70)
    
    # The 8 sensors with test data
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
    
    print(f"\nInitializing mapper for 4ft x 4ft greenhouse...")
    print(f"Resolution: 1cm")
    print(f"Number of sensors: {len(sensor_data)}")
    
    # Create mapper (4 feet = 121.92 cm)
    mapper = GreenhouseMapper(
        width_cm=121.92,
        height_cm=121.92,
        resolution_cm=1.0
    )
    
    print(f"Grid shape: {mapper.x_grid.shape}")
    print(f"Total interpolation points: {mapper.x_grid.size:,}")
    
    # Set sensor data
    print("\nSetting sensor data...")
    mapper.set_sensor_data(sensor_data)
    
    print("\nSensor positions (auto-generated):")
    for idx, row in mapper.sensors.iterrows():
        print(f"  Sensor {int(row['sensor_id'])}: ({row['x']:.1f}, {row['y']:.1f}) cm - "
              f"T={row['temperature']}°C, RH={row['humidity']}%")
    
    # Generate interpolated maps
    print("\nGenerating interpolated maps...")
    print("  - Temperature")
    print("  - Humidity")
    print("  - Pressure")
    print("  - Gas Resistance")
    
    # Create comprehensive visualization
    fig = mapper.plot_all_parameters(figsize=(20, 16), cmap='viridis')
    
    # Save to file
    output_file = 'greenhouse_environmental_map.png'
    fig.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved visualization to: {output_file}")
    
    # Display statistics
    print("\n" + "=" * 70)
    print("STATISTICAL SUMMARY")
    print("=" * 70)
    
    all_stats = mapper.get_statistics()
    
    for param in ['temperature', 'humidity', 'pressure', 'resistance']:
        stats = all_stats[param]
        units = {
            'temperature': '°C',
            'humidity': '% RH',
            'pressure': 'hPa',
            'resistance': 'Ω'
        }[param]
        
        print(f"\n{param.upper()}:")
        print(f"  Mean:       {stats['mean']:.4f} {units}")
        print(f"  Std Dev:    {stats['std']:.4f}")
        print(f"  Range:      {stats['range']:.4f} ({stats['min']:.4f} - {stats['max']:.4f})")
        print(f"  R²:         {stats['r_squared']:.4f}")
        print(f"  RMSE:       {stats['rmse']:.4f}")
    
    print("\n" + "=" * 70)
    print("\nR² values close to 1.0 indicate good interpolation quality.")
    print("These values are calculated using leave-one-out cross-validation.")
    
    # Show the plot
    print("\nDisplaying visualization...")
    plt.show()
    
    print("\n✓ Done! Check the saved image file.")

if __name__ == '__main__':
    main()
