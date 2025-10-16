"""
Plant-aware extension of GreenhouseMapper for biomass and growth mapping.
Handles scenarios with mixed measured and unmeasured plants.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from greenhouse_mapper import GreenhouseMapper
from typing import Dict, List, Tuple, Optional


class PlantMapper(GreenhouseMapper):
    """
    Extension of GreenhouseMapper specifically for plant growth and biomass mapping.
    
    Supports scenarios with both measured plants (with sensors) and unmeasured plants
    (without sensors but with biomass measurements).
    """
    
    def __init__(self, width_cm: float = 121.92, height_cm: float = 121.92, 
                 resolution_cm: float = 1.0,
                 pot_width_cm: float = 15.0,
                 pot_height_cm: float = 16.0):
        """
        Initialize the PlantMapper.
        
        Args:
            width_cm: Width of the greenhouse area in cm
            height_cm: Height of the greenhouse area in cm
            resolution_cm: Resolution of the interpolation grid in cm
            pot_width_cm: Width of each pot in cm (default: 15.0 cm = 5.9")
            pot_height_cm: Height of each pot in cm (default: 16.0 cm = 6.3")
        """
        super().__init__(width_cm, height_cm, resolution_cm)
        self.plants = None
        self.measured_plants = None
        self.unmeasured_plants = None
        self.pot_width_cm = pot_width_cm
        self.pot_height_cm = pot_height_cm
        
    def set_plant_data(self, 
                      plant_data: List[Dict],
                      plant_positions: List[Tuple[float, float]],
                      has_sensor: Optional[List[bool]] = None):
        """
        Set plant data including biomass and sensor information.
        
        Args:
            plant_data: List of dicts with keys like: biomass_g, temperature (if sensor), etc.
            plant_positions: List of (x, y) tuples in cm for each plant
            has_sensor: List of booleans indicating which plants have sensors
        """
        if len(plant_data) != len(plant_positions):
            raise ValueError("Number of plants must match number of positions")
        
        # If has_sensor not provided, assume plants with full data have sensors
        if has_sensor is None:
            has_sensor = [
                all(key in data for key in ['temperature', 'humidity', 'pressure', 'resistance'])
                for data in plant_data
            ]
        
        # Create plant GeoDataFrame
        plant_records = []
        sensor_records = []
        
        for i, (data, pos, has_sens) in enumerate(zip(plant_data, plant_positions, has_sensor)):
            from shapely.geometry import Point
            
            record = {
                'plant_id': i,
                'x': pos[0],
                'y': pos[1],
                'has_sensor': has_sens,
                'biomass_g': data.get('biomass_g'),
                'height_cm': data.get('height_cm'),
                'leaf_area_cm2': data.get('leaf_area_cm2'),
                'geometry': Point(pos[0], pos[1])
            }
            
            # Add sensor data if available
            if has_sens:
                record.update({
                    'temperature': data.get('temperature'),
                    'humidity': data.get('humidity'),
                    'pressure': data.get('pressure'),
                    'resistance': data.get('resistance')
                })
                sensor_records.append(record.copy())
            
            plant_records.append(record)
        
        self.plants = gpd.GeoDataFrame(plant_records, geometry='geometry')
        self.measured_plants = self.plants[self.plants['has_sensor'] == True].copy()
        self.unmeasured_plants = self.plants[self.plants['has_sensor'] == False].copy()
        
        # Set sensor data for environmental parameters
        if len(sensor_records) > 0:
            self.sensors = gpd.GeoDataFrame(sensor_records, geometry='geometry')
        
        print(f"Loaded {len(self.plants)} plants:")
        print(f"  - {len(self.measured_plants)} with sensors")
        print(f"  - {len(self.unmeasured_plants)} without sensors")
    
    def interpolate_biomass(self, method: str = 'cubic') -> np.ndarray:
        """
        Interpolate biomass across the greenhouse floor.
        
        Args:
            method: Interpolation method - 'linear', 'cubic', or 'rbf'
            
        Returns:
            2D array of interpolated biomass values
        """
        if self.plants is None:
            raise ValueError("No plant data loaded. Call set_plant_data() first.")
        
        # Get biomass data from all plants (both measured and unmeasured)
        points = np.column_stack([self.plants['x'].values, self.plants['y'].values])
        values = self.plants['biomass_g'].values
        
        # Remove any NaN values
        mask = ~np.isnan(values)
        points = points[mask]
        values = values[mask]
        
        if len(values) < 3:
            raise ValueError("Need at least 3 plants with biomass measurements")
        
        # Use parent class interpolation logic
        from scipy.interpolate import griddata, Rbf
        
        if method == 'rbf':
            rbf = Rbf(points[:, 0], points[:, 1], values, function='multiquadric', smooth=0.1)
            interpolated = rbf(self.x_grid, self.y_grid)
        else:
            interpolated = griddata(
                points, values,
                (self.x_grid, self.y_grid),
                method=method,
                fill_value=np.nan
            )
        
        # Store result
        self.interpolated_data['biomass_g'] = interpolated
        
        # Calculate statistics
        self._calculate_statistics('biomass_g', points, values, interpolated)
        
        return interpolated
    
    def plot_plant_map(self, 
                      parameter: str = 'biomass_g',
                      figsize: Tuple[float, float] = (14, 12),
                      cmap: str = 'YlGn',
                      show_plants: bool = True,
                      show_stats: bool = True,
                      title: Optional[str] = None,
                      save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot an interpolated map with plant locations clearly marked.
        
        Args:
            parameter: Parameter to plot ('biomass_g' or environmental parameters)
            figsize: Figure size
            cmap: Colormap
            show_plants: Whether to show plant locations
            show_stats: Whether to show statistics
            title: Custom title
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure object
        """
        # Interpolate if needed
        if parameter == 'biomass_g':
            if parameter not in self.interpolated_data:
                self.interpolate_biomass()
        else:
            if parameter not in self.interpolated_data:
                self.interpolate(parameter)
        
        data = self.interpolated_data[parameter]
        stats = self.statistics.get(parameter, {})
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot heatmap
        im = ax.contourf(self.x_grid, self.y_grid, data,
                        levels=50, cmap=cmap, extend='both', alpha=0.8)
        
        # Add contour lines
        contours = ax.contour(self.x_grid, self.y_grid, data,
                             levels=10, colors='black', alpha=0.3, linewidths=0.5)
        ax.clabel(contours, inline=True, fontsize=8, fmt='%.1f')
        
        # Plot plant locations
        if show_plants and self.plants is not None:
            # Measured plants (with sensors) - filled rectangles
            if len(self.measured_plants) > 0:
                for idx, row in self.measured_plants.iterrows():
                    # Rectangle is drawn from lower-left corner, so we offset by half width/height
                    rect = Rectangle(
                        (row['x'] - self.pot_width_cm / 2, row['y'] - self.pot_height_cm / 2),
                        self.pot_width_cm, self.pot_height_cm,
                        facecolor='darkgreen', edgecolor='white',
                        linewidth=2.5, alpha=0.9, zorder=5
                    )
                    ax.add_patch(rect)
                    
                    # Add plant IDs for measured plants
                    ax.annotate(f"P{int(row['plant_id'])}",
                               (row['x'], row['y']),
                               color='white',
                               fontsize=9,
                               fontweight='bold',
                               ha='center',
                               va='center',
                               zorder=6)
                
                # Add legend entry (create a dummy rectangle for legend)
                ax.scatter([], [], c='darkgreen', s=250, marker='s',
                          edgecolors='white', linewidths=2.5,
                          label='Plants with Sensors', alpha=0.9)
            
            # Unmeasured plants - hollow rectangles
            if len(self.unmeasured_plants) > 0:
                for idx, row in self.unmeasured_plants.iterrows():
                    rect = Rectangle(
                        (row['x'] - self.pot_width_cm / 2, row['y'] - self.pot_height_cm / 2),
                        self.pot_width_cm, self.pot_height_cm,
                        facecolor='none', edgecolor='darkgreen',
                        linewidth=2, alpha=0.7, zorder=5
                    )
                    ax.add_patch(rect)
                    
                    # Add plant IDs for unmeasured plants
                    ax.annotate(f"P{int(row['plant_id'])}",
                               (row['x'], row['y']),
                               color='darkgreen',
                               fontsize=8,
                               ha='center',
                               va='center',
                               zorder=6)
                
                # Add legend entry (create a dummy rectangle for legend)
                ax.scatter([], [], c='none', s=150, marker='s',
                          edgecolors='darkgreen', linewidths=2,
                          label='Plants without Sensors', alpha=0.7)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, pad=0.02)
        
        # Labels
        units = {
            'temperature': '°C',
            'humidity': '% RH',
            'pressure': 'hPa',
            'resistance': 'Ω',
            'biomass_g': 'g',
            'height_cm': 'cm',
            'leaf_area_cm2': 'cm²'
        }
        param_names = {
            'temperature': 'Temperature',
            'humidity': 'Relative Humidity',
            'pressure': 'Atmospheric Pressure',
            'resistance': 'Gas Resistance',
            'biomass_g': 'Fresh Biomass',
            'height_cm': 'Plant Height',
            'leaf_area_cm2': 'Leaf Area'
        }
        
        cbar.set_label(f"{param_names.get(parameter, parameter)} ({units.get(parameter, '')})",
                      fontsize=12)
        
        # Axis labels
        ax.set_xlabel('X Position (cm)', fontsize=12)
        ax.set_ylabel('Y Position (cm)', fontsize=12)
        
        # Title
        if title is None:
            title = f"Greenhouse {param_names.get(parameter, parameter)} Distribution"
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Statistics box
        if show_stats and stats:
            stats_text = (
                f"Statistics:\n"
                f"Mean: {stats.get('mean', np.nan):.2f} {units.get(parameter, '')}\n"
                f"Std Dev: {stats.get('std', np.nan):.2f}\n"
                f"Range: {stats.get('range', np.nan):.2f}\n"
                f"R²: {stats.get('r_squared', np.nan):.4f}\n"
                f"RMSE: {stats.get('rmse', np.nan):.4f}\n"
            )
            
            if self.plants is not None:
                stats_text += (
                    f"\nPlants:\n"
                    f"Total: {len(self.plants)}\n"
                    f"With sensors: {len(self.measured_plants)}\n"
                    f"Without: {len(self.unmeasured_plants)}"
                )
            
            ax.text(0.02, 0.98, stats_text,
                   transform=ax.transAxes,
                   fontsize=9,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))
        
        # Grid and legend
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_aspect('equal')
        
        if show_plants:
            ax.legend(loc='upper right', fontsize=10)
        
        plt.tight_layout()
        
        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_plant_comparison(self,
                             figsize: Tuple[float, float] = (20, 10),
                             save_path: Optional[str] = None) -> plt.Figure:
        """
        Create a comparison plot showing biomass distribution and environmental conditions.
        
        Returns:
            Matplotlib Figure object
        """
        # Ensure biomass is interpolated
        if 'biomass_g' not in self.interpolated_data:
            self.interpolate_biomass()
        
        # Check if we have environmental data
        has_env_data = self.sensors is not None and len(self.sensors) > 0
        
        if has_env_data:
            # 2x2 grid: biomass + temp, humidity, pressure
            fig, axes = plt.subplots(2, 2, figsize=figsize)
            axes = axes.flatten()
            
            parameters = ['biomass_g', 'temperature', 'humidity', 'pressure']
            cmaps = ['YlGn', 'RdYlBu_r', 'YlGnBu', 'viridis']
        else:
            # Just biomass
            fig, axes = plt.subplots(1, 1, figsize=(14, 12))
            axes = [axes]
            parameters = ['biomass_g']
            cmaps = ['YlGn']
        
        for ax, param, cmap in zip(axes, parameters, cmaps):
            # Interpolate if needed
            if param == 'biomass_g':
                if param not in self.interpolated_data:
                    self.interpolate_biomass()
            else:
                if param not in self.interpolated_data:
                    self.interpolate(param)
            
            data = self.interpolated_data[param]
            
            # Plot heatmap
            im = ax.contourf(self.x_grid, self.y_grid, data,
                           levels=50, cmap=cmap, extend='both', alpha=0.8)
            
            # Contours
            contours = ax.contour(self.x_grid, self.y_grid, data,
                                levels=8, colors='black', alpha=0.3, linewidths=0.5)
            ax.clabel(contours, inline=True, fontsize=7, fmt='%.1f')
            
            # Plants - use rectangles
            if len(self.measured_plants) > 0:
                for idx, row in self.measured_plants.iterrows():
                    rect = Rectangle(
                        (row['x'] - self.pot_width_cm / 2, row['y'] - self.pot_height_cm / 2),
                        self.pot_width_cm, self.pot_height_cm,
                        facecolor='darkgreen', edgecolor='white',
                        linewidth=2, alpha=0.9, zorder=5
                    )
                    ax.add_patch(rect)
            
            if len(self.unmeasured_plants) > 0:
                for idx, row in self.unmeasured_plants.iterrows():
                    rect = Rectangle(
                        (row['x'] - self.pot_width_cm / 2, row['y'] - self.pot_height_cm / 2),
                        self.pot_width_cm, self.pot_height_cm,
                        facecolor='none', edgecolor='darkgreen',
                        linewidth=1.5, alpha=0.7, zorder=5
                    )
                    ax.add_patch(rect)
            
            # Colorbar
            cbar = plt.colorbar(im, ax=ax, pad=0.02)
            
            units = {
                'temperature': '°C',
                'humidity': '% RH',
                'pressure': 'hPa',
                'biomass_g': 'g'
            }
            cbar.set_label(units.get(param, ''), fontsize=10)
            
            # Labels
            param_names = {
                'temperature': 'Temperature',
                'humidity': 'Relative Humidity',
                'pressure': 'Atmospheric Pressure',
                'biomass_g': 'Fresh Biomass'
            }
            
            ax.set_xlabel('X (cm)', fontsize=10)
            ax.set_ylabel('Y (cm)', fontsize=10)
            ax.set_title(param_names.get(param, param), fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
        
        plt.suptitle(f'Greenhouse Analysis - {len(self.plants)} Plants '
                    f'({len(self.measured_plants)} measured)',
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def get_plant_summary(self) -> pd.DataFrame:
        """
        Get a summary DataFrame of all plants.
        
        Returns:
            DataFrame with plant information
        """
        if self.plants is None:
            return pd.DataFrame()
        
        summary = self.plants.copy()
        summary = summary.drop(columns=['geometry'])
        return summary.sort_values('plant_id')
