"""
Sample Data Generator for Greenhouse Microclimate Experiment

Generates realistic synthetic data matching the experimental design:
- 16 spinach plants (7 with sensors, 9 without)
- 6-week timeline (2 baseline + 4 treatment)
- VPD gradient from humidifier (0.5-1.1 kPa)
- Weekly plant measurements (height, biomass, SPAD, leaf count)
- Environmental data (temperature, humidity, pressure)

This data is for visualization testing only - do not use for actual statistical inference!
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Dict, List


class GreenhouseDataGenerator:
    """Generate realistic synthetic data for greenhouse experiment."""
    
    def __init__(self, seed: int = 42):
        """
        Initialize data generator.
        
        Parameters
        ----------
        seed : int
            Random seed for reproducibility
        """
        np.random.seed(seed)
        
        # Plant positions (cm from bottom-left corner)
        # Pots are 15×16cm, humidifier is 15×20cm at (18, 18)
        # Minimum spacing: 24cm between pot centers to prevent overlap
        # Base grid with randomization to look natural
        base_positions = [
            (35, 28),   # P0 - sensor (near humidifier at 18,18)
            (60, 26),   # P1
            (85, 29),   # P2
            (110, 27),  # P3 - sensor
            (37, 53),   # P4
            (62, 51),   # P5 - sensor
            (87, 54),   # P6
            (112, 52),  # P7 - sensor
            (35, 78),   # P8
            (61, 80),   # P9
            (25, 104),  # P10 - sensor (far from humidifier, moved left)
            (86, 77),   # P11
            (111, 79),  # P12 - sensor
            (51, 103),  # P13 (moved right to avoid P10)
            (76, 102),  # P14 - sensor
            (101, 105)  # P15
        ]
        
        # Add small random jitter (±2cm) for natural appearance
        # Reduced jitter to maintain minimum spacing
        self.plant_positions = []
        for x, y in base_positions:
            jitter_x = np.random.uniform(-2, 2)
            jitter_y = np.random.uniform(-2, 2)
            self.plant_positions.append((x + jitter_x, y + jitter_y))
        
        # Sensor equipped plants (indices)
        self.has_sensor = [0, 3, 5, 7, 10, 12, 14]
        
        # Humidifier position and size (15cm × 20cm)
        self.humidifier_pos = (18, 18)
        
        # Experimental timeline
        self.start_date = datetime(2025, 10, 15)  # Week 1 start
        self.baseline_weeks = 2
        self.treatment_weeks = 4
        
    def _distance_from_humidifier(self, x: float, y: float) -> float:
        """Calculate Euclidean distance from humidifier."""
        hx, hy = self.humidifier_pos
        return np.sqrt((x - hx)**2 + (y - hy)**2)
    
    def _generate_vpd_gradient(self, x: float, y: float, period: str) -> float:
        """
        Generate VPD based on distance from humidifier.
        
        Parameters
        ----------
        x, y : float
            Plant coordinates (cm)
        period : str
            'baseline' or 'treatment'
            
        Returns
        -------
        float
            VPD in kPa
        """
        distance = self._distance_from_humidifier(x, y)
        
        if period == 'baseline':
            # Natural VPD, relatively uniform
            base_vpd = 0.75
            spatial_var = 0.05 * (distance / 100)  # Slight variation
            noise = np.random.normal(0, 0.02)
            return np.clip(base_vpd + spatial_var + noise, 0.6, 0.9)
        
        else:  # treatment
            # Strong gradient from humidifier
            # Near humidifier: low VPD (high humidity)
            # Far from humidifier: high VPD (low humidity)
            min_vpd = 0.55  # Near humidifier
            max_vpd = 1.05  # Far corner
            max_distance = self._distance_from_humidifier(112, 115)  # Far corner
            
            # Linear gradient with some spatial noise
            vpd = min_vpd + (max_vpd - min_vpd) * (distance / max_distance)
            noise = np.random.normal(0, 0.03)
            
            return np.clip(vpd + noise, 0.5, 1.1)
    
    def _calculate_temp_humidity(self, vpd: float) -> Tuple[float, float]:
        """
        Calculate temperature and humidity from VPD.
        
        Uses inverse VPD formula assuming reasonable greenhouse conditions.
        VPD = (1 - RH/100) × SVP(T)
        """
        # Assume temperature varies slightly (warmer near humidifier)
        temp = 23.0 + np.random.normal(0, 0.5)
        
        # Calculate SVP (saturation vapor pressure)
        svp = 0.6108 * np.exp((17.27 * temp) / (temp + 237.3))
        
        # Solve for RH from VPD
        # VPD = (1 - RH/100) × SVP
        # RH = 100 × (1 - VPD/SVP)
        humidity = 100 * (1 - vpd / svp)
        humidity = np.clip(humidity, 40, 85)
        
        return temp, humidity
    
    def generate_environmental_data(self) -> pd.DataFrame:
        """
        Generate environmental sensor data.
        
        Returns
        -------
        pd.DataFrame
            Columns: timestamp, plant_id, sensor_id, temperature, humidity, 
                     pressure, vpd, period
        """
        records = []
        
        # Generate data for each week
        for week in range(1, 7):  # Weeks 1-6
            period = 'baseline' if week <= self.baseline_weeks else 'treatment'
            week_date = self.start_date + timedelta(weeks=week-1)
            
            # Generate data for sensor-equipped plants only
            for plant_id in self.has_sensor:
                x, y = self.plant_positions[plant_id]
                
                # Generate VPD for this plant/week
                vpd = self._generate_vpd_gradient(x, y, period)
                temp, humidity = self._calculate_temp_humidity(vpd)
                
                # Pressure (relatively constant, slight daily variation)
                pressure = 1013.0 + np.random.normal(0, 2.0)
                
                records.append({
                    'timestamp': week_date,
                    'plant_id': plant_id,
                    'sensor_id': f'P{plant_id}_sensor',
                    'position_x': x,
                    'position_y': y,
                    'temperature': round(temp, 2),
                    'humidity': round(humidity, 1),
                    'pressure': round(pressure, 1),
                    'vpd_kpa': round(vpd, 3),
                    'period': period,
                    'week': week
                })
        
        return pd.DataFrame(records)
    
    def _growth_response_to_vpd(self, vpd: float) -> float:
        """
        Simulate plant growth response to VPD (quadratic relationship).
        
        Optimal VPD ~ 0.7 kPa (inverted U-shape)
        """
        optimal_vpd = 0.70
        max_growth = 1.0
        
        # Quadratic penalty for deviation from optimal
        penalty = 0.5 * ((vpd - optimal_vpd) / 0.3) ** 2
        growth_factor = max_growth * np.exp(-penalty)
        
        return growth_factor
    
    def generate_plant_measurements(self, env_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate weekly plant measurements.
        
        Parameters
        ----------
        env_data : pd.DataFrame
            Environmental data from generate_environmental_data()
            
        Returns
        -------
        pd.DataFrame
            Columns: plant_id, week, date, height_cm, leaf_count, color_score,
                     spad, biomass_g, growth_rate_cm_day, period, avg_vpd
        """
        records = []
        
        # Calculate average VPD per plant per period
        vpd_by_plant_period = {}
        for period in ['baseline', 'treatment']:
            period_data = env_data[env_data['period'] == period]
            for plant_id in range(16):
                x, y = self.plant_positions[plant_id]
                
                if plant_id in self.has_sensor:
                    # Use actual sensor data
                    plant_data = period_data[period_data['plant_id'] == plant_id]
                    avg_vpd = plant_data['vpd_kpa'].mean()
                else:
                    # Estimate VPD from position
                    sample_vpds = [self._generate_vpd_gradient(x, y, period) 
                                   for _ in range(10)]
                    avg_vpd = np.mean(sample_vpds)
                
                vpd_by_plant_period[(plant_id, period)] = avg_vpd
        
        # Generate growth trajectories
        for plant_id in range(16):
            x, y = self.plant_positions[plant_id]
            
            # Initial size variation (genetics)
            base_growth_rate = np.random.normal(0.9, 0.15)  # cm/day
            initial_height = np.random.normal(2.0, 0.3)
            
            # Generate weekly measurements
            current_height = initial_height
            
            for week in range(1, 7):
                period = 'baseline' if week <= self.baseline_weeks else 'treatment'
                week_date = self.start_date + timedelta(weeks=week-1)
                
                # Get VPD for this plant/period
                avg_vpd = vpd_by_plant_period[(plant_id, period)]
                
                # Growth rate influenced by VPD (stronger effect in treatment)
                vpd_effect = self._growth_response_to_vpd(avg_vpd)
                if period == 'treatment':
                    growth_rate = base_growth_rate * vpd_effect
                else:
                    # Baseline: minimal VPD effect (natural variation only)
                    growth_rate = base_growth_rate * np.random.normal(1.0, 0.1)
                
                # Update height (7 days of growth)
                height_gain = growth_rate * 7
                current_height += height_gain
                
                # Leaf count (increases over time, VPD influence)
                base_leaves = 2 + (week * 1.5)
                leaf_count = int(base_leaves * (0.8 + 0.4 * vpd_effect) + np.random.normal(0, 0.5))
                leaf_count = max(2, leaf_count)
                
                # Color score (1-5, better with optimal VPD)
                base_color = 3.5
                color_score = int(np.clip(base_color + (vpd_effect - 0.7) * 2, 1, 5))
                
                # SPAD (chlorophyll, ~35-45 for spinach)
                base_spad = 38
                spad = base_spad + (vpd_effect - 0.7) * 5 + np.random.normal(0, 2)
                spad = np.clip(spad, 30, 50)
                
                # Biomass (only measured at final week)
                if week == 6:
                    # Biomass scales with height and VPD effect
                    base_biomass = 15.0  # grams
                    biomass = base_biomass * (current_height / 18) * vpd_effect
                    biomass *= np.random.normal(1.0, 0.15)  # Individual variation
                else:
                    biomass = None
                
                records.append({
                    'plant_id': plant_id,
                    'week': week,
                    'date': week_date,
                    'height_cm': round(current_height, 1),
                    'leaf_count': leaf_count,
                    'color_score': color_score,
                    'spad': round(spad, 1),
                    'biomass_g': round(biomass, 2) if biomass else None,
                    'growth_rate_cm_day': round(growth_rate, 2),
                    'period': period,
                    'avg_vpd': round(avg_vpd, 3),
                    'position_x': x,
                    'position_y': y,
                    'has_sensor': plant_id in self.has_sensor
                })
        
        return pd.DataFrame(records)
    
    def generate_full_dataset(self) -> Dict[str, pd.DataFrame]:
        """
        Generate complete experimental dataset.
        
        Returns
        -------
        dict
            Keys: 'environmental', 'plant_measurements'
        """
        env_data = self.generate_environmental_data()
        plant_data = self.generate_plant_measurements(env_data)
        
        return {
            'environmental': env_data,
            'plant_measurements': plant_data
        }


def generate_sample_data(seed: int = 42) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to generate sample data.
    
    Parameters
    ----------
    seed : int
        Random seed for reproducibility
        
    Returns
    -------
    dict
        Dictionary with 'environmental' and 'plant_measurements' DataFrames
        
    Examples
    --------
    >>> data = generate_sample_data(seed=42)
    >>> env = data['environmental']
    >>> plants = data['plant_measurements']
    """
    generator = GreenhouseDataGenerator(seed=seed)
    return generator.generate_full_dataset()


if __name__ == "__main__":
    # Generate and save sample data
    print("Generating sample greenhouse data...")
    data = generate_sample_data(seed=42)
    
    env = data['environmental']
    plants = data['plant_measurements']
    
    print(f"\nEnvironmental data: {len(env)} records")
    print(env.head())
    
    print(f"\nPlant measurements: {len(plants)} records")
    print(plants[plants['week'] == 6][['plant_id', 'height_cm', 'biomass_g', 'avg_vpd']].head(10))
    
    # Save to CSV
    env.to_csv('sample_environmental_data.csv', index=False)
    plants.to_csv('sample_plant_data.csv', index=False)
    
    print("\nSample data saved to CSV files.")
