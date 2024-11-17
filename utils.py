import math
import random

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

def lerp_color(color_start, color_end, t):
    """
    Linearly interpolates between two RGB/RGBA colors.

    Parameters:
    - color_start (tuple): Starting RGB/RGBA color.
    - color_end (tuple): Ending RGB/RGBA color.
    - t (float): Interpolation factor between 0 and 1.

    Returns:
    - tuple: Interpolated RGB/RGBA color.
    """
    # If both colors have alpha channels
    if len(color_start) == 4 and len(color_end) == 4:
        return (
            int(lerp(color_start[0], color_end[0], t)),
            int(lerp(color_start[1], color_end[1], t)),
            int(lerp(color_start[2], color_end[2], t)),
            int(lerp(color_start[3], color_end[3], t))
        )
    
    # If only one color has alpha, preserve RGB interpolation and use the existing alpha
    if len(color_start) == 4:
        return (
            int(lerp(color_start[0], color_end[0], t)),
            int(lerp(color_start[1], color_end[1], t)),
            int(lerp(color_start[2], color_end[2], t)),
            color_start[3]
        )
    
    if len(color_end) == 4:
        return (
            int(lerp(color_start[0], color_end[0], t)),
            int(lerp(color_start[1], color_end[1], t)),
            int(lerp(color_start[2], color_end[2], t)),
            color_end[3]
        )
    
    # Default RGB interpolation
    return (
        int(lerp(color_start[0], color_end[0], t)),
        int(lerp(color_start[1], color_end[1], t)),
        int(lerp(color_start[2], color_end[2], t))
    )

def random_color_variation(base_color, variation=30):
    """
    Adds a random variation to a base color.

    Parameters:
    - base_color (tuple): Base RGB color.
    - variation (int): Maximum variation per channel.

    Returns:
    - tuple: Modified RGB color with variation.
    """
    return tuple(
        clamp(c + random.randint(-variation, variation), 0, 255)
        for c in base_color
    )