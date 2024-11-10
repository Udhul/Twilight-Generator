from twilight_generator import TwilightState, TwilightGenerator
from twilight_animator import TwilightAnimator
from PIL import Image
import os
import time

def generate_animation(output_dir = ''):
    # Define keyframes as a list of tuples (frame_number, TwilightState)
    keyframes = [
        (
            0,
            TwilightState(
                width=800,
                height=600,
                seed=12345,
                time_of_day=20.0,    # 8 PM
                star_density=3.0,
                transition_ratio=0.2,
                latitude=0.0,
                longitude=0.0,
                render_type='spherical'
            )
        ),
        (
            200,
            TwilightState(
                width=800,
                height=600,
                seed=12345,
                time_of_day=6.0,     # 6 AM
                star_density=1.0,
                transition_ratio=0.2,
                latitude=180.0,
                longitude=180.0,
                render_type='spherical'
            )
        ),
        (
            400,
            TwilightState(
                width=800,
                height=600,
                seed=12345,
                time_of_day=0.0,     # Midnight
                star_density=3.0,
                transition_ratio=0.2,
                latitude=360.0,      # Equivalent to 0.0 due to normalization
                longitude=360.0,     # Equivalent to 0.0 due to normalization
                render_type='spherical'
            )
        )
    ]

    # Initialize the animator with keyframes and direction 'forward'
    animator = TwilightAnimator(keyframes, direction='forward')

    # Initialize a TwilightGenerator (reused for efficiency)
    generator = TwilightGenerator(keyframes[0][1])

    # Iterate through interpolated states and generate images
    for frame_number, state in animator.sequence_generator():
        # Update generator with the new state
        generator.set_state(state)
        
        # Generate the image
        generator.generate()
        
        # Retrieve the image
        image = generator.get_image()
        
        # Save the image to a file
        # image_path = os.path.join(output_dir, f"frame_{frame_number:04d}.png")
        image_path = os.path.join(output_dir, f"frame.png")
        image.save(image_path)
        # print(f"Saved {image_path}")
        time.sleep(0.05)

    print("All frames have been generated and saved.")


def generate_single_image(output_dir = ''):
    # Define a twilight state
    state = TwilightState(
        width=1920,
        height=1080,
        seed=12345,
        time_of_day=18.0,  # 6 PM
        star_density=5.0,
        transition_ratio=0.25,
        latitude=45.0,
        longitude=90.0,
        render_type='spherical'
    )

    # Initialize the generator with the state
    generator = TwilightGenerator(state)

    # Generate the image
    generator.generate()

    # Retrieve the image
    image = generator.get_image()

    # Save the image to a file
    image_path = os.path.join(output_dir, 'twilight_render.png')
    image.save(image_path)

if __name__ == "__main__":
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    generate_single_image(output_dir)
    generate_animation(output_dir)