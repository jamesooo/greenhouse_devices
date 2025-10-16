"""
GreenhouseMapper - High-resolution spatial interpolation and visualization
for greenhouse environmental sensor data.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.interpolate import griddata, Rbf
from scipy.stats import linregress
from shapely.geometry import Point, Polygon
from typing import Dict, List, Tuple, Optional, Literal
import warnings


class GreenhouseMapper:
    """
    A class for mapping and visualizing greenhouse environmental data with
    high-resolution spatial interpolation.
    
    Attributes:
        width_cm (float): Width of greenhouse floor in cm
        height_cm (float): Height of greenhouse floor in cm
        resolution_cm (float): Grid resolution in cm
        sensors (gpd.GeoDataFrame): Sensor locations and current readings
    """
    
    def __init__(self, width_cm: float = 121.92, height_cm: float = 121.92, 
                 resolution_cm: float = 1.0):
        """
        Initialize the GreenhouseMapper.
        
        Args:
            width_cm: Width of greenhouse floor in cm (default: 4ft = 121.92cm)
            height_cm: Height of greenhouse floor in cm (default: 4ft = 121.92cm)
            resolution_cm: Grid resolution in cm (default: 1cm)
        """
        self.width_cm = width_cm
        self.height_cm = height_cm
        self.resolution_cm = resolution_cm
        
        # Create base grid
        self.x_grid, self.y_grid = self._create_grid()
        
        # Initialize sensor data
        self.sensors = None
        self.interpolated_data = {}
        self.statistics = {}
        
    def _create_grid(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a regular grid at the specified resolution.
        
        Returns:
            Tuple of (x_grid, y_grid) meshgrid arrays
        """
        x = np.arange(0, self.width_cm + self.resolution_cm, self.resolution_cm)
        y = np.arange(0, self.height_cm + self.resolution_cm, self.resolution_cm)
        return np.meshgrid(x, y)
    
    def set_sensor_data(self, sensor_data: List[Dict], 
                       sensor_positions: Optional[List[Tuple[float, float]]] = None):
        """
        Set sensor data with positions.
        
        Args:
            sensor_data: List of dicts with keys: temperature, humidity, pressure, resistance
            sensor_positions: List of (x, y) tuples in cm. If None, creates a grid layout.
        """
        if sensor_positions is None:
            # Automatically distribute sensors in a grid pattern
            sensor_positions = self._auto_position_sensors(len(sensor_data))
        
        if len(sensor_data) != len(sensor_positions):
            raise ValueError("Number of sensors must match number of positions")
        
        # Create GeoDataFrame
        data_records = []
        for i, (data, pos) in enumerate(zip(sensor_data, sensor_positions)):
            record = {
                'sensor_id': i,
                'x': pos[0],
                'y': pos[1],
                'temperature': data.get('temperature'),
                'humidity': data.get('humidity'),
                'pressure': data.get('pressure'),
                'resistance': data.get('resistance'),
                'geometry': Point(pos[0], pos[1])
            }
            data_records.append(record)
        
        self.sensors = gpd.GeoDataFrame(data_records, geometry='geometry')
        
    def _auto_position_sensors(self, num_sensors: int) -> List[Tuple[float, float]]:
        """
        Automatically position sensors in a roughly uniform grid.
        
        Args:
            num_sensors: Number of sensors to position
            
        Returns:
            List of (x, y) positions in cm
        """
        # Calculate grid dimensions
        cols = int(np.ceil(np.sqrt(num_sensors)))
        rows = int(np.ceil(num_sensors / cols))
        
        # Add margins (10cm from edges)
        margin = 10
        x_spacing = (self.width_cm - 2 * margin) / (cols - 1) if cols > 1 else 0
        y_spacing = (self.height_cm - 2 * margin) / (rows - 1) if rows > 1 else 0
        
        positions = []
        for i in range(num_sensors):
            row = i // cols
            col = i % cols
            x = margin + col * x_spacing
            y = margin + row * y_spacing
            positions.append((x, y))
        
        return positions
    
    def interpolate(self, parameter: str, 
                   method: Literal['linear', 'cubic', 'rbf'] = 'cubic') -> np.ndarray:
        """
        Interpolate sensor data across the greenhouse floor.
        
        Args:
            parameter: One of 'temperature', 'humidity', 'pressure', 'resistance'
            method: Interpolation method - 'linear', 'cubic', or 'rbf'
            
        Returns:
            2D array of interpolated values matching the grid
        """
        if self.sensors is None:
            raise ValueError("No sensor data loaded. Call set_sensor_data() first.")
        
        if parameter not in ['temperature', 'humidity', 'pressure', 'resistance']:
            raise ValueError(f"Invalid parameter: {parameter}")
        
        # Extract sensor positions and values
        points = np.column_stack([self.sensors['x'].values, self.sensors['y'].values])
        values = self.sensors[parameter].values
        
        # Remove any NaN values
        mask = ~np.isnan(values)
        points = points[mask]
        values = values[mask]
        
        if len(values) < 3:
            raise ValueError(f"Need at least 3 valid sensor readings for {parameter}")
        
        # Interpolate based on method
        if method == 'rbf':
            # Radial Basis Function interpolation
            rbf = Rbf(points[:, 0], points[:, 1], values, function='multiquadric', smooth=0.1)
            interpolated = rbf(self.x_grid, self.y_grid)
        else:
            # Grid-based interpolation (linear or cubic)
            interpolated = griddata(
                points, values, 
                (self.x_grid, self.y_grid), 
                method=method,
                fill_value=np.nan
            )
        
        # Store result
        self.interpolated_data[parameter] = interpolated
        
        # Calculate statistics
        self._calculate_statistics(parameter, points, values, interpolated)
        
        return interpolated
    
    def _calculate_statistics(self, parameter: str, points: np.ndarray, 
                              values: np.ndarray, interpolated: np.ndarray):
        """
        Calculate statistical metrics for the interpolation.
        
        Args:
            parameter: Parameter name
            points: Sensor positions (N x 2)
            values: Sensor values (N,)
            interpolated: Interpolated grid
        """
        # Calculate cross-validation R-squared using leave-one-out
        predictions = []
        actuals = []
        
        for i in range(len(points)):
            # Leave one out
            train_points = np.delete(points, i, axis=0)
            train_values = np.delete(values, i)
            test_point = points[i:i+1]
            test_value = values[i]
            
            # Interpolate without this point
            try:
                pred = griddata(train_points, train_values, test_point, method='cubic')
                if not np.isnan(pred[0]):
                    predictions.append(pred[0])
                    actuals.append(test_value)
            except:
                continue
        
        # Calculate R-squared
        if len(predictions) > 0:
            actuals = np.array(actuals)
            predictions = np.array(predictions)
            
            ss_res = np.sum((actuals - predictions) ** 2)
            ss_tot = np.sum((actuals - np.mean(actuals)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Calculate RMSE
            rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
        else:
            r_squared = np.nan
            rmse = np.nan
        
        # Store statistics
        self.statistics[parameter] = {
            'mean': np.nanmean(interpolated),
            'std': np.nanstd(interpolated),
            'min': np.nanmin(interpolated),
            'max': np.nanmax(interpolated),
            'range': np.nanmax(interpolated) - np.nanmin(interpolated),
            'sensor_mean': np.mean(values),
            'sensor_std': np.std(values),
            'r_squared': r_squared,
            'rmse': rmse,
            'num_sensors': len(values)
        }
    
    def plot_map(self, parameter: str, 
                 figsize: Tuple[float, float] = (12, 10),
                 cmap: str = 'viridis',
                 show_sensors: bool = True,
                 show_stats: bool = True,
                 title: Optional[str] = None,
                 save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot an interpolated heatmap of the specified parameter.
        
        Args:
            parameter: One of 'temperature', 'humidity', 'pressure', 'resistance'
            figsize: Figure size (width, height) in inches
            cmap: Matplotlib colormap name
            show_sensors: Whether to show sensor locations
            show_stats: Whether to display statistics on the plot
            title: Custom title (if None, auto-generated)
            save_path: Path to save figure (if None, not saved)
            
        Returns:
            Matplotlib Figure object
        """
        # Ensure data is interpolated
        if parameter not in self.interpolated_data:
            self.interpolate(parameter)
        
        data = self.interpolated_data[parameter]
        stats = self.statistics.get(parameter, {})
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot heatmap
        im = ax.contourf(self.x_grid, self.y_grid, data, 
                        levels=50, cmap=cmap, extend='both')
        
        # Add contour lines
        contours = ax.contour(self.x_grid, self.y_grid, data, 
                             levels=10, colors='black', alpha=0.3, linewidths=0.5)
        ax.clabel(contours, inline=True, fontsize=8, fmt='%.2f')
        
        # Plot sensor locations
        if show_sensors and self.sensors is not None:
            ax.scatter(self.sensors['x'], self.sensors['y'], 
                      c='red', s=100, marker='o', 
                      edgecolors='white', linewidths=2,
                      label='Sensors', zorder=5)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, pad=0.02)
        
        # Labels based on parameter
        units = {
            'temperature': '°C',
            'humidity': '% RH',
            'pressure': 'hPa',
            'resistance': 'Ω'
        }
        param_names = {
            'temperature': 'Temperature',
            'humidity': 'Relative Humidity',
            'pressure': 'Atmospheric Pressure',
            'resistance': 'Gas Resistance'
        }
        
        cbar.set_label(f"{param_names.get(parameter, parameter)} ({units.get(parameter, '')})", 
                      fontsize=12)
        
        # Axis labels
        ax.set_xlabel('X Position (cm)', fontsize=12)
        ax.set_ylabel('Y Position (cm)', fontsize=12)
        
        # Title
        if title is None:
            title = f"Greenhouse {param_names.get(parameter, parameter)} Map"
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Add statistics text box
        if show_stats and stats:
            stats_text = (
                f"Statistics:\n"
                f"Mean: {stats.get('mean', np.nan):.2f} {units.get(parameter, '')}\n"
                f"Std Dev: {stats.get('std', np.nan):.2f}\n"
                f"Range: {stats.get('range', np.nan):.2f}\n"
                f"R²: {stats.get('r_squared', np.nan):.4f}\n"
                f"RMSE: {stats.get('rmse', np.nan):.4f}\n"
                f"Sensors: {stats.get('num_sensors', 0)}"
            )
            ax.text(0.02, 0.98, stats_text, 
                   transform=ax.transAxes,
                   fontsize=10,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_aspect('equal')
        
        # Legend
        if show_sensors:
            ax.legend(loc='upper right')
        
        plt.tight_layout()
        
        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_all_parameters(self, 
                           figsize: Tuple[float, float] = (20, 16),
                           cmap: str = 'viridis',
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot all four parameters in a 2x2 grid.
        
        Args:
            figsize: Figure size (width, height) in inches
            cmap: Matplotlib colormap name
            save_path: Path to save figure (if None, not saved)
            
        Returns:
            Matplotlib Figure object
        """
        parameters = ['temperature', 'humidity', 'pressure', 'resistance']
        param_names = {
            'temperature': 'Temperature',
            'humidity': 'Relative Humidity',
            'pressure': 'Atmospheric Pressure',
            'resistance': 'Gas Resistance'
        }
        units = {
            'temperature': '°C',
            'humidity': '% RH',
            'pressure': 'hPa',
            'resistance': 'Ω'
        }
        
        # Ensure all are interpolated
        for param in parameters:
            if param not in self.interpolated_data:
                self.interpolate(param)
        
        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        axes = axes.flatten()
        
        for idx, param in enumerate(parameters):
            ax = axes[idx]
            data = self.interpolated_data[param]
            stats = self.statistics.get(param, {})
            
            # Plot heatmap
            im = ax.contourf(self.x_grid, self.y_grid, data, 
                           levels=50, cmap=cmap, extend='both')
            
            # Contours
            contours = ax.contour(self.x_grid, self.y_grid, data, 
                                levels=8, colors='black', alpha=0.3, linewidths=0.5)
            ax.clabel(contours, inline=True, fontsize=7, fmt='%.2f')
            
            # Sensors
            if self.sensors is not None:
                ax.scatter(self.sensors['x'], self.sensors['y'], 
                         c='red', s=80, marker='o', 
                         edgecolors='white', linewidths=1.5, zorder=5)
            
            # Colorbar
            cbar = plt.colorbar(im, ax=ax, pad=0.02)
            cbar.set_label(f"{units.get(param, '')}", fontsize=10)
            
            # Labels
            ax.set_xlabel('X Position (cm)', fontsize=10)
            ax.set_ylabel('Y Position (cm)', fontsize=10)
            ax.set_title(f"{param_names.get(param, param)}", 
                        fontsize=12, fontweight='bold')
            
            # Stats
            if stats:
                stats_text = (
                    f"μ={stats.get('mean', np.nan):.2f}, "
                    f"σ={stats.get('std', np.nan):.2f}\n"
                    f"R²={stats.get('r_squared', np.nan):.4f}, "
                    f"RMSE={stats.get('rmse', np.nan):.4f}"
                )
                ax.text(0.02, 0.98, stats_text, 
                       transform=ax.transAxes,
                       fontsize=8,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_aspect('equal')
        
        plt.suptitle('Greenhouse Environmental Mapping - All Parameters', 
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def get_statistics(self, parameter: Optional[str] = None) -> Dict:
        """
        Get statistics for one or all parameters.
        
        Args:
            parameter: Specific parameter, or None for all
            
        Returns:
            Dictionary of statistics
        """
        if parameter:
            return self.statistics.get(parameter, {})
        return self.statistics
    
    def export_interpolated_data(self, parameter: str, 
                                 filepath: str, 
                                 format: Literal['csv', 'geotiff'] = 'csv'):
        """
        Export interpolated data to file.
        
        Args:
            parameter: Parameter to export
            filepath: Output file path
            format: Export format ('csv' or 'geotiff')
        """
        if parameter not in self.interpolated_data:
            self.interpolate(parameter)
        
        data = self.interpolated_data[parameter]
        
        if format == 'csv':
            # Create DataFrame
            df = pd.DataFrame({
                'x': self.x_grid.flatten(),
                'y': self.y_grid.flatten(),
                parameter: data.flatten()
            })
            df.to_csv(filepath, index=False)
        elif format == 'geotiff':
            # Would require rasterio - placeholder for future implementation
            raise NotImplementedError("GeoTIFF export requires rasterio library")
        else:
            raise ValueError(f"Unsupported format: {format}")
