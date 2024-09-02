import logging
import sys
import warnings
from concurrent import futures

from aerial_target.aerial_target import AerialTarget
from py_ballisticcalc import *

logger.setLevel(logging.DEBUG)

PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Thousandth
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter
PreferredUnits.angular = Angular.Degree
PreferredUnits.pressure = Pressure.hPa

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    warnings.warn("Pillow not installed. test skipped")
    sys.exit(1)
import concurrent.futures


def new_img(scale=20, im_size=(640, 480)):
    im = Image.new('RGBA', im_size, (255, 255, 255, 255))
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
    return im, draw


click = 3.01
grid_scale = int((Unit.Thousandth(5) >> Unit.CmPer100m) / click)
logger.info(f'{grid_scale=}')
im, draw = new_img(grid_scale, (640, 480))
distance = 800

target = AerialTarget(Velocity.MPS(50),
                      Distance.Meter(distance),
                      Angular.Degree(0),
                      Angular.Degree(20),
                      Distance.Meter(3))

weapon = Weapon(sight_height=9.5, twist=15)
dm = DragModel(0.62, TableG1, 661, 0.51, 2.3)
ammo = Ammo(dm, 900)
zero_atmo = Atmo(altitude=150, pressure=1000, temperature=15, humidity=50)

for look_angle in range(20, 21, 10):
    target.look_angle = Angular.Degree(look_angle)
    points = []
    adjusted_points = []

    for direction in range(0, 181, 30):
        target.direction_from = Angular.Degree(direction)
        target._prepare()

        try:
            with futures.ThreadPoolExecutor() as executor:
                future = executor.submit(target.get_preemption, weapon, ammo, zero_atmo, Distance.Meter(500), False)
                result = future.result(timeout=2)
                pos_projection_point = (
                    im.width // 2 + (result.x_shift >> Unit.Thousandth) * grid_scale // 5,
                    im.height // 2 + (result.y_shift >> Unit.Thousandth) * grid_scale // 5
                )
                points.append(pos_projection_point)

                pos_projection_point = (
                    im.width // 2 - (result.x_shift >> Unit.Thousandth) * grid_scale // 5,
                    im.height // 2 + (result.y_shift >> Unit.Thousandth) * grid_scale // 5
                )
                points.append(pos_projection_point)

        except (RuntimeError, concurrent.futures.TimeoutError) as err:
            logger.error(err)

        try:
            with futures.ThreadPoolExecutor() as executor:
                future = executor.submit(target.get_preemption, weapon, ammo, zero_atmo, Distance.Meter(500), True)
                result = future.result(timeout=30)
                adjusted_pos_projection_point = (
                    im.width // 2 + (result.x_shift >> Unit.Thousandth) * grid_scale // 5,
                    im.height // 2 + (result.y_shift >> Unit.Thousandth) * grid_scale // 5
                )
                adjusted_points.append(adjusted_pos_projection_point)

                adjusted_pos_projection_point = (
                    im.width // 2 - (result.x_shift >> Unit.Thousandth) * grid_scale // 5,
                    im.height // 2 + (result.y_shift >> Unit.Thousandth) * grid_scale // 5
                )
                adjusted_points.append(adjusted_pos_projection_point)

        except (RuntimeError, concurrent.futures.TimeoutError) as err:
            logger.error(err)

    for point in points:
        draw.circle(point, radius=2, fill='black')

    for point in adjusted_points:
        draw.circle(point, radius=2, fill='green')

    max_x = max(points, key=lambda p: p[0])[0]
    min_x = min(points, key=lambda p: p[0])[0]
    max_y = max(points, key=lambda p: p[1])[1]
    min_y = min(points, key=lambda p: p[1])[1]

    draw.ellipse((
        min_x,
        min_y,
        max_x,
        max_y
    ), outline='black')

    max_x = max(adjusted_points, key=lambda p: p[0])[0]
    min_x = min(adjusted_points, key=lambda p: p[0])[0]
    max_y = max(adjusted_points, key=lambda p: p[1])[1]
    min_y = min(adjusted_points, key=lambda p: p[1])[1]

    draw.ellipse((
        min_x,
        min_y,
        max_x,
        max_y
    ), outline='green')

im.save(f'test_target_{distance}_{look_angle}.png')
