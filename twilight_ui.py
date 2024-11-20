import sys
from PIL import ImageQt

from twilight_generator import TwilightGenerator, TwilightState
from twilight_animator import Keyframe, Timeline, TwilightAnimator, AnimationThread, TwilightGeneratorThread

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QSlider, QComboBox, QPushButton,
                               QSpinBox, QListWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                               QFrame, QMessageBox, QFileDialog, QProgressDialog) 
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup UI elements
        self.setup_ui()

        # Initialize TwilightState and TwilightGenerator
        self.generator_thread = TwilightGeneratorThread()
        self.generator_thread.image_ready.connect(self.on_image_ready)
        self.generator_thread.start()

        # Timeline and Keyframes storage
        self.timeline = Timeline([], framerate=30)
        self.last_generated_frame = 0

        # Animator and Animation thread
        self.animator = TwilightAnimator(self.timeline, direction="forward")
        self.animation_thread = AnimationThread(self.animator)
        self.animator.frame_generated.connect(self.on_frame_generated, Qt.QueuedConnection)
        self.animator.animation_finished.connect(self.on_animation_finished, Qt.QueuedConnection)

        # Connect signals and slots
        self.setup_connections()

        # Trigger input change for initial state and image generation
        self.on_input_changed()

    def setup_ui(self):
        self.setWindowTitle("Twilight Wallpaper Controller")

        # Create the main widget and set it as central widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # Initialize layouts
        self.main_layout = QHBoxLayout(self.main_widget)
        self.controls_layout = QVBoxLayout()
        self.image_layout = QVBoxLayout()

        # Image Display Area
        self.image_label = QLabel()
        self.image_label.setFixedSize(960,540)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_layout.addWidget(self.image_label)

        # Parameter Controls
        self.parameter_group = QGroupBox("Parameters")
        self.parameter_layout = QFormLayout()

        # Time of Day
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 240)
        self.time_slider.setValue(0)
        self.time_slider.setTickPosition(QSlider.TicksBelow)
        self.time_slider.setTickInterval(10)
        self.time_label = QLabel("Time of Day: 0.0")
        self.parameter_layout.addRow(self.time_label, self.time_slider)

        # Latitude
        self.latitude_slider = QSlider(Qt.Horizontal)
        self.latitude_slider.setRange(0, 3600)  # 0 to 360.0 degrees
        self.latitude_slider.setValue(0)
        self.latitude_slider.setTickPosition(QSlider.TicksBelow)
        self.latitude_slider.setTickInterval(300)  # Ticks every 30 degrees
        self.latitude_label = QLabel("Latitude: 0.0")
        self.parameter_layout.addRow(self.latitude_label, self.latitude_slider)

        # Longitude
        self.longitude_slider = QSlider(Qt.Horizontal)
        self.longitude_slider.setRange(0, 3600)  # 0 to 360.0 degrees
        self.longitude_slider.setValue(0)
        self.longitude_slider.setTickPosition(QSlider.TicksBelow)
        self.longitude_slider.setTickInterval(300)  # Ticks every 30 degrees
        self.longitude_label = QLabel("Longitude: 0.0")
        self.parameter_layout.addRow(self.longitude_label, self.longitude_slider)

        # Star Density
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(0, 100)
        self.density_slider.setValue(50)
        # self.density_slider.setSingleStep(5)
        self.density_slider.setTickPosition(QSlider.TicksBelow)
        self.density_slider.setTickInterval(5)  # Ticks every 0.5 density units
        self.density_label = QLabel("Star Density: 0.5")
        self.parameter_layout.addRow(self.density_label, self.density_slider)

        # Transition Ratio
        self.transition_slider = QSlider(Qt.Horizontal)
        self.transition_slider.setRange(5, 50)
        self.transition_slider.setValue(20)
        self.transition_slider.setTickPosition(QSlider.TicksBelow)
        self.transition_slider.setTickInterval(5)  # Ticks every 0.05 units
        self.transition_label = QLabel("Transition Ratio: 0.2")
        self.parameter_layout.addRow(self.transition_label, self.transition_slider)

        # Render Type
        self.render_combo = QComboBox()
        self.render_combo.addItems(['Flat', 'Spherical'])
        self.render_label = QLabel("Render Type:")
        self.parameter_layout.addRow(self.render_label, self.render_combo)

        # Image Size
        self.width_input = QSpinBox()
        self.width_input.setRange(640, 3840)
        self.width_input.setSingleStep(64)
        self.width_input.setValue(1280)
        self.height_input = QSpinBox()
        self.height_input.setRange(480, 2160)
        self.height_input.setSingleStep(64)
        self.height_input.setValue(720)
        self.parameter_layout.addRow("Width:", self.width_input)
        self.parameter_layout.addRow("Height:", self.height_input)

        self.parameter_group.setLayout(self.parameter_layout)

        # Seed Controls
        self.seed_layout = QHBoxLayout()
        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 1000000)
        self.seed_input.setValue(12345)
        self.seed_apply_button = QPushButton("Apply Seed")
        self.seed_layout.addWidget(QLabel("Seed:"))
        self.seed_layout.addWidget(self.seed_input)
        self.seed_layout.addWidget(self.seed_apply_button)

        # Keyframe Management
        self.keyframe_group = QGroupBox("Keyframes")
        self.keyframe_layout = QVBoxLayout()

        self.kf_frame_input = QSpinBox()
        self.kf_frame_input.setRange(0, 10000)
        self.kf_frame_input.setValue(0)
        self.add_kf_button = QPushButton("Add/Update Keyframe")
        self.remove_kf_button = QPushButton("Remove Keyframe")
        self.set_frame_button = QPushButton("Set Frame for Selected Keyframe")
        self.kf_list_widget = QListWidget()

        self.keyframe_layout.addWidget(QLabel("Frame Number:"))
        self.keyframe_layout.addWidget(self.kf_frame_input)
        self.keyframe_layout.addWidget(self.add_kf_button)
        self.keyframe_layout.addWidget(self.remove_kf_button)
        self.keyframe_layout.addWidget(self.set_frame_button)
        self.keyframe_layout.addWidget(self.kf_list_widget)

        self.keyframe_group.setLayout(self.keyframe_layout)

        # Animation Controls
        self.animation_group = QGroupBox("Animation")
        self.animation_layout = QVBoxLayout()

        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setRange(1, 60)
        self.fps_slider.setValue(30)
        self.fps_value_label = QLabel("Framerate: 30 FPS")
        self.play_button = QPushButton("Play")
        self.current_frame_label = QLabel("Current Frame: 0")
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setRange(0, 10000)
        self.frame_slider.setValue(0)

        self.animation_layout.addWidget(self.fps_value_label)
        self.animation_layout.addWidget(self.fps_slider)
        self.animation_layout.addWidget(self.play_button)
        self.animation_layout.addWidget(self.current_frame_label)
        self.animation_layout.addWidget(self.frame_slider)

        self.save_animation_button = QPushButton("Save Animation")
        self.animation_layout.addWidget(self.save_animation_button)

        self.animation_group.setLayout(self.animation_layout)

        # Add controls to controls_layout
        self.controls_layout.addWidget(self.parameter_group)
        self.controls_layout.addLayout(self.seed_layout)
        self.controls_layout.addWidget(self.keyframe_group)
        self.controls_layout.addWidget(self.animation_group)

        # Add image and controls layouts to main_layout
        self.main_layout.addLayout(self.image_layout)
        self.main_layout.addLayout(self.controls_layout)

    def setup_connections(self):
        # Parameter controls
        self.time_slider.valueChanged.connect(self.on_input_changed)
        self.latitude_slider.valueChanged.connect(self.on_input_changed)
        self.longitude_slider.valueChanged.connect(self.on_input_changed)
        self.density_slider.valueChanged.connect(self.on_input_changed)
        self.transition_slider.valueChanged.connect(self.on_input_changed)
        self.render_combo.currentTextChanged.connect(self.on_input_changed)
        self.seed_apply_button.clicked.connect(self.on_input_changed)
        self.width_input.valueChanged.connect(self.on_input_changed)
        self.height_input.valueChanged.connect(self.on_input_changed)

        # Keyframe management
        self.add_kf_button.clicked.connect(self.add_keyframe)
        self.remove_kf_button.clicked.connect(self.remove_keyframe)
        self.set_frame_button.clicked.connect(self.set_frame_for_selected_keyframe)
        self.kf_list_widget.itemSelectionChanged.connect(self.on_keyframe_selected)

        # Animation controls
        self.fps_slider.valueChanged.connect(self.on_fps_changed)
        self.play_button.clicked.connect(self.toggle_play)
        self.frame_slider.valueChanged.connect(self.on_frame_slider_changed)
        self.save_animation_button.clicked.connect(self.save_animation)

    def on_input_changed(self):
        # Read all current parameter values from UI controls
        width = self.width_input.value()
        height = self.height_input.value()
        seed = self.seed_input.value()
        star_density = self.density_slider.value() / 100.0  # 0 to 100, represents 0.0 to 1.0
        transition_ratio = self.transition_slider.value() / 100.0  # 5 to 50, represents 0.05 to 0.5
        time_of_day = self.time_slider.value() / 10.0
        latitude = self.latitude_slider.value() / 10.0  # 0 to 360.0 degrees
        longitude = self.longitude_slider.value() / 10.0
        render_type = self.render_combo.currentText().lower()
        fps = self.fps_slider.value()

        # Update labels
        self.update_labels()

        if not hasattr(self, 'twilight_state'):
            self.twilight_state = TwilightState()

        # Update TwilightState
        self.twilight_state.width = width
        self.twilight_state.height = height
        self.twilight_state.seed = seed
        self.twilight_state.time_of_day = time_of_day
        self.twilight_state.star_density = star_density
        self.twilight_state.transition_ratio = transition_ratio
        self.twilight_state.latitude = latitude
        self.twilight_state.longitude = longitude
        self.twilight_state.render_type = render_type
        self.timeline.framerate = fps

        # Update render type for all keyframes
        for keyframe in self.timeline.keyframes:
            keyframe.state.width = width
            keyframe.state.height = height
            keyframe.state.seed = seed
            keyframe.state.render_type = render_type

        # Update TwilightGenerator's state. Wil emit a signal when done, which will update the image and ui
        self.generator_thread.set_state(self.frame_slider.value(), self.twilight_state)

    def add_keyframe(self):
        frame_number = self.kf_frame_input.value()
        state_copy = self.twilight_state.copy()
        new_keyframe = Keyframe(state_copy, frame_number)
        self.timeline.add_keyframe(new_keyframe)
        self.update_keyframes_list()
        self.update_frame_slider_range()

    def update_keyframes_list(self):
        self.kf_list_widget.clear()
        for keyframe in self.timeline.keyframes:
            state = keyframe.state
            item_text = f"Frame {keyframe.frame_number}: Time={state.time_of_day:.2f}, Lat={state.latitude:.1f}, Lon={state.longitude:.1f}, Density={state.star_density:.2f}, Transition={state.transition_ratio:.2f}"
            self.kf_list_widget.addItem(item_text)

    def update_frame_slider_range(self):
        if self.timeline.keyframes:
            self.frame_slider.setRange(self.timeline.start_frame, self.timeline.end_frame)
        else:
            self.frame_slider.setRange(0, 10000)

    def remove_keyframe(self):
        selected_items = self.kf_list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            index = self.kf_list_widget.row(item)
            self.timeline.remove_keyframe(index=index)
        # Update keyframes list widget
        self.update_keyframes_list()
        # Update frame slider range
        self.update_frame_slider_range()

    def set_frame_for_selected_keyframe(self):
        selected_items = self.kf_list_widget.selectedItems()
        if not selected_items:
            return
        frame_number = self.kf_frame_input.value()
        item = selected_items[0]
        index = self.kf_list_widget.row(item)
        # Update the frame number for the selected keyframe
        self.timeline.keyframes[index].frame_number = frame_number
        self.timeline.update() # Sort
        # Update keyframes list widget
        self.update_keyframes_list()
        # Update frame slider range
        self.update_frame_slider_range()

    def on_keyframe_selected(self):
        selected_items = self.kf_list_widget.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        index = self.kf_list_widget.row(item)
        keyframe = self.timeline.keyframes[index]
        # Update UI controls with state parameters
        self.kf_frame_input.setValue(keyframe.frame_number)
        # Update sliders
        self.block_ui_signals(True)
        self.time_slider.setValue(int(keyframe.state.time_of_day * 10))
        self.latitude_slider.setValue(int(keyframe.state.latitude * 10))
        self.longitude_slider.setValue(int(keyframe.state.longitude * 10))
        self.density_slider.setValue(int(keyframe.state.star_density * 100))
        self.transition_slider.setValue(int(keyframe.state.transition_ratio * 100))
        render_type_index = self.render_combo.findText(keyframe.state.render_type.capitalize())
        if render_type_index != -1:
            self.render_combo.setCurrentIndex(render_type_index)
        self.frame_slider.setValue(int(keyframe.frame_number))
        self.block_ui_signals(False)
        # Update labels (this will also update the TwilightState and image)
        self.on_input_changed()

    def on_fps_changed(self):
        fps = self.fps_slider.value()
        self.fps_value_label.setText(f"Framerate: {fps} FPS")
        if self.animation_thread:
            if self.animation_thread.isRunning():
                self.animation_thread.stop()
                self.timeline.framerate = fps
                self.animator.set_current_frame(self.frame_slider.value())
                self.animation_thread.start()
            else:
                self.timeline.framerate = fps
                self.animator.set_current_frame(self.frame_slider.value())

    def toggle_play(self):
        if self.animation_thread and self.animation_thread.isRunning():
            self.animation_thread.stop()
            self.play_button.setText("Play")
        else:
            if len(self.timeline.keyframes) < 2:
                self.show_warning("At least two keyframes are required to start animation.")
                return
            if self.frame_slider.value() >= self.timeline.end_frame:
                self.frame_slider.setValue(self.timeline.start_frame)
            self.timeline.framerate = self.fps_slider.value()
            self.animator.set_current_frame(self.frame_slider.value())
            self.play_button.setText("Pause")
            self.animation_thread.start()

    @Slot(int, object, object)
    def on_image_ready(self, frame_number, state, image):
        # Convert PIL Image to QImage and QPixmap at original dimensions
        qt_image = ImageQt.ImageQt(image)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Calculate scaling ratios
        width_ratio = self.image_label.width() / pixmap.width()
        height_ratio = self.image_label.height() / pixmap.height()
        scale_ratio = min(width_ratio, height_ratio)
        
        # Scale image maintaining aspect ratio
        new_width = int(pixmap.width() * scale_ratio)
        new_height = int(pixmap.height() * scale_ratio)
        
        scaled_pixmap = pixmap.scaled(new_width, new_height,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        
        # Center the image in the label
        x_offset = (self.image_label.width() - new_width) // 2
        y_offset = (self.image_label.height() - new_height) // 2
        
        # Create background pixmap
        result_pixmap = QPixmap(self.image_label.size())
        result_pixmap.fill(Qt.GlobalColor.black)
        
        # Paint scaled image onto centered background
        painter = QPainter(result_pixmap)
        painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
        painter.end()
        
        self.image_label.setPixmap(result_pixmap)
        self.update_ui_from_state(state, frame_number)

    @Slot(int, TwilightState)
    def on_frame_generated(self, frame_number, state):
        """Bridge over to self.generator_thread.set_state(). No additional actions as of now."""
        # # Update UI which updates TwilightGenerator's state and renders image
        # self.update_ui_from_state(state=state, frame_number=frame_number)
        self.generator_thread.set_state(frame_number, state)

    def on_animation_finished(self):
        self.play_button.setText("Play")

    def on_frame_slider_changed(self):
        frame_number = self.frame_slider.value()
        self.current_frame_label.setText(f"Current Frame: {frame_number}")
        state = self.timeline.get_state_at_frame(frame_number)
        if state:
            if not self.animation_thread.isRunning():
                self.generator_thread.set_state(frame_number, state)
            self.animator.set_current_frame(frame_number)
        else:
            print(f"No state found for frame {frame_number}")

    def update_labels(self):
        # Get values from sliders
        time_of_day = self.time_slider.value() / 10.0
        latitude = self.latitude_slider.value() / 10.0
        longitude = self.longitude_slider.value() / 10.0
        star_density = self.density_slider.value() / 100.0
        transition_ratio = self.transition_slider.value() / 100.0
        frame_number = self.frame_slider.value()
        fps = self.fps_slider.value()

        # Update all labels with formatted values
        self.time_label.setText(f"Time of Day: {time_of_day:.2f}")
        self.latitude_label.setText(f"Latitude: {latitude:.1f}")
        self.longitude_label.setText(f"Longitude: {longitude:.1f}")
        self.density_label.setText(f"Star Density: {star_density:.2f}")
        self.transition_label.setText(f"Transition Ratio: {transition_ratio:.2f}")
        self.current_frame_label.setText(f"Current Frame: {frame_number}")
        self.fps_value_label.setText(f"Framerate: {fps} FPS")

        # Animation
        if self.animation_thread and self.animation_thread.isRunning():
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play")

    def update_ui_from_state(self, state = None, frame_number = None):
        '''If state give, set it as current state. Else use the already set state. 
        If frame_number is given, set it as current frame. Else use self.last_generated_frame.
        When giving as argument, frame number should correspond to state.'''
        # If state is not given, use the already set state
        if isinstance(state, TwilightState):
            self.twilight_state = state
        else:
            state = self.twilight_state

        # If frame_number is not given, use the already set frame_number
        if frame_number is not None:
            self.last_generated_frame = frame_number
        else:
            frame_number = self.last_generated_frame

        # Update UI controls with state parameters
        self.block_ui_signals(True)
        self.time_slider.setValue(int(state.time_of_day * 10))
        self.latitude_slider.setValue(int(state.latitude * 10))
        self.longitude_slider.setValue(int(state.longitude * 10))
        self.density_slider.setValue(int(state.star_density * 100))
        self.transition_slider.setValue(int(state.transition_ratio * 100))
        render_type_index = self.render_combo.findText(state.render_type.capitalize())
        if render_type_index != -1:
            self.render_combo.setCurrentIndex(render_type_index)
        self.current_frame_label.setText(f"Current Frame: {frame_number}")
        self.frame_slider.setValue(frame_number)
        self.block_ui_signals(False)

        # Update labels
        self.update_labels()

    def block_ui_signals(self, block):
        self.time_slider.blockSignals(block)
        self.latitude_slider.blockSignals(block)
        self.longitude_slider.blockSignals(block)
        self.density_slider.blockSignals(block)
        self.transition_slider.blockSignals(block)
        self.render_combo.blockSignals(block)
        self.frame_slider.blockSignals(block)

    def show_warning(self, message):
        QMessageBox.warning(self, "Warning", message)

    def save_animation(self):
        if len(self.timeline.keyframes) < 2:
            self.show_warning("At least two keyframes are required to save animation.")
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Animation",
            "",
            "MP4 files (*.mp4);;GIF files (*.gif)"
        )
        
        if not file_path:
            return
        
        # Determine format from selected filter
        is_mp4 = "MP4" in selected_filter
        if is_mp4 and not file_path.endswith('.mp4'):
            file_path += '.mp4'
        elif not is_mp4 and not file_path.endswith('.gif'):
            file_path += '.gif'

        frames = []
        fps = self.timeline.framerate
        duration = int(1000 / fps)
        total_frames = self.timeline.end_frame - self.timeline.start_frame + 1
        
        # Create progress dialog
        progress = QProgressDialog("Generating animation frames...", "Cancel", 0, total_frames, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Saving Animation")
        progress.setMinimumDuration(0)
        
        # Generate each frame
        for frame in range(self.timeline.start_frame, self.timeline.end_frame + 1):
            if progress.wasCanceled():
                return
                
            state = self.timeline.get_state_at_frame(frame)
            if state:
                generator = TwilightGenerator(state)
                frames.append(generator.get_image())
                
                current_frame = frame - self.timeline.start_frame + 1
                progress.setValue(current_frame)
                progress.setLabelText(f"Generating frame {current_frame} of {total_frames}")
        
        # Before saving, update progress dialog for save phase
        progress.setLabelText("Saving animation to file...")
        progress.setCancelButton(None)
        progress.show()
        QApplication.processEvents()
        
        if is_mp4:
            import tempfile
            import os
            import subprocess
            import shutil
            def get_ffmpeg_path():
                """Get the path to the ffmpeg executable."""
                # Check in PATH
                ffmpeg_in_path = shutil.which('ffmpeg')
                if ffmpeg_in_path:
                    return ffmpeg_in_path
                    
                # Check in current working directory
                if os.path.exists('ffmpeg'):
                    return './ffmpeg'
                if os.path.exists('ffmpeg.exe'):
                    return './ffmpeg.exe'
                    
                # Check in program directory
                program_dir = os.path.dirname(os.path.abspath(__file__))
                if os.path.exists(os.path.join(program_dir, 'ffmpeg')):
                    return os.path.join(program_dir, 'ffmpeg')
                if os.path.exists(os.path.join(program_dir, 'ffmpeg.exe')):
                    return os.path.join(program_dir, 'ffmpeg.exe')
                    
                return None

            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                QMessageBox.warning(
                    self,
                    "FFmpeg Required",
                    "FFmpeg is required to create MP4 files.\nPlease install FFmpeg and make sure it's available in your system PATH."
                )
                return
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save frames as PNGs
                for i, frame in enumerate(frames):
                    frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    frame.save(frame_path)
                
                # Use ffmpeg with correct path to create MP4
                ffmpeg_cmd = [
                    ffmpeg_path,
                    '-y',
                    '-framerate', str(fps),
                    '-i', os.path.join(temp_dir, 'frame_%04d.png'),
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-crf', '23',
                    file_path
                ]
                subprocess.run(ffmpeg_cmd, check=True)
        else:
            # Save as GIF
            frames[0].save(
                file_path,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=0
            )
        
        # progress.close()
        progress.setRange(0,1)
        progress.setWindowTitle("Done!")
        progress.setLabelText("Done!")
        QTimer.singleShot(1000, progress.close)

    def closeEvent(self, event):
        if self.animation_thread and self.animation_thread.isRunning():
            self.animation_thread.stop()
            self.animation_thread.wait()
        self.generator_thread.stop()
        self.generator_thread.wait()
        event.accept()


if __name__ == "__main__":
    from PIL import Image  # Ensure PIL is imported
    app = QApplication(sys.argv)
    window = MainWindow()

    default_seed = 12345
    default_width = 1280
    default_height = 720
    default_keyframes = [
        Keyframe(TwilightState(width=default_width, height=default_height, seed=default_seed, time_of_day=0.0, latitude=0.0, longitude=0.0, star_density=1.0, render_type='flat'), 0),
        Keyframe(TwilightState(width=default_width, height=default_height, seed=default_seed, time_of_day=12.0, latitude=45.0, longitude=180.0, star_density=0.5, render_type='flat'), 120),
        Keyframe(TwilightState(width=default_width, height=default_height, seed=default_seed, time_of_day=24.0, latitude=0.0, longitude=360.0, star_density=1.0, render_type='flat'), 240)
    ]
    for kf in default_keyframes:
        window.timeline.add_keyframe(kf)
    window.update_ui_from_state(window.timeline.keyframes[0].state)
    window.update_keyframes_list()
    window.update_frame_slider_range()
    window.show()

    # Center the window on the screen
    screen = QApplication.primaryScreen().geometry()
    x = (screen.width() - window.width()) // 2
    y = (screen.height() - window.height()) // 2
    window.move(x, y)

    # Start the event loop
    sys.exit(app.exec())
