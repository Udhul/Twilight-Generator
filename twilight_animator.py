from twilight_generator import TwilightState
from utils import lerp, slerp
from PySide6.QtCore import QObject, Signal, Slot, QThread

class TwilightAnimator:
    """
    Handles interpolation between TwilightState keyframes to generate animation sequences.
    """

    def __init__(self, keyframes, direction='forward'):
        """
        Initializes the TwilightAnimator with keyframes and interpolation direction.

        Parameters:
        - keyframes (list of tuples): Each tuple should be (frame_number (int), TwilightState).
        - direction (str): 'forward' or 'backward'. Determines interpolation direction for cyclical attributes.
        """
        if not keyframes:
            raise ValueError("Keyframes list cannot be empty.")
        
        # Validate and sort keyframes by frame number
        self.keyframes = sorted(keyframes, key=lambda kf: kf[0])
        
        # Check for duplicate frame numbers
        frames = [kf[0] for kf in self.keyframes]
        if len(frames) != len(set(frames)):
            raise ValueError("Duplicate frame numbers detected in keyframes.")
        
        # Validate direction
        self.direction = direction.lower()
        if self.direction not in ['forward', 'backward']:
            raise ValueError("Interpolation direction must be 'forward' or 'backward'.")
    
    def sequence_generator(self):
        """
        Generator that yields interpolated TwilightState instances between keyframes.

        Yields:
        - tuple: (frame_number (int), TwilightState instance)
        """
        num_keyframes = len(self.keyframes)
        for i in range(num_keyframes - 1):
            start_frame, start_state = self.keyframes[i]
            end_frame, end_state = self.keyframes[i + 1]
            
            if end_frame <= start_frame:
                raise ValueError("Keyframes must have increasing frame numbers.")
            
            # Number of frames to interpolate
            total_steps = end_frame - start_frame
            
            for step in range(total_steps + 1):
                t = step / total_steps if total_steps > 0 else 1
                interpolated_state = self.interpolate_between(start_state, end_state, t)
                current_frame = start_frame + step
                yield (current_frame, interpolated_state)
    
    def interpolate_between(self, state1: TwilightState, state2: TwilightState, t: float) -> TwilightState:
        """
        Interpolates between two TwilightState instances based on t.

        Parameters:
        - state1 (TwilightState): Starting state.
        - state2 (TwilightState): Ending state.
        - t (float): Interpolation factor between 0 and 1.

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
                if self.direction == 'forward':
                    # Calculate forward delta
                    delta = (value2 - value1) % cycle
                    interpolated_value = (value1 + delta * t) % cycle
                elif self.direction == 'backward':
                    # Calculate backward delta
                    delta = (value1 - value2) % cycle
                    interpolated_value = (value1 - delta * t) % cycle
            else:
                # Non-cyclical attribute: linear interpolation (Only interpolate if int or float)
                if not isinstance(value1, (int, float)):
                    interpolated_value = value1
                else:
                    interpolated_value = lerp(value1, value2, t)
            
            new_state_kwargs[attr] = interpolated_value
        
        # Create a new TwilightState instance with interpolated values
        interpolated_state = TwilightState(**new_state_kwargs)
        return interpolated_state