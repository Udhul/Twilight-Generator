from twilight_generator import TwilightState, interpolate_states
from utils import lerp, slerp
from PySide6.QtCore import QObject, QThread, Signal, Slot
import time
from typing import List, Union, Optional


class Keyframe:
    def __init__(self, state: TwilightState, frame_number: int):
        """
        Initializes a Keyframe with a given TwilightState and frame number.

        Parameters:
        - state (TwilightState): The TwilightState associated with this keyframe.
        - frame_number (int): The frame number associated with this keyframe.
        """
        self.state = state
        self.frame_number = frame_number


class Timeline:
    def __init__(self, keyframes: List[Keyframe], framerate: Union[int,float] = 30, start_frame: int = None, end_frame: int = None):
        """
        Initializes a Timeline with a list of keyframes.

        Parameters:
        - keyframes (list of Keyframe): List of keyframes.
        - framerate (int, optional): The framerate of the animation. Defaults to 30.
        - start_frame (int, optional): The frame number to start the animation from. Defaults to the first keyframe.
        - end_frame (int, optional): The frame number to end the animation at. Defaults to the last keyframe.
        """
        keyframes = [kf for kf in keyframes if isinstance(kf, Keyframe)] # Filter out non-Keyframe objects
        self.keyframes:List[Keyframe] = keyframes.sort(key=lambda kf: kf.frame_number) # Sort ascending by frame number
        self.framerate = framerate
        self.start_frame = start_frame if start_frame is not None else keyframes[0].frame_number
        self.end_frame = end_frame if end_frame is not None else keyframes[-1].frame_number

    def add_keyframe(self, keyframe: Keyframe):
        """
        Adds a keyframe to the timeline. If a keyframe with the same frame number exists, it will be overwritten.
        
        Parameters:
        - keyframe (Keyframe): The keyframe to add or update
        """
        if not isinstance(keyframe, Keyframe):
            raise ValueError("Keyframe must be of type Keyframe")
            
        # Check if keyframe with same frame number exists and remove it
        for i, existing_kf in enumerate(self.keyframes):
            if existing_kf.frame_number == keyframe.frame_number:
                self.keyframes.pop(i)
                break
                
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda kf: kf.frame_number)

    def remove_keyframe(self, frame_number: int = None, index: int = None, keyframe: Keyframe = None):
        """
        Removes a keyframe from the timeline, identified by either frame_number, index or keyframe object. 
        """
        if isinstance(frame_number, int):
            for i, kf in enumerate(self.keyframes):
                if kf.frame_number == frame_number:
                    self.keyframes.pop(i)
                    return
                
        elif isinstance(index, int) and 0 <= index < len(self.keyframes):
            self.keyframes.pop(i)

        elif isinstance(keyframe, Keyframe) and keyframe in self.keyframes:
            self.keyframes.remove(keyframe)

    def get_state_at_frame(self, frame_number, keyframes: Optional[list[Keyframe]] = None) -> TwilightState:
        """
        Get the state at a specific frame number between keyframes.

        Parameters:
        - frame_number (int): The frame number to get the state for. Should be in the range between first and last keyframe
        - keyframes (list of Keyframe, optional): The list of keyframes to use. Defaults to the timeline's keyframes.

        Returns:
        - TwilightState: The state at the specified frame number.
        """
        # Prepare keyframes
        if keyframes is None:
            keyframes = self.keyframes
        else:
            keyframes = [kf for kf in keyframes if isinstance(kf, Keyframe)]
        if not keyframes:
            return None
        keyframes.sort(key=lambda kf: kf.frame_number)

        # If frame_number is before the first keyframe
        if frame_number <= keyframes[0].frame_number:
            return keyframes[0].state.copy()
        # If frame_number is after the last keyframe
        elif frame_number >= keyframes[-1][0]:
            return keyframes[-1].state.copy()

        # Find the two keyframes surrounding the frame_number
        for i in range(len(keyframes) - 1):
            start_frame, start_state = keyframes[i].frame_number, keyframes[i].state
            end_frame, end_state = keyframes[i + 1].frame_number, keyframes[i + 1].state
            
            # If frame_number is between start_frame and end_frame
            if start_frame <= frame_number <= end_frame:
                steps_between = end_frame - start_frame
                t = (frame_number - start_frame) / steps_between if steps_between > 0 else 0 # Get the interpolation factor
                interpolated_state = interpolate_states(start_state, end_state, t)
                return interpolated_state
        return None


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
            self.animation_finished.emit()
        finally:
            self._is_running = False

    def stop_animation(self):
        """
        Stops the animation sequence.
        """
        self._is_running = False

# TODO: FIX for actual interpolated frame
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
                    self._current_frame = self.keyframes[i - 1][0]
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
                continue  # Skip invalid keyframes

            # Number of frames to interpolate
            total_steps = end_frame - start_frame

            for step in range(total_steps):
                t = step / total_steps if total_steps > 0 else 1
                interpolated_state = interpolate_states(start_state, end_state, t)
                current_frame = start_frame + step
                yield (current_frame, interpolated_state)

        # Emit the last keyframe
        last_frame, last_state = self.keyframes[-1]
        yield (last_frame, last_state.copy())

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
        self.animator.moveToThread(self)

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