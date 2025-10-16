"""
Statistical Visualization Functions for Greenhouse Analysis

Implements all visualization components from STATISTICAL_ANALYSIS_PLAN.md:
- Biomass vs VPD scatter plots with quadratic fits
- Spatial heatmaps (temperature, humidity, VPD, biomass)
- Before-after comparisons (baseline vs treatment)
- Moran's I spatial autocorrelation plots
- Model diagnostic plots
- Publication-quality formatting

All functions designed for the experimental protocol in docs/protocol.md
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
from scipy.interpolate import griddata
from scipy.stats import linregress
from typing import Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')


# Set publication-quality defaults
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16


def plot_biomass_vs_vpd(
    df: pd.DataFrame,
    vpd_col: str = 'avg_vpd',
    biomass_col: str = 'biomass_g',
    ax: Optional[plt.Axes] = None,
    show_optimal_range: bool = True,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot biomass vs VPD with quadratic fit (Figure 2 from analysis plan).
    
    Parameters
    ----------
    df : pd.DataFrame
        Plant data with VPD and biomass columns
    vpd_col : str
        Column name for VPD values (kPa)
    biomass_col : str
        Column name for biomass values (g)
    ax : plt.Axes, optional
        Matplotlib axes to plot on
    show_optimal_range : bool
        Whether to shade optimal VPD range (0.6-0.8 kPa)
    save_path : str, optional
        Path to save figure
        
    Returns
    -------
    plt.Figure
        Matplotlib figure object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))
    else:
        fig = ax.get_figure()
    
    # Filter to final week data only (where biomass is measured)
    plot_data = df[df[biomass_col].notna()].copy()
    
    # Scatter plot
    ax.scatter(
        plot_data[vpd_col],
        plot_data[biomass_col],
        s=150,
        alpha=0.7,
        color='darkgreen',
        edgecolor='black',
        linewidth=1.5,
        zorder=3
    )
    
    # Fit quadratic model
    vpd = plot_data[vpd_col].values
    biomass = plot_data[biomass_col].values
    
    # Quadratic fit: y = a*x^2 + b*x + c
    coeffs = np.polyfit(vpd, biomass, 2)
    vpd_range = np.linspace(vpd.min(), vpd.max(), 100)
    biomass_pred = np.polyval(coeffs, vpd_range)
    
    ax.plot(vpd_range, biomass_pred, 'r-', linewidth=3, label='Quadratic Fit', zorder=2)
    
    # Calculate R² for the fit
    biomass_fit = np.polyval(coeffs, vpd)
    ss_res = np.sum((biomass - biomass_fit)**2)
    ss_tot = np.sum((biomass - np.mean(biomass))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Find optimal VPD (vertex of parabola)
    a, b, c = coeffs
    if a < 0:  # Inverted parabola (expected)
        optimal_vpd = -b / (2 * a)
        ax.axvline(optimal_vpd, color='blue', linestyle='--', linewidth=2,
                   label=f'Optimal VPD: {optimal_vpd:.2f} kPa', zorder=2)
    
    # Shade optimal range from literature
    if show_optimal_range:
        ax.axvspan(0.6, 0.8, alpha=0.15, color='lightblue',
                   label='Literature Optimal (0.6-0.8 kPa)', zorder=1)
    
    # Labels and formatting
    ax.set_xlabel('Vapor Pressure Deficit (kPa)', fontweight='bold')
    ax.set_ylabel('Final Fresh Biomass (g)', fontweight='bold')
    ax.set_title('Effect of VPD on Spinach Biomass', fontweight='bold', pad=15)
    
    # Add statistics text box
    textstr = '\n'.join([
        f'R² = {r_squared:.3f}',
        f'N = {len(plot_data)} plants',
        f'Quadratic model',
        f'a = {a:.2f}, b = {b:.2f}'
    ])
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_spatial_heatmap(
    plant_positions: List[Tuple[float, float]],
    values: np.ndarray,
    parameter_name: str,
    has_sensor: Optional[List[bool]] = None,
    greenhouse_size: Tuple[float, float] = (121.92, 121.92),
    pot_size: Tuple[float, float] = (15.0, 16.0),
    cmap: str = 'YlOrRd',
    ax: Optional[plt.Axes] = None,
    save_path: Optional[str] = None,
    humidifier_pos: Optional[Tuple[float, float]] = (18, 18)
) -> plt.Figure:
    """
    Plot spatial heatmap of environmental or plant data.
    
    Parameters
    ----------
    plant_positions : list of tuples
        (x, y) coordinates for each plant (cm)
    values : np.ndarray
        Values to plot (e.g., VPD, biomass, temperature)
    parameter_name : str
        Name of parameter for colorbar label
    has_sensor : list of bool, optional
        Which plants have sensors (for styling)
    greenhouse_size : tuple
        (width, height) of greenhouse in cm
    pot_size : tuple
        (width, height) of pots in cm
    cmap : str
        Matplotlib colormap name
    ax : plt.Axes, optional
        Axes to plot on
    save_path : str, optional
        Path to save figure
    humidifier_pos : tuple, optional
        (x, y) position of humidifier to mark on plot
        
    Returns
    -------
    plt.Figure
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 10))
    else:
        fig = ax.get_figure()
    
    width_cm, height_cm = greenhouse_size
    pot_width, pot_height = pot_size
    
    # Create interpolation grid
    resolution = 1  # 1cm resolution
    grid_x, grid_y = np.mgrid[0:width_cm:resolution, 0:height_cm:resolution]
    
    # Interpolate values
    grid_values = griddata(
        plant_positions,
        values,
        (grid_x, grid_y),
        method='linear'
    )
    
    # Plot heatmap
    im = ax.imshow(
        grid_values.T,
        extent=[0, width_cm, 0, height_cm],
        origin='lower',
        cmap=cmap,
        alpha=0.7,
        aspect='equal'
    )
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(parameter_name, fontweight='bold')
    
    # Plot plant pots as rectangles
    if has_sensor is None:
        has_sensor = [False] * len(plant_positions)
    
    for (x, y), has_sens, val in zip(plant_positions, has_sensor, values):
        rect_x = x - pot_width / 2
        rect_y = y - pot_height / 2
        
        if has_sens:
            # Filled green rectangle with white border for sensors
            rect = Rectangle(
                (rect_x, rect_y), pot_width, pot_height,
                facecolor='green', edgecolor='white',
                linewidth=2, alpha=0.7, zorder=3
            )
            # Add star marker for sensor
            ax.plot(x, y, '*', color='yellow', markersize=15,
                   markeredgecolor='black', markeredgewidth=1, zorder=4)
        else:
            # Hollow rectangle for non-sensor plants
            rect = Rectangle(
                (rect_x, rect_y), pot_width, pot_height,
                facecolor='none', edgecolor='darkgreen',
                linewidth=2, alpha=0.8, zorder=3
            )
        
        ax.add_patch(rect)
        
        # Add value label
        ax.text(x, y, f'{val:.2f}', ha='center', va='center',
               fontsize=8, fontweight='bold', color='black',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7),
               zorder=5)
    
    # Mark humidifier position with rectangle (15cm × 20cm)
    if humidifier_pos:
        hx, hy = humidifier_pos
        humidifier_width = 15  # cm
        humidifier_height = 20  # cm
        humidifier_rect = Rectangle(
            (hx - humidifier_width / 2, hy - humidifier_height / 2),
            humidifier_width, humidifier_height,
            facecolor='cyan', edgecolor='blue',
            linewidth=3, alpha=0.5, zorder=4
        )
        ax.add_patch(humidifier_rect)
        ax.text(hx, hy, '💨', ha='center', va='center', fontsize=24, zorder=5)
        ax.text(hx, hy - 12, 'Humidifier', ha='center', fontsize=9,
               fontweight='bold', color='blue', zorder=5)
    
    # Formatting
    ax.set_xlabel('X Position (cm)', fontweight='bold')
    ax.set_ylabel('Y Position (cm)', fontweight='bold')
    ax.set_title(f'Spatial Distribution: {parameter_name}', fontweight='bold', pad=15)
    ax.set_xlim(0, width_cm)
    ax.set_ylim(0, height_cm)
    ax.grid(True, alpha=0.2, linestyle='--')
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', edgecolor='white', label='Sensor Plant'),
        Patch(facecolor='none', edgecolor='darkgreen', label='Non-Sensor Plant')
    ]
    if humidifier_pos:
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='w',
                                         markerfacecolor='cyan', markersize=10,
                                         markeredgecolor='blue', markeredgewidth=2,
                                         label='Humidifier'))
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_baseline_vs_treatment(
    df: pd.DataFrame,
    metric: str = 'growth_rate_cm_day',
    vpd_col: str = 'avg_vpd',
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot before-after comparison (baseline vs treatment periods).
    
    Parameters
    ----------
    df : pd.DataFrame
        Plant measurements with 'period' column
    metric : str
        Column name for metric to compare
    vpd_col : str
        Column name for VPD values
    save_path : str, optional
        Path to save figure
        
    Returns
    -------
    plt.Figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left plot: Boxplot comparison
    # Aggregate by plant and period
    period_data = df.groupby(['plant_id', 'period'])[metric].mean().reset_index()
    
    sns.boxplot(
        data=period_data,
        x='period',
        y=metric,
        order=['baseline', 'treatment'],
        palette=['lightblue', 'lightcoral'],
        ax=axes[0]
    )
    
    # Add individual points
    sns.stripplot(
        data=period_data,
        x='period',
        y=metric,
        order=['baseline', 'treatment'],
        color='black',
        alpha=0.5,
        size=6,
        ax=axes[0]
    )
    
    axes[0].set_xlabel('Period', fontweight='bold')
    axes[0].set_ylabel(metric.replace('_', ' ').title(), fontweight='bold')
    axes[0].set_title('Metric Comparison: Baseline vs Treatment', fontweight='bold')
    axes[0].grid(True, alpha=0.3, axis='y')
    
    # Right plot: Change vs VPD
    # Calculate change for each plant
    baseline_vals = df[df['period'] == 'baseline'].groupby('plant_id')[metric].mean()
    treatment_vals = df[df['period'] == 'treatment'].groupby('plant_id')[metric].mean()
    treatment_vpd = df[df['period'] == 'treatment'].groupby('plant_id')[vpd_col].mean()
    
    changes = (treatment_vals - baseline_vals).dropna()
    vpd_values = treatment_vpd[changes.index]
    
    axes[1].scatter(vpd_values, changes, s=100, alpha=0.7, color='purple', edgecolor='black')
    axes[1].axhline(0, color='black', linestyle='--', alpha=0.5, linewidth=1)
    
    # Add regression line
    if len(vpd_values) > 2:
        slope, intercept, r, p, se = linregress(vpd_values, changes)
        x_line = np.linspace(vpd_values.min(), vpd_values.max(), 100)
        y_line = slope * x_line + intercept
        axes[1].plot(x_line, y_line, 'r-', linewidth=2,
                    label=f'r = {r:.2f}, p = {p:.3f}')
        axes[1].legend(loc='best')
    
    axes[1].set_xlabel('VPD During Treatment (kPa)', fontweight='bold')
    axes[1].set_ylabel(f'Δ {metric.replace("_", " ").title()}', fontweight='bold')
    axes[1].set_title('Metric Change vs VPD', fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_morans_i_scatter(
    values: np.ndarray,
    positions: List[Tuple[float, float]],
    distance_threshold: float = 30.0,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, float]:
    """
    Plot Moran's I spatial autocorrelation scatter plot.
    
    Parameters
    ----------
    values : np.ndarray
        Values to test for spatial autocorrelation (e.g., biomass)
    positions : list of tuples
        (x, y) coordinates
    distance_threshold : float
        Distance threshold for defining neighbors (cm)
    save_path : str, optional
        Path to save figure
        
    Returns
    -------
    tuple
        (fig, morans_i) - Figure and Moran's I statistic
    """
    from scipy.spatial import distance_matrix
    
    # Standardize values
    values_std = (values - np.mean(values)) / np.std(values)
    
    # Create distance matrix
    coords = np.array(positions)
    dist_mat = distance_matrix(coords, coords)
    
    # Create spatial weights (binary: 1 if within threshold, 0 otherwise)
    W = (dist_mat > 0) & (dist_mat <= distance_threshold)
    W = W.astype(float)
    
    # Row-standardize
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # Avoid division by zero
    W = W / row_sums
    
    # Calculate spatial lag (weighted average of neighbors)
    lag = W @ values_std
    
    # Calculate Moran's I
    n = len(values_std)
    morans_i = (values_std @ lag) / n
    
    # Create scatter plot
    fig, ax = plt.subplots(figsize=(8, 8))
    
    ax.scatter(values_std, lag, s=100, alpha=0.7, color='steelblue',
              edgecolor='black', linewidth=1)
    
    # Add regression line
    if len(values_std) > 2:
        slope, intercept, r, p, se = linregress(values_std, lag)
        x_line = np.linspace(values_std.min(), values_std.max(), 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, 'r-', linewidth=2)
    
    # Add quadrant lines
    ax.axhline(0, color='black', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(0, color='black', linestyle='--', alpha=0.5, linewidth=1)
    
    # Labels
    ax.set_xlabel('Standardized Values', fontweight='bold')
    ax.set_ylabel('Spatial Lag (Neighbors\' Average)', fontweight='bold')
    ax.set_title(f"Moran's I Spatial Autocorrelation\nI = {morans_i:.3f}",
                fontweight='bold', pad=15)
    
    # Interpretation text
    if morans_i > 0.3:
        interp = "Strong positive autocorrelation\n(nearby plants similar)"
    elif morans_i > 0:
        interp = "Weak positive autocorrelation"
    elif morans_i > -0.3:
        interp = "Weak negative autocorrelation"
    else:
        interp = "Strong negative autocorrelation\n(nearby plants dissimilar)"
    
    ax.text(0.05, 0.95, interp, transform=ax.transAxes, fontsize=11,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig, morans_i


def plot_model_diagnostics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    residuals: Optional[np.ndarray] = None,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot model diagnostic plots (residuals, Q-Q plot, etc.).
    
    Parameters
    ----------
    y_true : np.ndarray
        True values
    y_pred : np.ndarray
        Predicted values
    residuals : np.ndarray, optional
        Residuals (if None, calculated as y_true - y_pred)
    save_path : str, optional
        Path to save figure
        
    Returns
    -------
    plt.Figure
    """
    from scipy import stats
    
    if residuals is None:
        residuals = y_true - y_pred
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Q-Q plot (normality)
    stats.probplot(residuals, dist="norm", plot=axes[0, 0])
    axes[0, 0].set_title("Q-Q Plot: Normality of Residuals", fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Residuals vs Fitted (homoscedasticity)
    axes[0, 1].scatter(y_pred, residuals, alpha=0.6, s=60, edgecolor='black')
    axes[0, 1].axhline(y=0, color='red', linestyle='--', linewidth=2)
    axes[0, 1].set_xlabel("Fitted Values", fontweight='bold')
    axes[0, 1].set_ylabel("Residuals", fontweight='bold')
    axes[0, 1].set_title("Residuals vs Fitted Values", fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Scale-location plot
    sqrt_abs_resid = np.sqrt(np.abs(residuals))
    axes[1, 0].scatter(y_pred, sqrt_abs_resid, alpha=0.6, s=60, edgecolor='black')
    axes[1, 0].set_xlabel("Fitted Values", fontweight='bold')
    axes[1, 0].set_ylabel("√|Residuals|", fontweight='bold')
    axes[1, 0].set_title("Scale-Location Plot", fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Histogram of residuals
    axes[1, 1].hist(residuals, bins=10, edgecolor='black', alpha=0.7)
    axes[1, 1].axvline(0, color='red', linestyle='--', linewidth=2)
    axes[1, 1].set_xlabel("Residuals", fontweight='bold')
    axes[1, 1].set_ylabel("Frequency", fontweight='bold')
    axes[1, 1].set_title("Histogram of Residuals", fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    # Add Shapiro-Wilk test result
    stat, p = stats.shapiro(residuals)
    textstr = f'Shapiro-Wilk test:\nW = {stat:.4f}\np = {p:.4f}'
    if p > 0.05:
        textstr += '\n✓ Normal (p > 0.05)'
    else:
        textstr += '\n✗ Non-normal (p ≤ 0.05)'
    
    axes[1, 1].text(0.95, 0.95, textstr, transform=axes[1, 1].transAxes,
                   fontsize=9, verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def create_summary_figure(
    plant_data: pd.DataFrame,
    env_data: pd.DataFrame,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Create comprehensive summary figure with multiple panels.
    
    Parameters
    ----------
    plant_data : pd.DataFrame
        Plant measurements
    env_data : pd.DataFrame
        Environmental data
    save_path : str, optional
        Path to save figure
        
    Returns
    -------
    plt.Figure
    """
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # Panel 1: VPD spatial distribution (treatment period)
    ax1 = fig.add_subplot(gs[0, 0])
    treatment_env = env_data[env_data['period'] == 'treatment']
    # Group by position first, then extract positions and values
    vpd_grouped = treatment_env.groupby(['position_x', 'position_y'])['vpd_kpa'].mean().reset_index()
    sensor_positions = list(zip(vpd_grouped['position_x'], vpd_grouped['position_y']))
    vpd_values = vpd_grouped['vpd_kpa'].values
    
    if len(vpd_values) > 0:
        plot_spatial_heatmap(
            sensor_positions,
            vpd_values,
            'VPD (kPa)',
            cmap='RdYlBu_r',
            ax=ax1,
            humidifier_pos=(18, 18)
        )
    
    # Panel 2: Biomass vs VPD
    ax2 = fig.add_subplot(gs[0, 1])
    final_data = plant_data[plant_data['week'] == 6].copy()
    plot_biomass_vs_vpd(final_data, ax=ax2, show_optimal_range=True)
    
    # Panel 3: Baseline vs Treatment comparison (Height)
    ax3 = fig.add_subplot(gs[1, 0])
    period_data = plant_data.groupby(['plant_id', 'period'])['height_cm'].mean().reset_index()
    import seaborn as sns
    sns.boxplot(
        data=period_data,
        x='period',
        y='height_cm',
        order=['baseline', 'treatment'],
        palette=['lightblue', 'lightcoral'],
        ax=ax3
    )
    ax3.set_xlabel('Period', fontweight='bold')
    ax3.set_ylabel('Height (cm)', fontweight='bold')
    ax3.set_title('Height: Baseline vs Treatment', fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Baseline vs Treatment comparison (SPAD)
    ax4 = fig.add_subplot(gs[1, 1])
    spad_data = plant_data.groupby(['plant_id', 'period'])['spad'].mean().reset_index()
    sns.boxplot(
        data=spad_data,
        x='period',
        y='spad',
        order=['baseline', 'treatment'],
        palette=['lightblue', 'lightcoral'],
        ax=ax4
    )
    ax4.set_xlabel('Period', fontweight='bold')
    ax4.set_ylabel('SPAD', fontweight='bold')
    ax4.set_title('SPAD: Baseline vs Treatment', fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Panel 5: Time series - height over weeks
    ax5 = fig.add_subplot(gs[2, 0])
    for plant_id in plant_data['plant_id'].unique()[:5]:  # Show 5 plants
        plant_series = plant_data[plant_data['plant_id'] == plant_id].sort_values('week')
        ax5.plot(plant_series['week'], plant_series['height_cm'],
                marker='o', label=f'Plant {plant_id}', alpha=0.7, linewidth=2)
    ax5.axvline(2.5, color='red', linestyle='--', linewidth=2, label='Treatment Start')
    ax5.set_xlabel('Week', fontweight='bold')
    ax5.set_ylabel('Height (cm)', fontweight='bold')
    ax5.set_title('Plant Growth Over Time (Sample)', fontweight='bold')
    ax5.legend(loc='upper left', fontsize=8)
    ax5.grid(True, alpha=0.3)
    
    # Panel 6: VPD distribution by period
    ax6 = fig.add_subplot(gs[2, 1])
    baseline_vpd = env_data[env_data['period'] == 'baseline']['vpd_kpa']
    treatment_vpd = env_data[env_data['period'] == 'treatment']['vpd_kpa']
    ax6.hist(baseline_vpd, bins=15, alpha=0.6, label='Baseline', color='lightblue', edgecolor='black')
    ax6.hist(treatment_vpd, bins=15, alpha=0.6, label='Treatment', color='lightcoral', edgecolor='black')
    ax6.set_xlabel('VPD (kPa)', fontweight='bold')
    ax6.set_ylabel('Frequency', fontweight='bold')
    ax6.set_title('VPD Distribution by Period', fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3, axis='y')
    
    fig.suptitle('Greenhouse Microclimate Experiment: Summary Results',
                fontsize=18, fontweight='bold', y=0.995)
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


if __name__ == "__main__":
    print("Statistical plotting module loaded.")
    print("Available functions:")
    print("  - plot_biomass_vs_vpd()")
    print("  - plot_spatial_heatmap()")
    print("  - plot_baseline_vs_treatment()")
    print("  - plot_morans_i_scatter()")
    print("  - plot_model_diagnostics()")
    print("  - create_summary_figure()")
