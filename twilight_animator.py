from twilight_generator import TwilightState
from utils import lerp, slerp
from PySide6.QtCore import QObject, QThread, Signal, Slot
import time


class TwilightAnimator(QObject):
    """
    Handles interpolation between TwilightState keyframes to generate animation sequences.
    Emits signals for each generated frame and when the animation finishes.
    """
    
    frame_generated = Signal(int, TwilightState)  # Signal emitting (frame_number, interpolated_state)
    animation_finished = Signal()  # Signal emitted when animation completes
    
    def __init__(self, keyframes, direction='forward', framerate=30):
        """
        Initializes the TwilightAnimator with keyframes, interpolation direction, and framerate.

        Parameters:
        - keyframes (list of tuples): Each tuple should be (frame_number (int), TwilightState).
        - direction (str): 'forward' or 'backward'. Determines interpolation direction for cyclical attributes.
        - framerate (int): Frames per second. Determines the delay between frame generations.
        """
        super().__init__()
        
        if not keyframes:
            raise ValueError("Keyframes list cannot be empty.")
        
        # Sort keyframes by frame number
        self.keyframes = sorted(keyframes, key=lambda kf: kf[0])
        
        # Check for duplicate frame numbers
        frames = [kf[0] for kf in self.keyframes]
        if len(frames) != len(set(frames)):
            raise ValueError("Duplicate frame numbers detected in keyframes.")
        
        # Validate direction
        self.direction = direction.lower()
        if self.direction not in ['forward', 'backward']:
            raise ValueError("Interpolation direction must be 'forward' or 'backward'.")
        
        # Validate framerate
        if not isinstance(framerate, (int, float)) or framerate <= 0:
            raise ValueError("Framerate must be a positive number.")
        self.framerate = framerate
        self.frame_delay = 1.0 / self.framerate  # Seconds per frame
        
        self._is_running = False  # Control flag for animation loop
        self._current_frame = self.keyframes[0][0]  # Initialize current frame

    @Slot()
    def run_animation(self):
        """
        Starts the animation sequence.
        This method should be run in a separate QThread.
        """
        self._is_running = True
        try:
            for frame_number, state in self.sequence_generator():
                if not self._is_running:
                    break
                self.frame_generated.emit(frame_number, state)
                time.sleep(self.frame_delay)
        finally:
            self._is_running = False
            self.animation_finished.emit()
    
    def stop_animation(self):
        """
        Stops the animation sequence.
        """
        self._is_running = False
    
    def set_current_frame(self, frame_number):
        """
        Sets the current frame to start the animation from.

        Parameters:
        - frame_number (int): The frame number to start from.
        """
        # Find the closest keyframe less than or equal to the desired frame
        for i, (kf_frame, _) in enumerate(self.keyframes):
            if kf_frame > frame_number:
                if i == 0:
                    self._current_frame = self.keyframes[0][0]
                else:
                    self._current_frame = self.keyframes[i-1][0]
                break
        else:
            # If frame_number is beyond the last keyframe
            self._current_frame = self.keyframes[-1][0]
    
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
                if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                    interpolated_value = lerp(value1, value2, t)
                else:
                    interpolated_value = value1  # Retain value1 if not numeric
            
            new_state_kwargs[attr] = interpolated_value
        
        # Create a new TwilightState instance with interpolated values
        interpolated_state = TwilightState(**new_state_kwargs)
        return interpolated_state
    

class AnimationThread(QThread):
    """
    QThread subclass to run TwilightAnimator in a separate thread.
    """
    def __init__(self, keyframes, direction='forward', framerate=30, parent=None):
        super().__init__(parent)
        self.keyframes = keyframes
        self.direction = direction
        self.framerate = framerate
        self.animator = TwilightAnimator(self.keyframes, self.direction, self.framerate)
    
    def run(self):
        """
        Overrides the run method to start the animation.
        """
        self.animator.run_animation()
    
    def stop(self):
        """
        Stops the animation and waits for the thread to finish.
        """
        self.animator.stop_animation()
        self.quit()
        self.wait()
    
    def set_current_frame(self, frame_number):
        """
        Sets the current frame of the animator.

        Parameters:
        - frame_number (int): The frame number to set.
        """
        self.animator.set_current_frame(frame_number)