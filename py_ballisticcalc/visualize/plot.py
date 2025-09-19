"""Ballistic Trajectory Visualization and Plotting Module.

This module provides matplotlib-based trajectory analysis and visualization.
It is used by HitResult.plot() and DangerSpace.overlay().

Key Features:
    - Interactive trajectory plotting with customizable styling
    - Danger space visualization overlays for tactical analysis
    - Time-of-flight axis integration for temporal analysis
    - Velocity profiling on secondary axes
    - Special point marking (zero crossings, Mach transitions)
    - Sight line and barrel line visualization
    - Multi-format export capabilities

Core Functions:
    - hit_result_as_plot: Complete trajectory visualization with all features
    - trajectory_as_plot: Simplified trajectory plotting
    - add_danger_space_overlay: Tactical danger space visualization
    - add_time_of_flight_axis: Temporal analysis integration
    - show_hit_result_plot: Interactive display functionality

Examples:
    ```python
    from py_ballisticcalc import Calculator, Shot
    from py_ballisticcalc.visualize.plot import hit_result_as_plot
    import matplotlib.pyplot as plt
    
    # Calculate trajectory
    calc = Calculator()
    shot = Shot(...)
    shot_result = calc.fire(shot, trajectory_range=1000)
    
    # Create comprehensive plot
    ax = shot_result.plot()
    
    # Add danger space analysis
    danger_space = shot_result.danger_space(at_range=200, target_height=1.5)
    danger_space.overlay(ax)
    
    # Display results
    plt.title("Ballistic Trajectory Analysis")
    plt.show()
    ```

Dependencies:
    This module requires matplotlib as an optional dependency. Install via:
    `pip install py_ballisticcalc[visualize]`

Visualization Components:
    - Trajectory Path: Primary projectile path with environmental corrections
    - Sight Line: Line-of-sight from scope to target
    - Barrel Line: Bore axis direction and launch angle
    - Velocity Profile: Secondary axis showing velocity decay
    - Special Points: Zero crossings, Mach transitions
    - Danger Space: Tactical engagement zone visualization
    - Time Axis: Temporal correlation for flight time analysis

Styling and Customization:
    The module uses a consistent color scheme optimized for both screen display
    and print publication. Colors are defined in PLOT_COLORS dictionary and
    can be customized for specific visualization requirements.
"""
# pylint: skip-file
from __future__ import annotations
# Standard library imports
import math
import warnings

# Third-party imports
from typing_extensions import Any, Optional

# Local imports
from py_ballisticcalc import HitResult
from py_ballisticcalc.helpers import find_time_for_distance_in_shot
from py_ballisticcalc.trajectory_data import TrajFlag, DangerSpace
from py_ballisticcalc.unit import PreferredUnits, Angular

# Handle optional matplotlib dependency with graceful degradation
try:
    import matplotlib
    from matplotlib.patches import Polygon
    from matplotlib.axes import Axes
    from matplotlib import pyplot, ticker

    assert matplotlib
except (ImportError, AssertionError) as error:
    warnings.warn("Install matplotlib to get results as a plot", UserWarning)
    raise error

__all__ = (
    'show_hit_result_plot',
    'add_danger_space_overlay',
    'trajectory_as_plot',
    'hit_result_as_plot',
    'add_time_of_flight_axis',
)

# Plotting configuration constants
PLOT_FONT_HEIGHT = 72
PLOT_FONT_SIZE = 552 / PLOT_FONT_HEIGHT

# Color scheme optimized for both screen and print visualization
PLOT_COLORS: dict[Any, tuple[float, float, float, float]] = {
    "trajectory": (130 / 255, 179 / 255, 102 / 255, 1.0),
    "frame": (.0, .0, .0, 1.0),
    "velocity": (108 / 255, 142 / 255, 191 / 255, 1.0),
    "sight": (150 / 255, 115 / 255, 166 / 255, 1.0),
    "barrel": (184 / 255, 84 / 255, 80 / 255, 1.0),
    "face": (.0, .0, .0, .0),
    TrajFlag.ZERO_UP: (215 / 255, 155 / 255, .0, 1.0),
    TrajFlag.ZERO_DOWN: (108 / 255, 142 / 255, 191 / 255, 1.0),
    TrajFlag.MACH: (184 / 255, 84 / 255, 80 / 255, 1.0)
}


def show_hit_result_plot() -> None:
    """Display the current matplotlib plot using the configured backend.

    Note:
        This function requires a properly configured matplotlib backend.
        In some environments (e.g., headless servers), you may need to
        configure an appropriate backend before calling this function.
        
        For Jupyter notebooks, plots are typically displayed automatically
        without requiring this function call.
    
    Raises:
        RuntimeError: If no matplotlib backend is available for display.
        ImportError: If matplotlib is not properly installed.
    """
    pyplot.show()


def add_danger_space_overlay(danger_space: DangerSpace, ax: Axes, label: Optional[str] = None) -> None:
    """Add danger space visualization overlay to existing trajectory plot.
    
    This function highlights the danger space region on a trajectory plot,
    providing tactical visualization of the area where a projectile poses
    a threat to targets of specified height. The danger space is rendered
    as a filled polygon with appropriate transparency and color coding.
    
    The danger space represents the ground distance over which a projectile
    remains dangerous to a target of given height, accounting for trajectory
    curvature and ballistic characteristics.
    
    Args:
        danger_space: DangerSpace object containing calculated danger zone data.
                     Must include near and far distance boundaries and associated
                     trajectory points for accurate visualization.
        ax: Matplotlib Axes object to overlay the danger space visualization.
           Should contain an existing trajectory plot for proper context.
        label: Optional custom label for the danger space overlay.
              If None, uses default danger space description.
              Use empty string '' to suppress labeling.
              
    Examples:
        Basic danger space overlay:
        ```python
        # Calculate trajectory and danger space
        hit_result = calc.fire(shot, trajectory_range=1000)
        danger_space = hit_result.danger_space(
            at_range=Distance.Yard(300),
            target_height=Distance.Meter(1.8)  # Human target
        )
        
        # Create plot with danger space
        ax = hit_result.plot()
        add_danger_space_overlay(danger_space, ax)
        plt.title("Trajectory with Danger Space Analysis")
        plt.show()
        ```
        
        Multiple danger spaces:
        ```python
        # Different target heights
        ax = hit_result.plot()
        
        # Vehicle danger space
        vehicle_danger = hit_result.danger_space(600, Distance.Meter(2.0))
        add_danger_space_overlay(vehicle_danger, ax, "Vehicle")
        
        # Personnel danger space  
        personnel_danger = hit_result.danger_space(400, Distance.Meter(1.8))
        add_danger_space_overlay(personnel_danger, ax, "Personnel")
        
        plt.show()
        ```
    
    Visualization Features:
        - Filled polygon showing ground danger zone extent
        - Semi-transparent red overlay preserving trajectory visibility
        - Target height indicator at specified range position
        - Automatic labeling with range and target information
        - Color coding consistent with ballistic analysis standards
        - Automatic scaling to match existing plot dimensions
    
    Mathematical Background:
        The danger space calculation considers:
        - Projectile trajectory curvature over the engagement range
        - Near and far intersection points with target profile
        
        The visualization accurately represents the ground projection
        of the three-dimensional danger volume for the specified target.
    
    Note:
        The danger space overlay preserves existing plot formatting and
        scales. Ensure the trajectory plot covers the danger space range
        for complete visualization.
        
        For very large danger spaces or extreme trajectory angles, consider
        adjusting plot limits to ensure full danger space visibility.
        
        The target height indicator shows the vertical extent of the target
        at the specified engagement range, providing context for the
        danger space calculation.
    """
    # Extract distance and height values in preferred units
    begin_dist = (danger_space.begin.distance >> PreferredUnits.distance)
    begin_drop = (danger_space.begin.height >> PreferredUnits.drop)
    end_dist = (danger_space.end.distance >> PreferredUnits.distance)
    end_drop = (danger_space.end.height >> PreferredUnits.drop)
    range_dist = (danger_space.at_range.distance >> PreferredUnits.distance)
    range_drop = (danger_space.at_range.height >> PreferredUnits.drop)
    h = danger_space.target_height >> PreferredUnits.drop

    # Target position and height indicator (dotted red line)
    ax.plot((range_dist, range_dist), (range_drop + h / 2, range_drop - h / 2),
            color='r', linestyle=':')
            
    # Shaded danger-space region (filled polygon)
    vertices = (
        (begin_dist, begin_drop), (end_dist, begin_drop),
        (end_dist, end_drop), (begin_dist, end_drop)
    )
    polygon = Polygon(vertices, closed=True, edgecolor='none', facecolor='r', alpha=0.3)
    ax.add_patch(polygon)
    
    # Add label if requested
    if label is None:  # Use default label
        label = f"Danger space\nat {danger_space.at_range.slant_distance << PreferredUnits.distance}"
    if label != '':  # Add label if not explicitly suppressed
        ax.text(begin_dist + (end_dist - begin_dist) / 2, end_drop, label, color='r',
                linespacing=1.2, fontsize=PLOT_FONT_SIZE, ha='center', va='top')


def add_time_of_flight_axis(ax: Axes, hit_result: HitResult, time_precision: int = 1) -> Axes:
    """Add a secondary x-axis to the top of the shot plot, representing the time of flight in seconds.

    The ticks on the time axis correspond to the distance ticks at the bottom of the plot, where applicable.
    Time values are formatted according to the specified precision.

    Args:
        ax: The matplotlib Axes object to which the time of flight axis will be added.
        hit_result: The result object containing shot data, including distances and times.
        time_precision: Number of decimal points to use when formatting time values. Defaults to 1.

    Returns:
        The original Axes object with the added time of flight axis.
    """

    def time_label_for_distance(distance_in_unit, distance_unit, decimal_point_in_seconds):
        time = find_time_for_distance_in_shot(hit_result, distance_in_unit, distance_unit)
        if math.isnan(time):
            return ""
        else:
            return f"{time:.{decimal_point_in_seconds}f}"

    twin_x_axes = ax.twiny()
    twin_x_axes.set_xlim(ax.get_xlim())
    xticks = ax.get_xticks()
    shot_last_distance = hit_result[-1].distance >> PreferredUnits.distance
    sensible_time_ticks = xticks[xticks <= shot_last_distance]
    sensible_time_ticks = sensible_time_ticks[sensible_time_ticks >= 0]

    sensible_top_labels = [
        time_label_for_distance(x, PreferredUnits.distance, time_precision)
        for x in sensible_time_ticks
    ]
    twin_x_axes.xaxis.set_major_locator(ticker.FixedLocator(sensible_time_ticks.tolist()))
    twin_x_axes.xaxis.set_major_formatter(ticker.FixedFormatter(sensible_top_labels))

    twin_x_axes.set_xlabel("s")
    return ax


def trajectory_as_plot(hit_result: HitResult, look_angle: Optional[Angular] = None) -> Axes:
    """Plot only trajectory, barrel, and sight lines.

    Args:
        hit_result: The result object containing shot trajectory data.
        look_angle: The look angle for the sight line. If None, uses the one from hit_result.

    Returns:
        Matplotlib Axes object with the plotted trajectory, barrel, and sight lines.

    Note:
        This function does not plot time axis or velocity profile.
        For a more comprehensive plot, use `hit_result_as_plot`.
    """
    if look_angle is None:
        look_angle = hit_result.props.look_angle

    font_size = PLOT_FONT_SIZE
    df = hit_result.dataframe()
    fig, ax = pyplot.subplots()

    ax = df.plot(x='distance', y=['height'], ylabel=PreferredUnits.drop.symbol,
                 color=PLOT_COLORS['trajectory'], linewidth=2, ax=ax)

    # Transparent figure and axes background
    fig.patch.set_alpha(0.0)  # Set the figure (background) to transparent
    ax.patch.set_alpha(0.0)  # Set the axis background to transparent

    max_range = df.distance.max()
    max_range_in_drop_units = PreferredUnits.distance(df.distance.max()) >> PreferredUnits.drop
    # Sight line
    x_sight = [0, max_range]
    y_sight = [0, max_range_in_drop_units * math.tan(look_angle >> Angular.Radian)]
    ax.plot(x_sight, y_sight, linestyle='--', color=PLOT_COLORS['sight'])
    # Barrel pointing line
    x_bbl = [0, max_range]
    y_bbl = [-(hit_result.props.shot.weapon.sight_height >> PreferredUnits.drop),
             max_range_in_drop_units * math.tan(hit_result.trajectory[0].angle >> Angular.Radian)
             - (hit_result.props.shot.weapon.sight_height >> PreferredUnits.drop)]
    ax.plot(x_bbl, y_bbl, linestyle=':', color=PLOT_COLORS['barrel'])
    # Line labels
    sight_above_bbl = y_sight[1] > y_bbl[1]
    if (x_sight[1] - x_sight[0]) == 0:
        angle = 90.0
    else:
        angle = math.degrees(math.atan((y_sight[1] - y_sight[0]) / (x_sight[1] - x_sight[0])))
    ax.text(x_sight[1], y_sight[1], "Sight line", linespacing=1.2,
            rotation=angle, rotation_mode='anchor', transform_rotates_text=True,
            fontsize=font_size, color=PLOT_COLORS['sight'], ha='right',
            va='bottom' if sight_above_bbl else 'top')
    if (x_bbl[1] - x_bbl[0]) == 0:
        angle = 90.0
    else:
        angle = math.degrees(math.atan((y_bbl[1] - y_bbl[0]) / (x_bbl[1] - x_bbl[0])))
    ax.text(x_bbl[1], y_bbl[1],
            "Launch angle", linespacing=1.2,
            rotation=angle, rotation_mode='anchor',
            transform_rotates_text=True,
            fontsize=font_size, color=PLOT_COLORS['barrel'],
            ha='right', va='top' if sight_above_bbl else 'bottom')
    return ax


def hit_result_as_plot(hit_result, look_angle: Optional[Angular] = None, show_time_axis: bool = True) -> Axes:
    """Plot trajectory, velocity on secondary axis, barrel and sight lines, and optional time axis.

    Args:
        hit_result: The result object containing shot trajectory data.
        look_angle: The look angle for the sight line. If None, uses the one from hit_result.
        show_time_axis: Whether to add the time of flight axis to the plot.

    Returns:
        Matplotlib Axes object with the plotted trajectory and additional features.
    """
    ax = trajectory_as_plot(hit_result, look_angle)

    font_size = PLOT_FONT_SIZE
    df = hit_result.dataframe()
    max_range = df.distance.max()
    backward_bending_trajectory = (hit_result[-1].distance >> PreferredUnits.distance) != max_range

    for p in hit_result.trajectory:
        if TrajFlag(p.flag) & TrajFlag.ZERO:
            ax.plot([p.distance >> PreferredUnits.distance, p.distance >> PreferredUnits.distance],
                    [df['height'].min(), p.height >> PreferredUnits.drop], linestyle=':',
                    color=PLOT_COLORS[TrajFlag(p.flag) & TrajFlag.ZERO])
            ax.text((p.distance >> PreferredUnits.distance) + max_range / 100, df['height'].min(),
                    f"{TrajFlag.name(TrajFlag(p.flag) & TrajFlag.ZERO)}",
                    fontsize=font_size, rotation=90, color=PLOT_COLORS[TrajFlag(p.flag) & TrajFlag.ZERO])
        if TrajFlag(p.flag) & TrajFlag.MACH:
            ax.plot([p.distance >> PreferredUnits.distance, p.distance >> PreferredUnits.distance],
                    [df['height'].min(), p.height >> PreferredUnits.drop],
                    linestyle=':', color=PLOT_COLORS[TrajFlag.MACH])
            ax.text((p.distance >> PreferredUnits.distance) + max_range / 100, df['height'].min(),
                    "Mach 1", fontsize=font_size, rotation=90, color=PLOT_COLORS[TrajFlag.MACH])

    # Plot velocity (on secondary axis)
    df.plot(x='distance', xlabel=PreferredUnits.distance.symbol,
            y=['velocity'], ylabel=PreferredUnits.velocity.symbol,
            secondary_y=True, color=PLOT_COLORS['velocity'],
            ylim=[0, df['velocity'].max()], ax=ax)
    # Let secondary shine through
    ax.set_zorder(1)
    ax.set_facecolor(PLOT_COLORS['face'])

    # Set frame (border) color to rgb(215, 155, 0)
    for spine in ax.spines.values():
        spine.set_edgecolor(PLOT_COLORS['frame'])
        spine.set_linewidth(1)  # Optional: set the thickness of the frame

    # Set axis labels to the same color (rgb(215, 155, 0))
    ax.xaxis.label.set_color(PLOT_COLORS['frame'])  # X-axis label color
    ax.yaxis.label.set_color(PLOT_COLORS['frame'])  # Y-axis label color
    # Secondary Y-axis label color (if applicable)
    ax.right_ax.yaxis.label.set_color(PLOT_COLORS['frame'])  # type: ignore[attr-defined]

    # Set the ticks color to match the frame and labels (optional)
    ax.tick_params(axis='x', colors=PLOT_COLORS['frame'])
    ax.tick_params(axis='y', colors=PLOT_COLORS['frame'])
    # For the secondary y-axis
    ax.right_ax.tick_params(axis='y', colors=PLOT_COLORS['frame'])  # type: ignore[attr-defined]

    if show_time_axis:
        if not backward_bending_trajectory:
            add_time_of_flight_axis(ax, hit_result)
        else:
            warnings.warn("Trajectory bends backward; suppressing time axis.")

    return ax
