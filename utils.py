import math

def clamp(value, min_value, max_value):
    """Ensures that the value stays within the [min_value, max_value] range."""
    return max(min_value, min(max_value, value))

def lerp(a, b, t):
    """Linear interpolation between a and b with t in [0,1]."""
    return (1 - t) * a + t * b

def slerp(a, b, t):
    """Spherical linear interpolation between a and b with t in [0,1]."""
    t = clamp(t, 0.0, 1.0)
    # Calculate the shortest angular difference
    diff = (b - a) % 360
    if diff > 180:
        b = a - (360 - diff)
    theta_0 = math.radians(a)
    theta_1 = math.radians(b)
    delta = theta_1 - theta_0
    theta = theta_0 + delta * t
    return math.degrees(theta % (2 * math.pi))
