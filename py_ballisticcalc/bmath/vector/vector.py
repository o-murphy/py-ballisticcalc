import math


class Vector(object):
    """ VectorCed object keeps data about a 3D vector """

    def __init__(self, x: float, y: float, z: float):
        """
        Create create a vector from its coordinates
        :param x: X-coordinate
        :param y: Y-coordinate
        :param z: Z-coordinate
        """
        self.x: float = x
        self.y: float = y
        self.z: float = z

    def __str__(self) -> str:
        """
        Converts a vector into a string
        :return: formatted string [X, Y, Z]
        """
        return f'[X={self.x}, Y={self.y}, Z={self.z}]'

    def __copy__(self) -> 'VectorCed':
        """
        Creates a copy of the vector
        :return: VectorCed
        """
        return Vector(self.x, self.y, self.z)

    def multiply_by_vector(self, v2: 'VectorCed') -> float:
        """
        Returns a product of two vectors
        The product of two vectors is a sum of products of each coordinate
        :param v2: VectorCed(x2, y2, z2)
        :return: float
        """
        return self.x * v2.x + self.y * v2.y + self.z * v2.z
        # return cvector.multiply_by_vector(self.x, self.y, self.z, v2.x, v2.y, v2.z)

    def magnitude(self) -> float:
        """
        Returns a magnitude of the vector
        The magnitude of the vector is the length of a line that starts in point (0,0,0)
        and ends in the point set by the vector coordinates
        :return: magnitude of the vector
        """
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        # return cvector.magnitude(self.x, self.y, self.z)


    def multiply_by_const(self, a: float) -> 'VectorCed':
        """
        Multiplies the vector by the constant
        :param a: float multiplier
        :return: VectorCed
        """
        return Vector(self.x * a, self.y * a, self.z * a)

    def add(self, v2: 'VectorCed') -> 'VectorCed':
        """
        Adds two vectors
        :param v2: VectorCed(x2, y2, z2)
        :return: sum of two vectors
        """
        return Vector(self.x + v2.x, self.y + v2.y, self.z + v2.z)

    def subtract(self, v2: 'VectorCed') -> 'VectorCed':
        """
        Subtracts one vector from another
        :param v2: VectorCed(x2, y2, z2)
        :return: VectorCed
        """
        return Vector(self.x - v2.x, self.y - v2.y, self.z - v2.z)

    def negate(self) -> 'VectorCed':
        """
        Returns a vector which is symmetrical to this vector vs (0,0,0) point
        :return: VectorCed
        """
        return Vector(-self.x, -self.y, -self.z)

    def normalize(self) -> 'VectorCed':
        """
        Returns a vector of magnitude one which is collinear to this vector
        :return: VectorCed
        """
        magnitude = self.magnitude()
        if math.fabs(magnitude) < 1e-10:
            return self.__copy__()
        return self.multiply_by_const(1.0 / magnitude)
