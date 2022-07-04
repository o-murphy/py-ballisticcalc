import math


class CramerSpeedOfSound(object):

    @staticmethod
    def at_atmosphere(t: float = 26, p: float = 760, rh: float = 50):
        kelvin = 273.15  # For converting to Kelvin
        # e = 2.71828182845904523536
        e = math.e
        pa = p / 7.501 * 1000  # 760mmHg ~= 101,325kpa
        if rh > 100 or rh < 0:
            raise ValueError("Data out of range: Relative humidity must be between 0 and 100%")

        t_kel = kelvin + t  # Measured ambient temp

        # Molecular concentration of water vapour calculated from Rh
        # using Giacomos method by Davis (1991) as implemented in DTU report 11b-1997
        enh = 3.141593 * 10 ** -8 * pa + 1.00062 + t ** 2 * 5.6 * 10 ** -7

        psv1 = t_kel ** 2 * 1.2378847 * 10 ** -5 - 1.9121316 * 10 ** -2 * t_kel
        psv2 = 33.93711047 - 6.3431645 * 10 ** 3 / t_kel

        psv = e ** psv1 * e ** psv2
        h = rh * enh * psv / pa
        xw = h / 100.0

        # Xc = 314.0 * 10 ** -6
        xc = 400.0 * 10 ** -6

        # Speed calculated using the method
        # of Cramer from JASA vol 93 p. 2510

        c1 = 0.603055 * t + 331.5024 - t ** 2 * 5.28 * 10 ** -4 + (
                0.1495874 * t + 51.471935 - t ** 2 * 7.82 * 10 ** -4) * xw
        c2 = (-1.82 * 10 ** -7 + 3.73 * 10 ** -8 * t - t ** 2 * 2.93 * 10 ** -10) * pa + (
                -85.20931 - 0.228525 * t + t ** 2 * 5.91 * 10 ** -5) * xc
        c3 = xw ** 2 * 2.835149 - pa ** 2 * 2.15 * 10 ** -13 + xc ** 2 * 29.179762 + 4.86 * 10 ** -4 * xw * pa * xc

        c = c1 + c2 - c3
        return c
