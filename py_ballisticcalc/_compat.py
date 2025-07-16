import bisect
import sys

"""Get a function that runs bisect_left on a list with a key lambda.  For compatibility with Python < 3.10."""


def get_bisect_left_key_func():
    """Get a function that runs bisect_left on a list with a key lambda.  For compatibility with Python < 3.10."""
    if sys.version_info >= (3, 10):
        return bisect.bisect_left

    # For Python < 3.10, we need to extract keys manually
    def _bisect_left_key(a, x, key):
        keys = [key(item) for item in a]
        return bisect.bisect_left(keys, x)

    return _bisect_left_key


bisect_left_key = get_bisect_left_key_func()

__all__ = (
    'bisect_left_key',
)
