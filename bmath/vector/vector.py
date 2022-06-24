import math


class Vector(object):
    """ Vector object keeps data about a 3D vector """

    def __init__(self, x: float, y: float, z: float):
        """
        Create create a vector from its coordinates
        :param x: X-coordinate
        :param y: Y-coordinate
        :param z: Z-coordinate
        """
        self.x = x
        self.y = y
        self.z = z

    def __str__(self) -> str:
        """
        Converts a vector into a string
        :return: formatted string [X, Y, Z]
        """
        return f'[X={self.x}, Y={self.y}, Z={self.z}]'

    def __copy__(self) -> 'Vector':
        """
        Creates a copy of the vector
        :return: Vector
        """
        return Vector(self.x, self.y, self.z)

    @staticmethod
    def multiply_by_vector(v1: 'Vector', v2: 'Vector') -> float:
        """
        Returns a product of two vectors
        The product of two vectors is a sum of products of each coordinate
        :param v1: Vector(x1, y1, z1)
        :param v2: Vector(x2, y2, z2)
        :return: float
        """
        return v1.x * v2.x + v1.y * v2.y + v1.z * v2.z

    def magnitude(self) -> float:
        """
        Retruns a magnitude of the vector
        The magnitude of the vector is the length of a line that starts in point (0,0,0)
        and ends in the point set by the vector coordinates
        :return: magnitude of the vector
        """
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    @staticmethod
    def multiply_by_const(v1: 'Vector', a: float) -> 'Vector':
        """
        Multiplies the vector by the constant
        :param v1: Vector(x1, y1, z1)
        :param a: float multiplier
        :return: Vector
        """
        return Vector(v1.x * a, v1.y * a, v1.z * a)

    @staticmethod
    def add(v1: 'Vector', v2: 'Vector') -> 'Vector':
        """
        Adds two vectors
        :param v1: Vector(x1, y1, z1)
        :param v2: Vector(x2, y2, z2)
        :return: sum of two vectors
        """
        return Vector(v1.x + v2.x, v1.y + v2.y, v1.z + v2.z)

    @staticmethod
    def substract(v1: 'Vector', v2: 'Vector') -> 'Vector':
        """
        Subtracts one vector from another
        :param v1: Vector(x1, y1, z1)
        :param v2: Vector(x2, y2, z2)
        :return: Vector
        """
        return Vector(v1.x - v2.x, v1.y - v2.y, v1.z - v2.z)

    @staticmethod
    def negate(v1: 'Vector') -> 'Vector':
        """
        Returns a vector which is symmetrical to this vector vs (0,0,0) point
        :param v1: Vector(x1, y1, z1)
        :return: Vector
        """
        return Vector(-v1.x, -v1.y, -v1.z)

    @staticmethod
    def normalize(v1: 'Vector') -> 'Vector':
        """
        Returns a vector of magnitude one which is collinear to this vector
        :param v1: Vector(x1, y1, z1)
        :return: Vector
        """
        magnitude = v1.magnitude()
        if abs(magnitude) < 1 ** -10:
            return v1.__copy__()
        return v.multiply_by_const(v, 1.0 / magnitude)

    # def multiply_self_by_const(self, a: float) -> None:
    #     """
    #     MultiplyByConst multiplies the vector by the constant
    #     :param self:
    #     :param a: float multiplier
    #     :return:
    #     """
    #     self.x *= a
    #     self.y *= a
    #     self.z *= a

    # def multiply_self_by_vector(self, v2: 'Vector') -> float:
    #     """
    #     MultiplyByVector returns a product of two vectors
    #     The product of two vectors is a sum of products of each coordinate
    #     :param self:
    #     :param v2: another Vector(x, y, z)
    #     :return: float
    #     """
    #     return self.x * v2.x + self.y * v2.y + self.z * v2.z


if __name__ == '__main__':
    v = Vector(10, 20, 8)
    print(v.magnitude(), Vector.magnitude(v))
