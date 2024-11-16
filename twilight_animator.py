from twilight_generator import TwilightState, TwilightGenerator, interpolate_states
from utils import lerp, slerp
from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot
from PySide6.QtGui import QPixmap
from PIL import ImageQt
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
        self.framerate = framerate
        if not keyframes:
            self.keyframes = []
            self.start_frame = 0
            self.end_frame = 0
        else:
            self.keyframes:List[Keyframe] = keyframes
            self.start_frame = start_frame if start_frame is not None else keyframes[0].frame_number
            self.end_frame = end_frame if end_frame is not None else keyframes[-1].frame_number
        self.update()

    def update(self, reset_start_end: bool = True):
        """Validate and sort keyframes on timeline"""
        self.keyframes = [kf for kf in self.keyframes if isinstance(kf, Keyframe)] # Filter out non-Keyframe objects
        self.keyframes.sort(key=lambda kf: kf.frame_number) # Sort ascending by frame number
        if self.keyframes and reset_start_end:
            self.start_frame = self.keyframes[0].frame_number
            self.end_frame = self.keyframes[-1].frame_number

    def add_keyframe(self, keyframe: Keyframe):
        """
        Adds a keyframe to the timeline. If a keyframe with the same frame number exists, it will be overwritten.
        
        Parameters:
        - keyframe (Keyframe): The keyframe to add or update
        """
        if not isinstance(keyframe, Keyframe):
            raise ValueError("Keyframe must be of type Keyframe")
            
        # Check if keyframe with same frame number exists and remove it
        if self.keyframes:
            for i, existing_kf in enumerate(self.keyframes):
                if existing_kf.frame_number == keyframe.frame_number:
                    self.keyframes.pop(i)
                    break
                
        self.keyframes.append(keyframe)
        self.update()

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
            self.keyframes.pop(index)

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
        elif frame_number >= keyframes[-1].frame_number:
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

    def __init__(self, timeline: Timeline = None, direction='forward'):
        """
        Initializes the TwilightAnimator with a Timeline instance.

        Parameters:
        - timeline (Timeline): Timeline containing keyframes and framerate settings
        - direction (str): 'forward' or 'backward'. Determines interpolation direction for cyclical attributes.
        """
        super().__init__()

        self.timeline = timeline if timeline else Timeline([])
        
        # Validate direction
        self.direction = direction.lower()
        if self.direction not in ['forward', 'backward']:
            raise ValueError("Interpolation direction must be 'forward' or 'backward'.")

        self.frame_delay = 1.0 / self.timeline.framerate
        self._is_running = False
        self.next_frame = self.timeline.start_frame # Next frame number to be generated. Not last generated frame

    @Slot()
    def run_animation(self):
        """
        Starts the animation sequence.
        This method should be run in a separate QThread.
        """
        self._is_running = True
        try:
            self.frame_delay = 1.0 / self.timeline.framerate
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

    def set_current_frame(self, frame_number):
        """
        Sets the current frame to start the animation from.

        Parameters:
        - frame_number (int): The frame number to start from.
        """

        target_state = self.timeline.get_state_at_frame(frame_number)
        if target_state:
            self.next_frame = frame_number
            return target_state

    def sequence_generator(self):
        """
        Generator that yields interpolated TwilightState instances between keyframes on the timeline.

        Yields:
        - tuple: (frame_number (int), TwilightState instance)
        """
        while self.next_frame <= self.timeline.end_frame and self._is_running:
            state = self.timeline.get_state_at_frame(self.next_frame)
            if state:
                yield (self.next_frame, state)
            self.next_frame += 1

class AnimationThread(QThread):
    """
    QThread subclass to run TwilightAnimator in a separate thread.
    """

    def __init__(self, animator:TwilightAnimator = None, timeline: Timeline = None, direction='forward', parent=None):
        """
        Create a threaded animator. 
        If param animator given, it will be used. 
        Else a new animator is created from timeline and direction.
        """
        super().__init__(parent)

        if isinstance(animator, TwilightAnimator):
            self.animator = animator
        else:
            self.animator = TwilightAnimator(timeline, direction)
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

class TwilightGeneratorThread(QThread):
    image_ready = Signal(int, object, object)  # frame_number, state, image
    
    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height
        self.current_state = None
        self.next_state = None
        self.current_frame = 0
        self.next_frame = 0
        self.running = True
        self.generator = TwilightGenerator(TwilightState())
        # self.moveToThread(self)
        
    def set_state(self, frame_number, state):
        self.next_frame = frame_number
        self.next_state = state
        
    def run(self):
        while self.running:
            if self.next_state:
                # Take next state as current
                self.current_state = self.next_state
                self.current_frame = self.next_frame
                # Clear next state since we're processing it
                self.next_state = None
                
                # Generate image with current state
                self.generator.set_state(self.current_state)
                self.generator.generate()
                image = self.generator.get_image()
                
                # Convert PIL Image to QImage
                qt_image = ImageQt.ImageQt(image)
                pixmap = QPixmap.fromImage(qt_image)
                pixmap = pixmap.scaled(
                    self.width,
                    self.height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                # Emit the result
                self.image_ready.emit(self.current_frame, self.current_state, pixmap)
            else:
                # Sleep briefly if no work to do
                self.msleep(1)
                
    def stop(self):
        self.running = False