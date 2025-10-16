"""
TimescaleDB Connector for Greenhouse Sensor Data

Provides methods to query sensor data from TimescaleDB for visualization.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional, List, Dict
from datetime import datetime, timedelta


class TimescaleDBConnector:
    """
    Connector for querying greenhouse sensor data from TimescaleDB.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 5432,
                 database: str = 'greenhouse', user: str = 'postgres',
                 password: str = 'postgres'):
        """
        Initialize database connection.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.connection_string = (
            f"postgresql://{user}:{password}@{host}:{port}/{database}"
        )
        self.engine = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(self.connection_string)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Successfully connected to TimescaleDB")
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            print("Disconnected from TimescaleDB")
    
    def query_sensor_data(self, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         sensor_ids: Optional[List[str]] = None,
                         table_name: str = 'sensor_data') -> pd.DataFrame:
        """
        Query sensor data from TimescaleDB.
        
        Args:
            start_time: Start of time range (default: 1 hour ago)
            end_time: End of time range (default: now)
            sensor_ids: List of sensor IDs to query (default: all)
            table_name: Name of the sensor data table
            
        Returns:
            DataFrame with columns: timestamp, sensor_id, temperature, humidity, 
                                   pressure, resistance
        """
        if not self.engine:
            self.connect()
        
        # Default time range: last hour
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)
        
        # Build query
        query = f"""
            SELECT 
                time as timestamp,
                device_id as sensor_id,
                temperature,
                humidity,
                pressure,
                gas_resistance as resistance
            FROM {table_name}
            WHERE time >= :start_time AND time <= :end_time
        """
        
        params = {
            'start_time': start_time,
            'end_time': end_time
        }
        
        if sensor_ids:
            query += " AND device_id = ANY(:sensor_ids)"
            params['sensor_ids'] = sensor_ids
        
        query += " ORDER BY time DESC"
        
        # Execute query
        try:
            df = pd.read_sql(text(query), self.engine, params=params)
            return df
        except Exception as e:
            print(f"Query failed: {e}")
            raise
    
    def query_latest_readings(self, 
                             sensor_ids: Optional[List[str]] = None,
                             table_name: str = 'sensor_data') -> pd.DataFrame:
        """
        Get the latest reading from each sensor.
        
        Args:
            sensor_ids: List of sensor IDs (default: all)
            table_name: Name of the sensor data table
            
        Returns:
            DataFrame with latest reading for each sensor
        """
        if not self.engine:
            self.connect()
        
        query = f"""
            SELECT DISTINCT ON (device_id)
                time as timestamp,
                device_id as sensor_id,
                temperature,
                humidity,
                pressure,
                gas_resistance as resistance
            FROM {table_name}
        """
        
        params = {}
        
        if sensor_ids:
            query += " WHERE device_id = ANY(:sensor_ids)"
            params['sensor_ids'] = sensor_ids
        
        query += " ORDER BY device_id, time DESC"
        
        try:
            df = pd.read_sql(text(query), self.engine, params=params)
            return df
        except Exception as e:
            print(f"Query failed: {e}")
            raise
    
    def query_time_averaged(self,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           sensor_ids: Optional[List[str]] = None,
                           interval: str = '5 minutes',
                           table_name: str = 'sensor_data') -> pd.DataFrame:
        """
        Query time-averaged sensor data.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            sensor_ids: List of sensor IDs
            interval: Time bucket interval (e.g., '5 minutes', '1 hour')
            table_name: Name of the sensor data table
            
        Returns:
            DataFrame with time-averaged data
        """
        if not self.engine:
            self.connect()
        
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)
        
        query = f"""
            SELECT 
                time_bucket(:interval, time) as timestamp,
                device_id as sensor_id,
                AVG(temperature) as temperature,
                AVG(humidity) as humidity,
                AVG(pressure) as pressure,
                AVG(gas_resistance) as resistance,
                COUNT(*) as sample_count
            FROM {table_name}
            WHERE time >= :start_time AND time <= :end_time
        """
        
        params = {
            'interval': interval,
            'start_time': start_time,
            'end_time': end_time
        }
        
        if sensor_ids:
            query += " AND device_id = ANY(:sensor_ids)"
            params['sensor_ids'] = sensor_ids
        
        query += " GROUP BY timestamp, device_id ORDER BY timestamp DESC"
        
        try:
            df = pd.read_sql(text(query), self.engine, params=params)
            return df
        except Exception as e:
            print(f"Query failed: {e}")
            raise
    
    def get_sensor_positions(self, 
                            table_name: str = 'sensor_positions') -> pd.DataFrame:
        """
        Get sensor positions from database.
        
        Args:
            table_name: Name of the sensor positions table
            
        Returns:
            DataFrame with columns: sensor_id, x_cm, y_cm
        """
        if not self.engine:
            self.connect()
        
        query = f"""
            SELECT 
                sensor_id,
                x_position_cm as x,
                y_position_cm as y
            FROM {table_name}
        """
        
        try:
            df = pd.read_sql(text(query), self.engine)
            return df
        except Exception as e:
            print(f"Query failed: {e}")
            print("Note: sensor_positions table may not exist yet")
            return pd.DataFrame(columns=['sensor_id', 'x', 'y'])
    
    def prepare_data_for_mapper(self, 
                               sensor_data_df: pd.DataFrame,
                               sensor_positions_df: Optional[pd.DataFrame] = None) -> tuple:
        """
        Prepare data in the format expected by GreenhouseMapper.
        
        Args:
            sensor_data_df: DataFrame from query methods
            sensor_positions_df: DataFrame with sensor positions (optional)
            
        Returns:
            Tuple of (sensor_data_list, sensor_positions_list)
        """
        # Group by sensor and get latest/average reading
        if 'timestamp' in sensor_data_df.columns:
            # Get latest reading for each sensor
            latest = sensor_data_df.sort_values('timestamp', ascending=False)
            latest = latest.groupby('sensor_id').first().reset_index()
        else:
            latest = sensor_data_df
        
        # Convert to list of dicts
        sensor_data = []
        for _, row in latest.iterrows():
            sensor_data.append({
                'temperature': row.get('temperature'),
                'humidity': row.get('humidity'),
                'pressure': row.get('pressure'),
                'resistance': row.get('resistance')
            })
        
        # Get positions if available
        sensor_positions = None
        if sensor_positions_df is not None and not sensor_positions_df.empty:
            # Match sensor IDs
            positions = []
            for sensor_id in latest['sensor_id']:
                pos_row = sensor_positions_df[sensor_positions_df['sensor_id'] == sensor_id]
                if not pos_row.empty:
                    positions.append((
                        float(pos_row.iloc[0]['x']),
                        float(pos_row.iloc[0]['y'])
                    ))
                else:
                    positions.append(None)
            
            # Only use if all sensors have positions
            if None not in positions:
                sensor_positions = positions
        
        return sensor_data, sensor_positions
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
