import asyncio
import logging

from PIL import Image, ImageDraw, ImageFont

from aerial_targets_shooting.aerial_target import AerialTarget
from py_ballisticcalc import *
from py_ballisticcalc.logger import logger

logger.setLevel(logging.DEBUG)

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Thousandth
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter
PreferredUnits.angular = Angular.Degree


def new_img(scale=20):
    im = Image.new('RGB', im_size, color='white')
    draw = ImageDraw.Draw(im)
    draw.line(((im.width // 2, 0), (im.width // 2, im.height)), fill='black')
    draw.line(((0, im.height // 2), (im.width, im.height // 2)), fill='black')

    for y in range(im.height // 2, im.height, scale):
        draw.line(((im.width // 2 - 5, y), (im.width // 2 + 5, y)), fill='black')
    for y in range(im.height // 2, 0, -scale):
        draw.line(((im.width // 2 - 5, y), (im.width // 2 + 5, y)), fill='black')

    for x in range(im.width // 2, im.width, scale):
        draw.line(((x, im.height // 2 - 5), (x, im.height // 2 + 5)), fill='black')
    for x in range(im.width // 2, 0, -scale):
        draw.line(((x, im.height // 2 - 5), (x, im.height // 2 + 5)), fill='black')

    for x in range(0, im.width // 2 + scale + 1, 4 * scale):
        draw.circle((im.width // 2, im.height // 2), radius=x, outline='black')
    return im


def get_trajectory_for_look_angle(distance, look_angle):
    # set_global_use_powder_sensitivity(True)  # enable muzzle velocity correction my powder temperature

    # define params with default prefer_units
    length = Distance.Inch(2.3)

    weapon = Weapon(sight_height=Unit.Centimeter(9.5), twist=15)
    dm = DragModel(0.62, TableG1, 661, 0.51, length=length)
    ammo = Ammo(dm, 900)

    zero_atmo = Atmo(
        altitude=Unit.Meter(150),
        pressure=Unit.hPa(1000),
        temperature=Unit.Celsius(15),
        humidity=50
    )
    zero = Shot(weapon=weapon, ammo=ammo, atmo=zero_atmo)
    zero_distance = Distance.Meter(500)

    calc = Calculator()
    calc.set_weapon_zero(zero, zero_distance)

    shot = Shot(look_angle=look_angle, weapon=weapon, ammo=ammo, atmo=zero_atmo)
    shot_result = calc.fire(shot, distance, Distance.Meter(10))
    return shot_result


# props to draw reticle
click = 1.5
grid_colors = ['red', 'blue', 'green']
grid_scale = int((Unit.Thousandth(5) >> Unit.CmPer100m) / click)
print(f'{grid_scale=}')

im: Image = None
draw: ImageDraw = None
im_size = (1188, 842)

# initial values
flight_direction, look_angle, flight_time = 0, 0, 0
distance = Distance.Meter(501)
initial_target = None
font = ImageFont.truetype("arial.ttf", 20)
shot_result = None


async def get_preemption_point(look_angle, flight_direction):
    global initial_target
    # define first target position to sight line
    initial_target = AerialTarget(
        Velocity.MPS(50),
        distance,
        Angular.Degree(flight_direction),
        Angular.Degree(look_angle),
        Angular.Degree(15),
        Distance.Meter(3)
    )

    # calculate trajectory to get bullet flight time
    flight_time = shot_result[-1:][0].time

    # calculate target position relative to sight line
    _, pos = initial_target.at_time(flight_time)

    # [print(row) for row in f"{pos!r}".split(', ')]
    # print()

    xs = pos.x_shift >> Unit.Thousandth
    ys = pos.y_shift >> Unit.Thousandth

    adjusted_shot_result = get_trajectory_for_look_angle(pos.look_distance, pos.look_angle)
    adjusted_flight_time = adjusted_shot_result[-1:][0].time

    _, adjusted_pos = initial_target.at_time(adjusted_flight_time)

    pos_projection_point = (
        im.width // 2 + xs * (grid_scale // 4),
        im.height // 2 + ys * (grid_scale // 4)
    )

    adjusted_pos_projection_point = (
        im.width // 2 + (adjusted_pos.x_shift >> Unit.Thousandth) * (grid_scale // 4),
        im.height // 2 + (adjusted_pos.y_shift >> Unit.Thousandth) * (grid_scale // 4)
    )

    # draw.circle(adjusted_pos_projection_point, radius=3, fill="#0000ff")
    # print(f"time: {flight_time:.3f} | {adjusted_flight_time:.3f} | {flight_time-adjusted_flight_time:.3f}")
    return pos_projection_point, adjusted_pos_projection_point


async def get_preemption_points(look_angle):
    global shot_result
    shot_result = get_trajectory_for_look_angle(distance, look_angle)
    tasks = [get_preemption_point(look_angle, flight_direction) for flight_direction in range(0, 360, 15)]
    points = await asyncio.gather(*tasks)
    # points += [(-p[0], p) for p in points]
    return points


async def draw_preemption_points(draw):
    tasks = [get_preemption_points(look_angle) for look_angle in range(10, 31, 10)]
    ellipses = await asyncio.gather(*tasks)
    colors = ['red', 'blue', 'green']
    look_angles_ = list(range(10, 31, 10))

    for ellipse in ellipses:
        look_angle_ = look_angles_.pop(0)
        color = colors.pop()
        points, adjusted_points = zip(*ellipse)

        for i, p in enumerate(adjusted_points):
            if logger.level == logging.DEBUG:
                draw.circle(p, radius=2, fill=color)
                draw.circle(points[i], radius=1, fill='black')
            else:
                draw.circle(p, radius=2, fill='black')

        max_x = max(adjusted_points, key=lambda p: p[0])[0]
        min_x = min(adjusted_points, key=lambda p: p[0])[0]
        max_y = max(adjusted_points, key=lambda p: p[1])[1]
        min_y = min(adjusted_points, key=lambda p: p[1])[1]

        if logger.level == logging.DEBUG:
            draw.ellipse((
                min_x,
                min_y,
                max_x,
                max_y
            ), outline=color)

            draw.text((im.width // 2 + 10, max_y),
                      f"look_angle: {look_angle_:.2f}deg",
                      fill=color,
                      font=font)
        else:
            draw.ellipse((
                min_x,
                min_y,
                max_x,
                max_y
            ), outline='black')

    if logger.level == logging.DEBUG:
        draw.text((10, 10),
                  text=f"look distance: {distance >> Unit.Meter:.2f}m\n"
                       f"click:         {click:.3f}",
                  fill='black',
                  font=font)


async def calculate_reticles():
    global distance, im, draw
    for d in [500, 800, 1000]:
        distance = Distance.Meter(d)
        im = new_img(grid_scale)
        draw = ImageDraw.Draw(im)
        await draw_preemption_points(draw)
        im.save(f"{distance}m_{click}_{im_size[0]}x{im_size[1]}.png")


asyncio.run(calculate_reticles())
