from aerial_targets_shooting.aerial_target import AerialTarget
from py_ballisticcalc import *
from PIL import Image, ImageDraw

# set global library settings
PreferredUnits.velocity = Velocity.MPS
PreferredUnits.adjustment = Angular.Thousandth
PreferredUnits.temperature = Temperature.Celsius
PreferredUnits.distance = Distance.Meter
PreferredUnits.sight_height = Distance.Centimeter
PreferredUnits.drop = Distance.Centimeter
PreferredUnits.angular = Angular.Degree


def new_img(scale=20):
    im = Image.new('RGB', (640, 480), color='white')
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
    shot_result = calc.fire(shot, distance, Distance.Meter(100))
    return shot_result


# props to draw reticle
click = 3.01
grid_colors = ['red', 'blue', 'green']
grid_scale = int((Unit.Thousandth(5) >> Unit.CmPer100m) / click)
print(f'{grid_scale=}')
im = new_img(grid_scale)
draw = ImageDraw.Draw(im)

# initial values
flight_direction, look_angle, flight_time = 0, 0, 0
distance = Distance.Meter(301)

for look_angle in range(10, 31, 10):

    color = grid_colors.pop(0)
    points = []
    for flight_direction in range(0, 360, 15):
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
        shot_result = get_trajectory_for_look_angle(distance, initial_target.look_angle)
        flight_time = shot_result[-1:][0].time

        # calculate target position relative to sight line
        target, pos = initial_target.at_time(flight_time)

        # [print(row) for row in f"{pos!r}".split(', ')]
        # print()

        xs = pos.x_shift >> Unit.Thousandth
        ys = pos.y_shift >> Unit.Thousandth

        points.append((im.width // 2 + xs * (grid_scale // 4), im.height // 2 + ys * (grid_scale // 4)))

    for p in points:
        draw.circle(p, radius=3, fill=color)

    max_x = max(points, key=lambda p: p[0])[0]
    min_x = min(points, key=lambda p: p[0])[0]
    max_y = max(points, key=lambda p: p[1])[1]
    min_y = min(points, key=lambda p: p[1])[1]

    draw.ellipse((
        min_x,
        min_y,
        max_x,
        max_y
    ), outline=color)

    draw.text((im.width // 2 + 10, max_y),
              f"look_angle: {look_angle}deg",
              fill=color)

draw.text((10, 10),
          text=f"time:          {flight_time}s\n"
               f"look distance: {distance >> Unit.Meter}m\n"
               f"click:         {click}",
          fill='black')

im.save(f"{look_angle}deg_{distance}m_{click}.png")
