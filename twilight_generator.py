import random
import math
from PIL import Image, ImageDraw, ImageQt
from utils import clamp, lerp, slerp, lerp_color

class TwilightState:
    """
    Encapsulates all state variables required for generating a twilight render.
    """

    # Define cyclical attributes and their cycle points
    CYCLICAL_ATTRIBUTES = {
        'time_of_day': 24.000001,   # Cycles every 24 hours
        'latitude': 360.000001,     # Cycles every 360 degrees
        'longitude': 360.000001     # Cycles every 360 degrees
    }

    def __init__(self, 
                 width=1920, 
                 height=1080, 
                 seed=12345,
                 time_of_day=0.0,  # Hour of the day (0-24)
                 star_density=0.5,  # Multiplier for number of stars
                 transition_ratio=0.2,  # Proportion of height for color transitions
                 latitude=0.0,    # 0.0 to 360.0 degrees
                 longitude=0.0,    # 0.0 to 360.0 degrees
                 render_type='spherical'  # 'spherical' or 'flat'
                ):
        # Initialize private attributes
        self._width = None
        self._height = None
        self._seed = None
        self._time_of_day = None
        self._star_density = None
        self._transition_ratio = None
        self._latitude = None
        self._longitude = None
        self._render_type = None

        # Use setters to initialize values with validation
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randint(0, 1000000)
        self.time_of_day = time_of_day
        self.star_density = star_density
        self.transition_ratio = transition_ratio
        self.latitude = latitude
        self.longitude = longitude
        self.render_type = render_type

    # Width
    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if isinstance(value, (int, float)) and value > 0:
            self._width = int(value)
        else:
            raise ValueError("Width must be a positive integer.")

    # Height
    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        if isinstance(value, (int, float)) and value > 0:
            self._height = int(value)
        else:
            raise ValueError("Height must be a positive integer.")

    # Seed
    @property
    def seed(self):
        return self._seed

    @seed.setter
    def seed(self, value):
        if isinstance(value, (int, float)) and 0 <= value <= 1000000:
            self._seed = int(value)
        else:
            raise ValueError("Seed must be an integer between 0 and 1,000,000.")

    # Time of Day
    @property
    def time_of_day(self):
        return self._time_of_day

    @time_of_day.setter
    def time_of_day(self, value):
        if isinstance(value, (int, float)):
            self._time_of_day = value % self.CYCLICAL_ATTRIBUTES['time_of_day']  # Normalize to [0,24)
        else:
            raise ValueError("Time of day must be a number (float or int).")

    # Star Density
    @property
    def star_density(self):
        return self._star_density

    @star_density.setter
    def star_density(self, value):
        if isinstance(value, (int, float)):
            self._star_density = clamp(value, 0.0, 1.0)
        else:
            raise ValueError("Star density must be a number (float or int).")

    # Transition Ratio
    @property
    def transition_ratio(self):
        return self._transition_ratio

    @transition_ratio.setter
    def transition_ratio(self, value):
        if isinstance(value, (int, float)):
            self._transition_ratio = clamp(value, 0.05, 0.5)
        else:
            raise ValueError("Transition ratio must be a number (float or int).")

    # Latitude
    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, value):
        if isinstance(value, (int, float)):
            self._latitude = value % self.CYCLICAL_ATTRIBUTES['latitude']  # Normalize to [0,360)
        else:
            raise ValueError("Latitude must be a number (float or int).")

    # Longitude
    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, value):
        if isinstance(value, (int, float)):
            self._longitude = value % self.CYCLICAL_ATTRIBUTES['longitude']  # Normalize to [0,360)
        else:
            raise ValueError("Longitude must be a number (float or int).")

    # Render Type
    @property
    def render_type(self):
        return self._render_type

    @render_type.setter
    def render_type(self, value):
        if isinstance(value, str):
            value = value.lower()
            if value in ['spherical', 'flat']:
                self._render_type = value
            else:
                raise ValueError("Render type must be 'spherical' or 'flat'.")
        else:
            raise ValueError("Render type must be a string ('spherical' or 'flat').")

    def to_dict(self):
        """Returns the state variables as a dictionary."""
        return {
            'width': self.width,
            'height': self.height,
            'seed': self.seed,
            'time_of_day': self.time_of_day,
            'star_density': self.star_density,
            'transition_ratio': self.transition_ratio,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'render_type': self.render_type
        }

    def copy(self):
        """Creates a deep copy of the TwilightState instance."""
        return TwilightState(
            width=self.width,
            height=self.height,
            seed=self.seed,
            time_of_day=self.time_of_day,
            star_density=self.star_density,
            transition_ratio=self.transition_ratio,
            latitude=self.latitude,
            longitude=self.longitude,
            render_type=self.render_type
        )

class TwilightGenerator:
    """
    Generates twilight wallpaper images based on the provided TwilightState.
    """

    # Constants
    NUM_SMALL_STARS = 2500
    NUM_BIG_STARS = 200

    ORANGE = (255, 72, 0)
    BLUE = (0, 110, 189)
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    def __init__(self, state: TwilightState):
        """
        Initializes the TwilightGenerator with a given TwilightState.
        """
        self.state = state
        self._initialize_parameters()
        self._initialize_stars()
        self.image = None

    def _initialize_parameters(self):
        """Initialize parameters based on the current state."""
        self.width = self.state.width
        self.height = self.state.height
        self.seed = self.state.seed
        self.time_of_day = self.state.time_of_day
        self.star_density = self.state.star_density
        self.transition_ratio = self.state.transition_ratio
        self.latitude = self.state.latitude
        self.longitude = self.state.longitude
        self.render_type = self.state.render_type

        # Initialize random generator with seed
        self.random_gen = random.Random(self.seed)

        # Define star size ranges
        self.size_min = max(1, int(self.width * 0.001))  # 0.1% of width
        self.size_max = max(2, int(self.width * 0.002))  # 0.2% of width

    def _initialize_stars(self):
        """Generate master star lists based on the current state."""
        # Calculate total stars based on density
        self.total_small_stars = int(self.NUM_SMALL_STARS * self.star_density)
        self.total_big_stars = int(self.NUM_BIG_STARS * self.star_density)

        # Generate small stars with normalized coordinates
        self.small_stars = [
            (self.random_gen.uniform(0, 1), self.random_gen.uniform(0, 1))
            for _ in range(self.total_small_stars)
        ]

        # Generate big stars with normalized coordinates and size factor
        self.big_stars = [
            (
                self.random_gen.uniform(0, 1),
                self.random_gen.uniform(0, 1),
                self.random_gen.randint(self.size_min, self.size_max) / self.width
            )
            for _ in range(self.total_big_stars)
        ]

    def set_state(self, state: TwilightState):
        """
        Updates the generator with a new state.

        Parameters:
        - state (TwilightState): The new state to apply.
        """
        regenerate_stars = (
            self.seed != state.seed or
            self.width != state.width or
            self.height != state.height or
            self.star_density != state.star_density
        )

        self.state = state
        self._initialize_parameters()

        if regenerate_stars:
            self._initialize_stars()

    def _create_gradient(self) -> Image.Image:
        """
        Creates a gradient image based on the current time_of_day and transition_ratio.

        Returns:
        - PIL.Image.Image: The gradient overlay.
        """
        gradient = Image.new('RGBA', (self.width, self.height), self.BLACK)
        draw = ImageDraw.Draw(gradient)

        cutoff = self.height * self.transition_ratio

        # Map time_of_day (0-24) to a phase (0-1)
        phase = (self.time_of_day % 24) / 24.0

        # Define gradient colors based on phase
        if phase < 0.25:
            # Midnight to Dawn: black to orange
            ratio = phase / 0.25
            top_color = lerp_color(self.BLACK, self.ORANGE, ratio)
            bottom_color = lerp_color(self.BLACK, self.BLUE, ratio)
        elif phase < 0.5:
            # Dawn to Noon: orange to blue
            ratio = (phase - 0.25) / 0.25
            top_color = lerp_color(self.ORANGE, self.BLUE, ratio)
            bottom_color = self.BLUE
        elif phase < 0.75:
            # Noon to Sunset: blue to orange
            ratio = (phase - 0.5) / 0.25
            top_color = lerp_color(self.BLUE, self.ORANGE, ratio)
            bottom_color = lerp_color(self.BLUE, self.BLACK, ratio)
        else:
            # Sunset to Midnight: orange to black
            ratio = (phase - 0.75) / 0.25
            top_color = lerp_color(self.ORANGE, self.BLACK, ratio)
            bottom_color = self.BLACK

        # Draw the upper gradient (top to cutoff)
        for y in range(int(cutoff)):
            t = y / cutoff
            color = lerp_color(top_color, bottom_color, t)
            draw.line([(0, y), (self.width, y)], fill=color + (255,))

        # Draw the lower gradient (cutoff to bottom)
        for y in range(int(cutoff), self.height):
            t = (y - cutoff) / (self.height - cutoff)
            color = lerp_color(bottom_color, self.BLACK, t)
            draw.line([(0, y), (self.width, y)], fill=color + (255,))

        return gradient

    def _draw_stars(self, base_image: Image.Image) -> Image.Image:
        """
        Draws stars onto the base image.

        Parameters:
        - base_image (PIL.Image.Image): The image to draw stars on.

        Returns:
        - PIL.Image.Image: The image with stars drawn.
        """
        draw = ImageDraw.Draw(base_image)

        # Calculate shifts for flat projection
        longitude_shift = (self.longitude / 360.0) * self.width
        latitude_shift = (self.latitude / 360.0) * self.height

        # Ensure seamless repetition
        longitude_shift %= self.width
        latitude_shift %= self.height

        # Draw small stars as single pixels
        for norm_x, norm_y in self.small_stars:
            x = int((norm_x * self.width + longitude_shift) % self.width)
            y = int((norm_y * self.height + latitude_shift) % self.height)

            color = self._get_star_color(y)
            if 0 <= x < self.width and 0 <= y < self.height:
                base_image.putpixel((x, self.height - y - 1), color + (255,))

        # Draw big stars as diamonds
        for norm_x, norm_y, norm_size in self.big_stars:
            x = int((norm_x * self.width + longitude_shift) % self.width)
            y = int((norm_y * self.height + latitude_shift) % self.height)
            size = max(1, int(norm_size * self.width))

            color = self._get_star_color(y)
            # Draw diamond shape
            for dx, dy in [(-size, 0), (0, -size), (size, 0), (0, size)]:
                xi, yi = x + dx, y + dy
                xi = clamp(xi, 0, self.width - 1)
                yi = clamp(yi, 0, self.height - 1)
                base_image.putpixel((xi, self.height - yi - 1), color + (255,))

        return base_image

    def _get_star_color(self, y: int) -> tuple[int, int, int]:
        """
        Determines the color of a star based on its y-coordinate.

        Parameters:
        - y (int): The y-coordinate of the star.

        Returns:
        - Tuple[int, int, int]: The RGB color of the star.
        """
        if y > self.height / 2:
            return self.WHITE

        cutoff = self.height * self.transition_ratio

        if y < cutoff:
            ratio = y / cutoff
            base_color = lerp_color(self.ORANGE, self.BLUE, ratio)
        else:
            ratio = (y - cutoff) / (self.height - cutoff)
            base_color = lerp_color(self.BLUE, self.BLACK, ratio)

        # Blend with white based on the position
        a = clamp(y / (self.height / 2.0), 0.0, 1.0)
        blended_color = (
            clamp(int(base_color[0] * (1.0 - a) + self.WHITE[0] * a), 0, 255),
            clamp(int(base_color[1] * (1.0 - a) + self.WHITE[1] * a), 0, 255),
            clamp(int(base_color[2] * (1.0 - a) + self.WHITE[2] * a), 0, 255)
        )

        return blended_color

    def generate(self):
        """
        Generates the twilight wallpaper image based on the current state.
        """
        # Create base image with black background
        base_image = Image.new('RGBA', (self.width, self.height), self.BLACK)

        # Apply gradient
        gradient = self._create_gradient()
        base_image = Image.alpha_composite(base_image, gradient)

        # Draw stars
        base_image = self._draw_stars(base_image)

        # Finalize image
        self.image = base_image.convert('RGB')

    def get_image(self, reverse_y = True) -> Image.Image:
        """
        Returns the generated image.

        Returns:
        - PIL.Image.Image: The generated twilight wallpaper.
        """
        if self.image is None:
            self.generate()
        if reverse_y:
            return self.image.copy().transpose(Image.FLIP_TOP_BOTTOM)
        else:
            return self.image.copy()

    def save_image(self, filepath: str):
        """
        Saves the generated image to a file.

        Parameters:
        - filepath (str): The path to save the image.
        """
        if self.image:
            self.image.save(filepath)
        else:
            raise ValueError("No image generated to save.")

def interpolate_states(state1: TwilightState, state2: TwilightState, t: float, forward: bool = True) -> TwilightState:
    """
    Interpolates between two TwilightState instances based on t.

    Parameters:
    - state1 (TwilightState): Starting state.
    - state2 (TwilightState): Ending state.
    - t (float): Interpolation factor between 0 and 1.
    - forward (bool): Interpolation direction for cyclical attributes

    Returns:
    - TwilightState: Interpolated state.
    """
    new_state_kwargs = {}

    for attr in state1.to_dict():
        value1 = getattr(state1, attr)
        value2 = getattr(state2, attr)

        # Check if the attribute is cyclical
        if attr in TwilightState.CYCLICAL_ATTRIBUTES:
            cycle = TwilightState.CYCLICAL_ATTRIBUTES[attr]
            if forward:
                # Calculate forward delta
                delta = (value2 - value1) % cycle
                interpolated_value = (value1 + delta * t) % cycle
            else:
                # Calculate backward delta
                delta = (value1 - value2) % cycle
                interpolated_value = (value1 - delta * t) % cycle
        else:
            # Non-cyclical attribute: linear interpolation (Only interpolate if int or float)
            if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                interpolated_value = lerp(value1, value2, t)
                # Ensure integer attributes remain integers
                if isinstance(value1, int) and isinstance(value2, int):
                    interpolated_value = int(round(interpolated_value))
            else:
                interpolated_value = value1  # Retain value1 if not numeric

        new_state_kwargs[attr] = interpolated_value

    # Create a new TwilightState instance with interpolated values
    interpolated_state = TwilightState(**new_state_kwargs)
    return interpolated_state