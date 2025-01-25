# type: ignore
# pylint: skip-file

import math

from typing_extensions import Optional
import warnings

from py_ballisticcalc import HitResult
from py_ballisticcalc.trajectory_data import TrajFlag, DangerSpace
from py_ballisticcalc.unit import PreferredUnits, Angular
from py_ballisticcalc.helpers import find_time_for_distance_in_shot

try:
    import matplotlib
    from matplotlib.patches import Polygon
    from matplotlib.axes import Axes
    from matplotlib import pyplot, ticker
except ImportError as error:
    warnings.warn("Install matplotlib to get results as a plot", UserWarning)
    raise error

__all__ = (
    'show_hit_result_plot',
    'add_danger_space_overlay',
    'hit_result_as_plot',
)

PLOT_FONT_HEIGHT = 72
PLOT_FONT_SIZE = 552 / PLOT_FONT_HEIGHT

PLOT_COLORS = {
    "trajectory": (130 / 255, 179 / 255, 102 / 255, 1.0),
    "frame": (.0, .0, .0, 1.0),
    "velocity": (108 / 255, 142 / 255, 191 / 255, 1.0),
    "sight": (150 / 255, 115 / 255, 166 / 255, 1.0),
    "barrel": (184 / 255, 84 / 255, 80 / 255, 1.0),
    "face": (.0, .0, .0, .0),
    TrajFlag.ZERO_UP: (215 / 255, 155 / 255, .0),
    TrajFlag.ZERO_DOWN: (108 / 255, 142 / 255, 191 / 255, 1.0),
    TrajFlag.MACH: (184 / 255, 84 / 255, 80 / 255, 1.0)
}


def show_hit_result_plot() -> None:
    pyplot.show()


def add_danger_space_overlay(danger_space: DangerSpace, ax: 'Axes', label: Optional[str] = None):  # type: ignore
    """Highlights danger-space region on plot"""

    cosine = math.cos(danger_space.look_angle >> Angular.Radian)
    begin_dist = (danger_space.begin.distance >> PreferredUnits.distance) * cosine
    begin_drop = (danger_space.begin.height >> PreferredUnits.drop) * cosine
    end_dist = (danger_space.end.distance >> PreferredUnits.distance) * cosine
    end_drop = (danger_space.end.height >> PreferredUnits.drop) * cosine
    range_dist = (danger_space.at_range.distance >> PreferredUnits.distance) * cosine
    range_drop = (danger_space.at_range.height >> PreferredUnits.drop) * cosine
    h = danger_space.target_height >> PreferredUnits.drop

    # Target position and height:
    ax.plot((range_dist, range_dist), (range_drop + h / 2, range_drop - h / 2),
            color='r', linestyle=':')
    # Shaded danger-space region:
    vertices = (
        (begin_dist, begin_drop), (end_dist, begin_drop),
        (end_dist, end_drop), (begin_dist, end_drop)
    )
    polygon = Polygon(vertices, closed=True,
                      edgecolor='none', facecolor='r', alpha=0.3)
    ax.add_patch(polygon)
    if label is None:  # Add default label
        label = f"Danger space\nat {danger_space.at_range.distance << PreferredUnits.distance}"
    if label != '':
        ax.text(begin_dist + (end_dist - begin_dist) / 2, end_drop, label, color='r',
                linespacing=1.2, fontsize=PLOT_FONT_SIZE, ha='center', va='top')


def add_time_of_flight_axis(ax: 'Axes', hit_result: HitResult, time_precision: int = 1) -> 'Axes':
    """Add on the top of shot plot the axis, corresponding to time of flight in seconds.
       The ticks used for time axis correspond to distance ticks at the bottom of the plot, where it makes sense.
       :param time_precision: describes how much decimal points should be used in formatting time values
    """
    def time_label_for_distance(
        distance_in_unit, distance_unit, decimal_point_in_seconds
    ):
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
    twin_x_axes.xaxis.set_major_locator(ticker.FixedLocator(sensible_time_ticks))
    twin_x_axes.xaxis.set_major_formatter(ticker.FixedFormatter(sensible_top_labels))

    twin_x_axes.set_xlabel("s")
    return ax


def hit_result_as_plot(hit_result, look_angle: Optional[Angular] = None, show_time_axis:bool=True) -> 'Axes':  # type: ignore
    """
    :param hit_result: HitResult object
    :param look_angle: look_angle
    :param show_time_axis: whether time of flight axis should be added to plot
    :return: graph of the trajectory
    """

    if look_angle is None:
        look_angle = hit_result.shot.look_angle

    if not hit_result.extra:
        warnings.warn("HitResult.plot: To show extended data"
                      "Use Calculator.fire(..., extra_data=True)")

    font_size = PLOT_FONT_SIZE
    df = hit_result.dataframe()
    fig, ax = pyplot.subplots()

    ax = df.plot(x='distance', y=['height'], ylabel=PreferredUnits.drop.symbol,
                 color=PLOT_COLORS['trajectory'], linewidth=2, ax=ax)
    #max_range = hit_result.trajectory[-1].distance >> PreferredUnits.distance  # This doesn't correctly handle backward-bending trajectories
    max_range = df.distance.max()
    backward_bending_trajectory = (hit_result[-1].distance>>PreferredUnits.distance)!=max_range


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

    # Transparent figure and axes background
    fig.patch.set_alpha(0.0)  # Set the figure (background) to transparent
    ax.patch.set_alpha(0.0)  # Set the axis background to transparent

    max_range_in_drop_units = PreferredUnits.distance(df.distance.max()) >> PreferredUnits.drop
    # Sight line
    x_sight = [0, max_range]
    y_sight = [0, max_range_in_drop_units * math.tan(look_angle >> Angular.Radian)]
    ax.plot(x_sight, y_sight, linestyle='--', color=PLOT_COLORS['sight'])
    # Barrel pointing line
    x_bbl = [0, max_range]
    y_bbl = [-(hit_result.shot.weapon.sight_height >> PreferredUnits.drop),
             max_range_in_drop_units * math.tan(hit_result.trajectory[0].angle >> Angular.Radian)
             - (hit_result.shot.weapon.sight_height >> PreferredUnits.drop)]
    ax.plot(x_bbl, y_bbl, linestyle=':', color=PLOT_COLORS['barrel'])
    # Line labels
    sight_above_bbl = y_sight[1] > y_bbl[1]
    if (x_sight[1] - x_sight[0]) == 0:
        angle = 90
    else:
        angle = math.degrees(math.atan((y_sight[1] - y_sight[0]) / (x_sight[1] - x_sight[0])))
    ax.text(x_sight[1], y_sight[1], "Sight line", linespacing=1.2,
            rotation=angle, rotation_mode='anchor', transform_rotates_text=True,
            fontsize=font_size, color=PLOT_COLORS['sight'], ha='right',
            va='bottom' if sight_above_bbl else 'top')
    if (x_bbl[1] - x_bbl[0]) == 0:
        angle = 90
    else:
        angle = math.degrees(
            math.atan((y_bbl[1] - y_bbl[0]) / (x_bbl[1] - x_bbl[0]))
        )
    ax.text(x_bbl[1], y_bbl[1],
            "Barrel pointing", linespacing=1.2,
            rotation=angle, rotation_mode='anchor',
            transform_rotates_text=True,
            fontsize=font_size, color=PLOT_COLORS['barrel'],
            ha='right', va='top' if sight_above_bbl else 'bottom')
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
    ax.right_ax.yaxis.label.set_color(PLOT_COLORS['frame'])

    # Set the ticks color to match the frame and labels (optional)
    ax.tick_params(axis='x', colors=PLOT_COLORS['frame'])
    ax.tick_params(axis='y', colors=PLOT_COLORS['frame'])
    # For the secondary y-axis
    ax.right_ax.tick_params(axis='y', colors=PLOT_COLORS['frame'])

    if show_time_axis:
        if not backward_bending_trajectory:
            add_time_of_flight_axis(ax, hit_result)
        else:
            warnings.warn("The trajectory is backward bending. Please add custom time visualization if needed")

    return ax
