"""
Database schema setup script for greenhouse sensor data.
Creates the necessary tables for storing sensor data and positions in TimescaleDB.
"""

from sqlalchemy import create_engine, text
import sys


def create_sensor_data_table(engine):
    """Create the main sensor data hypertable."""
    
    # Create table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS sensor_data (
        time TIMESTAMPTZ NOT NULL,
        device_id TEXT NOT NULL,
        temperature DOUBLE PRECISION,
        humidity DOUBLE PRECISION,
        pressure DOUBLE PRECISION,
        gas_resistance DOUBLE PRECISION,
        PRIMARY KEY (time, device_id)
    );
    """
    
    # Create hypertable (TimescaleDB-specific)
    create_hypertable_sql = """
    SELECT create_hypertable('sensor_data', 'time', 
                            if_not_exists => TRUE,
                            migrate_data => TRUE);
    """
    
    # Create indexes for better query performance
    create_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_sensor_data_device_id 
        ON sensor_data (device_id, time DESC);
    """
    
    with engine.connect() as conn:
        print("Creating sensor_data table...")
        conn.execute(text(create_table_sql))
        conn.commit()
        
        print("Converting to hypertable...")
        try:
            conn.execute(text(create_hypertable_sql))
            conn.commit()
        except Exception as e:
            print(f"  Note: {e}")
        
        print("Creating indexes...")
        conn.execute(text(create_indexes_sql))
        conn.commit()
        
    print("✓ sensor_data table created successfully")


def create_sensor_positions_table(engine):
    """Create the sensor positions table."""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS sensor_positions (
        sensor_id TEXT PRIMARY KEY,
        x_position_cm DOUBLE PRECISION NOT NULL,
        y_position_cm DOUBLE PRECISION NOT NULL,
        z_position_cm DOUBLE PRECISION DEFAULT 0,
        description TEXT,
        installed_date TIMESTAMPTZ DEFAULT NOW(),
        active BOOLEAN DEFAULT TRUE
    );
    """
    
    with engine.connect() as conn:
        print("Creating sensor_positions table...")
        conn.execute(text(create_table_sql))
        conn.commit()
        
    print("✓ sensor_positions table created successfully")


def insert_sample_positions(engine, num_sensors=8):
    """Insert sample sensor positions."""
    
    # Auto-generate positions for demo
    import numpy as np
    
    # Simple grid layout
    cols = int(np.ceil(np.sqrt(num_sensors)))
    rows = int(np.ceil(num_sensors / cols))
    
    margin = 10
    width = 121.92
    height = 121.92
    x_spacing = (width - 2 * margin) / (cols - 1) if cols > 1 else 0
    y_spacing = (height - 2 * margin) / (rows - 1) if rows > 1 else 0
    
    positions = []
    for i in range(num_sensors):
        row = i // cols
        col = i % cols
        x = margin + col * x_spacing
        y = margin + row * y_spacing
        positions.append((f"sensor_{i}", x, y, f"Sensor {i}"))
    
    # Insert positions
    insert_sql = """
    INSERT INTO sensor_positions (sensor_id, x_position_cm, y_position_cm, description)
    VALUES (:sensor_id, :x, :y, :desc)
    ON CONFLICT (sensor_id) DO UPDATE 
    SET x_position_cm = EXCLUDED.x_position_cm,
        y_position_cm = EXCLUDED.y_position_cm,
        description = EXCLUDED.description;
    """
    
    with engine.connect() as conn:
        print(f"Inserting {num_sensors} sample sensor positions...")
        for sensor_id, x, y, desc in positions:
            conn.execute(text(insert_sql), {
                'sensor_id': sensor_id,
                'x': x,
                'y': y,
                'desc': desc
            })
        conn.commit()
        
    print("✓ Sample sensor positions inserted")


def insert_sample_data(engine):
    """Insert the test data from the user."""
    
    test_data = [
        (23.90, 48.43, 1009.11, 78424.00),
        (23.92, 48.44, 1009.15, 78773.00),
        (23.91, 48.44, 1009.11, 78773.00),
        (23.93, 48.44, 1009.11, 78703.00),
        (23.92, 48.45, 1009.11, 78493.00),
        (23.86, 48.46, 1009.13, 78843.00),
        (23.93, 48.46, 1009.13, 78354.00),
        (23.92, 48.47, 1009.11, 78633.00),
    ]
    
    insert_sql = """
    INSERT INTO sensor_data (time, device_id, temperature, humidity, pressure, gas_resistance)
    VALUES (NOW(), :device_id, :temp, :humidity, :pressure, :resistance);
    """
    
    with engine.connect() as conn:
        print(f"Inserting {len(test_data)} sample sensor readings...")
        for i, (temp, humidity, pressure, resistance) in enumerate(test_data):
            conn.execute(text(insert_sql), {
                'device_id': f'sensor_{i}',
                'temp': temp,
                'humidity': humidity,
                'pressure': pressure,
                'resistance': resistance
            })
        conn.commit()
        
    print("✓ Sample sensor data inserted")


def setup_database(host='localhost', port=5432, database='greenhouse',
                  user='postgres', password='postgres',
                  insert_samples=True):
    """
    Complete database setup.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        insert_samples: Whether to insert sample data
    """
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    print(f"\nConnecting to database: {database} at {host}:{port}")
    print(f"User: {user}")
    print("-" * 60)
    
    try:
        engine = create_engine(connection_string)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"Connected! PostgreSQL version: {version[:50]}...")
        
        # Create tables
        create_sensor_data_table(engine)
        create_sensor_positions_table(engine)
        
        # Insert samples if requested
        if insert_samples:
            print("\nInserting sample data...")
            insert_sample_positions(engine, num_sensors=8)
            insert_sample_data(engine)
        
        print("\n" + "=" * 60)
        print("✅ Database setup complete!")
        print("=" * 60)
        
        engine.dispose()
        return 0
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    # You can customize these parameters
    result = setup_database(
        host='localhost',
        port=5432,
        database='greenhouse',
        user='postgres',
        password='postgres',
        insert_samples=True
    )
    
    sys.exit(result)
