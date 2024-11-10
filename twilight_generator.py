import random
import math
from PIL import Image, ImageDraw, ImageQt
from utils import clamp, lerp, slerp

class TwilightState:
    """
    Encapsulates all state variables required for generating a twilight render.
    """

    # Define cyclical attributes and their cycle points
    CYCLICAL_ATTRIBUTES = {
        'time_of_day': 24.0,   # Cycles every 24 hours
        'latitude': 360.0,     # Cycles every 360 degrees
        'longitude': 360.0     # Cycles every 360 degrees
    }

    def __init__(self, 
                 width=1920, 
                 height=1080, 
                 seed=None,
                 time_of_day=0.0,  # Hour of the day (0-24)
                 star_density=1.0,  # Multiplier for number of stars
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
            self._star_density = clamp(value, 0.1, 5.0)
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
    def __init__(self, state: TwilightState):
        """
        Initializes the TwilightGenerator with a given TwilightState.

        Parameters:
        - state (TwilightState): The state containing all parameters for generation.
        """
        self.state = state
        self.width = state.width
        self.height = state.height
        self.seed = state.seed
        self.time_of_day = state.time_of_day
        self.star_density = state.star_density
        self.transition_ratio = state.transition_ratio
        self.latitude = state.latitude
        self.longitude = state.longitude
        self.render_type = state.render_type

        self.image = None
        self.draw = None

        # Base colors
        self.orange = (255, 72, 0)
        self.blue = (0, 110, 189)
        self.black = (0, 0, 0)
        self.white = (255, 255, 255)

        # Initialize random generator with seed
        self.random_gen = random.Random(self.seed)

        # Define maximum density
        self.max_density = 5.0

        # Base star counts
        self.base_small_stars = 2500
        self.base_big_stars = 200

        # Calculate scale factor based on dimensions
        scale_factor = (self.width * self.height) / (1920 * 1080)

        # Calculate total stars based on scale factor and max density
        self.total_small_stars = int(self.base_small_stars * scale_factor * self.max_density)
        self.total_big_stars = int(self.base_big_stars * scale_factor * self.max_density)

        # Define star size ranges
        size_min = max(1, int(self.width / 960))  # Ensures at least size 1
        size_max = max(2, int(self.width / 480))  # Ensures at least size 2

        # Pre-generate master star lists
        self.master_small_stars = [
            (self.random_gen.uniform(0, 1), self.random_gen.uniform(0, 1))
            for _ in range(self.total_small_stars)
        ]

        self.master_big_stars = [
            (self.random_gen.uniform(0, 1), self.random_gen.uniform(0, 1),
             self.random_gen.randint(size_min, size_max) / self.width)
            for _ in range(self.total_big_stars)
        ]

    def set_state(self, state: TwilightState):
        """
        Updates the generator with a new state.

        Parameters:
        - state (TwilightState): The new state to apply.
        """
        self.state = state
        self.width = state.width
        self.height = state.height
        self.seed = state.seed
        self.time_of_day = state.time_of_day
        self.star_density = state.star_density
        self.transition_ratio = state.transition_ratio
        self.latitude = state.latitude
        self.longitude = state.longitude
        self.render_type = state.render_type

        # Reinitialize random generator and stars if seed or star parameters change
        self.random_gen = random.Random(self.seed)

        # Re-generate master star lists based on new state
        self._initialize_stars()

    def _initialize_stars(self):
        """Re-initializes the star lists based on the current state."""
        # Re-generate master star lists
        self.master_small_stars = [
            (self.random_gen.uniform(0, 1), self.random_gen.uniform(0, 1))
            for _ in range(self.total_small_stars)
        ]

        self.master_big_stars = [
            (self.random_gen.uniform(0, 1), self.random_gen.uniform(0, 1),
             self.random_gen.randint(1, 2) / self.width)
            for _ in range(self.total_big_stars)
        ]

    def get_star_color(self, y):
        """
        Determines the color of a star based on its y-coordinate.

        Parameters:
        - y (float): The y-coordinate of the star in pixels.

        Returns:
        - Tuple of (r, g, b)
        """
        # y=0 is top, y=height is bottom
        ratio = y / self.height
        cutoff = self.transition_ratio

        # Stars should be drawn above the transition line
        if ratio < cutoff:
            # Transition from orange to blue
            t = (ratio) / cutoff
            r = int(lerp(self.orange[0], self.blue[0], t))
            g = int(lerp(self.orange[1], self.blue[1], t))
            b = int(lerp(self.orange[2], self.blue[2], t))
        else:
            # Upper half stars are white
            return self.white

        # Adjust brightness based on time_of_day (24-hour cycle)
        # 0 and 24 = darkest, 12 = brightest
        night_factor = -math.cos((self.time_of_day / 12.0) * math.pi) * 0.5 + 0.5  # Inverted

        # Adjust brightness based on night_factor
        r = int(r * night_factor)
        g = int(g * night_factor)
        b = int(b * night_factor)

        return (r, g, b)

    def generate(self):
        """
        Generates the twilight wallpaper image based on the current state.
        """
        # Create a new image with RGBA mode to support transparency for gradient
        self.image = Image.new('RGBA', (self.width, self.height), self.black)
        self.draw = ImageDraw.Draw(self.image)

        # Draw stars based on render_type
        if self.render_type == 'spherical':
            self._generate_stars_spherical()
        elif self.render_type == 'flat':
            self._generate_stars_flat()
        else:
            raise ValueError("Invalid render_type. Choose 'spherical' or 'flat'.")

        # Create and apply gradient overlay
        self._apply_gradient()

        # Flip the image vertically to correct orientation
        self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)

        # Convert to RGB after compositing
        self.image = self.image.convert('RGB')

    def _generate_stars_spherical(self):
        """Generates stars using spherical projection."""
        # Field of view settings
        fov = 30.0  # Field of view in degrees
        aspect_ratio = self.width / self.height
        fov_vertical = 2 * math.degrees(math.atan(math.tan(math.radians(fov / 2)) / aspect_ratio))

        # Convert longitude/latitude to radians
        lon_rad = math.radians(self.longitude)
        lat_rad = math.radians(self.latitude)

        # Draw small stars with spherical projection
        density_ratio = self.star_density / self.max_density
        total_small_stars_display = int(len(self.master_small_stars) * density_ratio)
        total_big_stars_display = int(len(self.master_big_stars) * density_ratio)

        for star in self.master_small_stars[:total_small_stars_display]:
            norm_x, norm_y = star

            # Convert normalized coordinates to spherical angles
            star_lon = norm_x * 2 * math.pi
            star_lat = (norm_y - 0.5) * math.pi

            # Calculate relative position from viewing angle
            dx = math.cos(star_lat) * math.sin(star_lon - lon_rad)
            dy = (math.cos(star_lat) * math.cos(star_lon - lon_rad) * math.sin(lat_rad)
                  - math.sin(star_lat) * math.cos(lat_rad))
            dz = (math.cos(star_lat) * math.cos(star_lon - lon_rad) * math.cos(lat_rad)
                  + math.sin(star_lat) * math.sin(lat_rad))

            # Project only visible stars (dz > 0 means in front of viewer)
            if dz > 0:
                # Convert to screen coordinates
                x = int(self.width * (0.5 + (dx / (2 * math.tan(math.radians(fov / 2))))))
                y = int(self.height * (0.5 + (dy / (2 * math.tan(math.radians(fov_vertical / 2))))))

                color = self.get_star_color(y)

                if 0 <= x < self.width and 0 <= y < self.height:
                    self.image.putpixel((x, y), color + (255,))

        # Draw big stars
        for star in self.master_big_stars[:total_big_stars_display]:
            norm_x, norm_y, norm_size = star

            star_lon = norm_x * 2 * math.pi
            star_lat = (norm_y - 0.5) * math.pi

            dx = math.cos(star_lat) * math.sin(star_lon - lon_rad)
            dy = (math.cos(star_lat) * math.cos(star_lon - lon_rad) * math.sin(lat_rad)
                  - math.sin(star_lat) * math.cos(lat_rad))
            dz = (math.cos(star_lat) * math.cos(star_lon - lon_rad) * math.cos(lat_rad)
                  + math.sin(star_lat) * math.sin(lat_rad))

            if dz > 0:
                x = int(self.width * (0.5 + (dx / (2 * math.tan(math.radians(fov / 2))))))
                y = int(self.height * (0.5 + (dy / (2 * math.tan(math.radians(fov_vertical / 2))))))
                size = int(norm_size * self.width)

                color = self.get_star_color(y)

                points = [
                    (x, y - size),
                    (x + size, y),
                    (x, y + size),
                    (x - size, y)
                ]
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.draw.polygon(points, fill=color + (255,))

    def _generate_stars_flat(self):
        """Generates stars using flat projection."""
        # Calculate shifts based on latitude and longitude
        longitude_shift = (self.longitude / 360.0) * self.width
        latitude_shift = (self.latitude / 360.0) * self.height

        # Calculate star visibility based on time of day
        night_factor = -math.cos((self.time_of_day / 12.0) * math.pi) * 0.5 + 1

        # Draw all stars with flat projection
        density_ratio = self.star_density / self.max_density
        total_small_stars_display = int(len(self.master_small_stars) * density_ratio)
        total_big_stars_display = int(len(self.master_big_stars) * density_ratio)

        # Draw small stars
        for star in self.master_small_stars[:total_small_stars_display]:
            norm_x, norm_y = star
            shifted_x = (norm_x * self.width + longitude_shift) % self.width
            shifted_y = (norm_y * self.height + latitude_shift) % self.height
            x = int(shifted_x)
            y = int(shifted_y)

            # Apply night_factor to star brightness
            color = tuple(int(c * night_factor) for c in self.white)

            if 0 <= x < self.width and 0 <= y < self.height:
                self.image.putpixel((x, y), color + (255,))

        # Draw big stars
        for star in self.master_big_stars[:total_big_stars_display]:
            norm_x, norm_y, norm_size = star
            shifted_x = (norm_x * self.width + longitude_shift) % self.width
            shifted_y = (norm_y * self.height + latitude_shift) % self.height
            x = int(shifted_x)
            y = int(shifted_y)
            size = int(norm_size * self.width)

            # Apply night_factor to star brightness
            color = tuple(int(c * night_factor) for c in self.white)

            points = [
                (x, y - size),
                (x + size, y),
                (x, y + size),
                (x - size, y)
            ]
            if 0 <= x < self.width and 0 <= y < self.height:
                self.draw.polygon(points, fill=color + (255,))

    def _apply_gradient(self):
        """Creates and applies the gradient overlay based on time of day."""
        gradient = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)

        # Calculate gradient position based on time of day
        # Move gradient up/down based on time - fully below view at night
        time_factor = math.sin((self.time_of_day / 24.0) * 2 * math.pi)
        gradient_offset = max(int(self.height * (1.0 + time_factor)), 0)
        
        # Make sure gradient does not exceed image boundaries
        gradient_offset = min(gradient_offset, self.height)

        for y in range(self.height):
            adjusted_y = y + gradient_offset
            if adjusted_y < 0 or adjusted_y >= self.height:
                continue

            ratio = adjusted_y / self.height
            orange_ratio = self.transition_ratio * 0.75  # Make orange portion 75% of transition area

            if ratio < orange_ratio:
                # Transition from orange to blue
                t = ratio / orange_ratio
                r = int(lerp(self.orange[0], self.blue[0], t))
                g = int(lerp(self.orange[1], self.blue[1], t))
                b = int(lerp(self.orange[2], self.blue[2], t))
                alpha = 255
            else:
                # Transition from blue to transparent
                t = (ratio - orange_ratio) / (1 - orange_ratio)
                t = clamp(t, 0.0, 1.0)
                r = int(lerp(self.blue[0], 0, t))
                g = int(lerp(self.blue[1], 0, t))
                b = int(lerp(self.blue[2], 0, t))
                alpha = int(255 * (1.0 - t))

            gradient_draw.line([(0, y), (self.width, y)], fill=(r, g, b, alpha))

        # Composite gradient over star field
        self.image = Image.alpha_composite(self.image, gradient)

    def get_image(self) -> Image.Image:
        """
        Returns the generated image.

        Returns:
        - PIL.Image.Image: The generated twilight wallpaper.
        """
        if self.image is None:
            self.generate()
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