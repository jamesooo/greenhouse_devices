#!/usr/bin/env python3
"""
Setup script to test the greenhouse visualization environment.
Run this after installing requirements to verify everything works.
"""

import sys

def check_imports():
    """Check if all required packages can be imported."""
    print("Checking required packages...")
    packages = {
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'geopandas': 'GeoPandas',
        'matplotlib': 'Matplotlib',
        'scipy': 'SciPy',
        'shapely': 'Shapely',
        'psycopg2': 'psycopg2',
        'sqlalchemy': 'SQLAlchemy',
        'seaborn': 'Seaborn'
    }
    
    missing = []
    versions = {}
    
    for module_name, display_name in packages.items():
        try:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            versions[display_name] = version
            print(f"  ✓ {display_name}: {version}")
        except ImportError:
            missing.append(display_name)
            print(f"  ✗ {display_name}: NOT FOUND")
    
    return missing, versions

def check_local_modules():
    """Check if local modules can be imported."""
    print("\nChecking local modules...")
    try:
        from greenhouse_mapper import GreenhouseMapper
        print("  ✓ greenhouse_mapper")
    except ImportError as e:
        print(f"  ✗ greenhouse_mapper: {e}")
        return False
    
    try:
        from db_connector import TimescaleDBConnector
        print("  ✓ db_connector")
    except ImportError as e:
        print(f"  ✗ db_connector: {e}")
        return False
    
    return True

def run_basic_test():
    """Run a basic functionality test."""
    print("\nRunning basic functionality test...")
    try:
        from greenhouse_mapper import GreenhouseMapper
        
        # Create mapper
        mapper = GreenhouseMapper(width_cm=121.92, height_cm=121.92, resolution_cm=2.0)
        print(f"  ✓ Created mapper with grid shape: {mapper.x_grid.shape}")
        
        # Test data
        test_data = [
            {'temperature': 23.90, 'humidity': 48.43, 'pressure': 1009.11, 'resistance': 78424.00},
            {'temperature': 23.92, 'humidity': 48.44, 'pressure': 1009.15, 'resistance': 78773.00},
            {'temperature': 23.91, 'humidity': 48.44, 'pressure': 1009.11, 'resistance': 78773.00},
        ]
        
        mapper.set_sensor_data(test_data)
        print(f"  ✓ Added {len(test_data)} sensors")
        
        # Interpolate
        mapper.interpolate('temperature', method='linear')
        print("  ✓ Interpolation successful")
        
        # Get statistics
        stats = mapper.get_statistics('temperature')
        print(f"  ✓ Statistics calculated (R² = {stats.get('r_squared', 'N/A'):.4f})")
        
        print("\n✅ All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main setup check routine."""
    print("=" * 60)
    print("Greenhouse Visualization Tool - Setup Check")
    print("=" * 60)
    
    # Check imports
    missing, versions = check_imports()
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("\nPlease install missing packages:")
        print("  pip install -r requirements.txt")
        return 1
    
    # Check local modules
    if not check_local_modules():
        print("\n❌ Local modules not found or have errors")
        return 1
    
    # Run test
    if not run_basic_test():
        return 1
    
    print("\n" + "=" * 60)
    print("Setup verification complete!")
    print("You can now use the visualization tool.")
    print("Try running: jupyter notebook greenhouse_visualization_demo.ipynb")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
