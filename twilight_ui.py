import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QSlider, QComboBox, QPushButton,
                               QSpinBox, QListWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                               QFrame, QMessageBox)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, Signal, Slot, QObject

from twilight_generator import TwilightGenerator, TwilightState, interpolate_states
from twilight_animator import Keyframe, Timeline, TwilightAnimator, AnimationThread
from PIL import Image, ImageQt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

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
        self.image_label.setFixedSize(800, 450)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_layout.addWidget(self.image_label)

        # Parameter Controls
        self.parameter_group = QGroupBox("Parameters")
        self.parameter_layout = QFormLayout()

        # Time of Day
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 2400)  # We can use 0 to 2400 and divide by 100 to get 0.0 to 24.0
        self.time_slider.setValue(0)
        self.time_label = QLabel("Time of Day: 0.0")
        self.parameter_layout.addRow(self.time_label, self.time_slider)

        # Latitude
        self.latitude_slider = QSlider(Qt.Horizontal)
        self.latitude_slider.setRange(0, 3600)  # 0 to 360.0 degrees
        self.latitude_slider.setValue(0)
        self.latitude_label = QLabel("Latitude: 0.0")
        self.parameter_layout.addRow(self.latitude_label, self.latitude_slider)

        # Longitude
        self.longitude_slider = QSlider(Qt.Horizontal)
        self.longitude_slider.setRange(0, 3600)  # 0 to 360.0 degrees
        self.longitude_slider.setValue(0)
        self.longitude_label = QLabel("Longitude: 0.0")
        self.parameter_layout.addRow(self.longitude_label, self.longitude_slider)

        # Star Density
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(10, 500)  # Represents 0.1 to 5.0 after scaling
        self.density_slider.setValue(250)
        self.density_label = QLabel("Star Density: 2.5")
        self.parameter_layout.addRow(self.density_label, self.density_slider)

        # Transition Ratio
        self.transition_slider = QSlider(Qt.Horizontal)
        self.transition_slider.setRange(5, 50)  # Represents 0.05 to 0.5 after scaling
        self.transition_slider.setValue(20)
        self.transition_label = QLabel("Transition Ratio: 0.2")
        self.parameter_layout.addRow(self.transition_label, self.transition_slider)

        # Render Type
        self.render_combo = QComboBox()
        self.render_combo.addItems(['Flat', 'Spherical'])
        self.render_label = QLabel("Render Type:")
        self.parameter_layout.addRow(self.render_label, self.render_combo)

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
        self.fps_slider.setRange(1, 120)
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

        self.animation_group.setLayout(self.animation_layout)

        # Add controls to controls_layout
        self.controls_layout.addWidget(self.parameter_group)
        self.controls_layout.addLayout(self.seed_layout)
        self.controls_layout.addWidget(self.keyframe_group)
        self.controls_layout.addWidget(self.animation_group)

        # Add image and controls layouts to main_layout
        self.main_layout.addLayout(self.image_layout)
        self.main_layout.addLayout(self.controls_layout)

        # Initialize TwilightState and TwilightGenerator
        self.twilight_state = TwilightState()
        self.twilight_generator = TwilightGenerator(self.twilight_state)
        self.update_image()

        # Timeline and Keyframes storage
        self.timeline = Timeline([], framerate=30)

        # Animation thread
        self.animation_thread = None

        # Connect signals and slots
        self.setup_connections()

    def setup_connections(self):
        # Parameter controls
        self.time_slider.valueChanged.connect(self.on_input_changed)
        self.latitude_slider.valueChanged.connect(self.on_input_changed)
        self.longitude_slider.valueChanged.connect(self.on_input_changed)
        self.density_slider.valueChanged.connect(self.on_input_changed)
        self.transition_slider.valueChanged.connect(self.on_input_changed)
        self.render_combo.currentTextChanged.connect(self.on_input_changed)

        # Seed controls
        self.seed_apply_button.clicked.connect(self.on_seed_changed)

        # Keyframe management
        self.add_kf_button.clicked.connect(self.add_keyframe)
        self.remove_kf_button.clicked.connect(self.remove_keyframe)
        self.set_frame_button.clicked.connect(self.set_frame_for_selected_keyframe)
        self.kf_list_widget.itemSelectionChanged.connect(self.on_keyframe_selected)

        # Animation controls
        self.fps_slider.valueChanged.connect(self.on_fps_changed)
        self.play_button.clicked.connect(self.toggle_play)
        self.frame_slider.valueChanged.connect(self.on_frame_slider_changed)

    def on_input_changed(self):
        # Read all current parameter values from UI controls
        time_of_day = self.time_slider.value() / 100.0  # Since we used 0 to 2400
        latitude = self.latitude_slider.value() / 10.0  # 0 to 360.0 degrees
        longitude = self.longitude_slider.value() / 10.0
        star_density = self.density_slider.value() / 100.0  # 10 to 500, represents 0.1 to 5.0
        transition_ratio = self.transition_slider.value() / 100.0  # 5 to 50, represents 0.05 to 0.5
        render_type = self.render_combo.currentText().lower()

        # Update labels
        self.time_label.setText(f"Time of Day: {time_of_day:.2f}")
        self.latitude_label.setText(f"Latitude: {latitude:.1f}")
        self.longitude_label.setText(f"Longitude: {longitude:.1f}")
        self.density_label.setText(f"Star Density: {star_density:.2f}")
        self.transition_label.setText(f"Transition Ratio: {transition_ratio:.2f}")

        # Update TwilightState
        self.twilight_state.time_of_day = time_of_day
        self.twilight_state.latitude = latitude
        self.twilight_state.longitude = longitude
        self.twilight_state.star_density = star_density
        self.twilight_state.transition_ratio = transition_ratio
        self.twilight_state.render_type = render_type

        # Update render type for all keyframes
        for keyframe in self.timeline.keyframes:
            keyframe.state.render_type = render_type

        # Update TwilightGenerator's state
        self.twilight_generator.set_state(self.twilight_state)

        # Generate and display the new image
        self.update_image()

    def on_seed_changed(self):
        seed = self.seed_input.value()
        self.twilight_state.seed = seed

        # Reinitialize TwilightGenerator with new seed
        self.twilight_generator.set_state(self.twilight_state)

        # Generate and display the new image
        self.update_image()

    def update_image(self):
        self.twilight_generator.generate()
        image = self.twilight_generator.get_image()
        # Convert PIL Image to QImage
        qt_image = ImageQt.ImageQt(image)
        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(pixmap)

    def pil_image_to_qimage(self, pil_image):
        # Convert PIL image to QImage
        if pil_image.mode == "RGB":
            r, g, b = pil_image.split()
            pil_image = Image.merge("RGB", (r, g, b))
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format_RGB888)
            return qimage
        elif pil_image.mode == "RGBA":
            data = pil_image.convert("RGBA").tobytes("raw", "RGBA")
            qimage = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format_RGBA8888)
            return qimage
        else:
            raise NotImplementedError("Unsupported image mode: " + pil_image.mode)

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
        self.time_slider.setValue(int(keyframe.state.time_of_day * 100))
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
        if self.animation_thread and self.animation_thread.isRunning():
            # Need to restart animation thread with new framerate
            self.animation_thread.stop()
            self.animation_thread = AnimationThread(self.timeline, framerate=fps)
            self.animation_thread.animator.frame_generated.connect(self.update_frame, Qt.QueuedConnection)
            self.animation_thread.animator.animation_finished.connect(self.on_animation_finished, Qt.QueuedConnection)
            self.animation_thread.start()

    def toggle_play(self):
        if self.animation_thread and self.animation_thread.isRunning():
            self.animation_thread.stop()
            self.play_button.setText("Play")
        else:
            if len(self.timeline.keyframes) < 2:
                self.show_warning("At least two keyframes are required to start animation.")
                return
            self.timeline.framerate = self.fps_slider.value()
            self.animation_thread = AnimationThread(self.timeline)
            self.animation_thread.animator.frame_generated.connect(self.update_frame, Qt.QueuedConnection)
            self.animation_thread.animator.animation_finished.connect(self.on_animation_finished, Qt.QueuedConnection)
            self.animation_thread.start()
            self.play_button.setText("Pause")

    @Slot(int, TwilightState)
    def update_frame(self, frame_number, state):
        # Update TwilightGenerator's state
        self.twilight_generator.set_state(state)
        # Generate and display the new image
        self.update_image()
        # Update current frame label and frame slider
        self.current_frame_label.setText(f"Current Frame: {frame_number}")
        self.frame_slider.blockSignals(True)  # To prevent recursion
        self.frame_slider.setValue(frame_number)
        self.frame_slider.blockSignals(False)

    def on_animation_finished(self):
        self.play_button.setText("Play")

    def on_frame_slider_changed(self):
        frame_number = self.frame_slider.value()
        self.current_frame_label.setText(f"Current Frame: {frame_number}")
        state = self.timeline.get_state_at_frame(frame_number)
        if state:
            self.update_ui_from_state(state)
            if self.animation_thread and self.animation_thread.isRunning():
                self.animation_thread.animator.set_current_frame(frame_number)

    def update_ui_from_state(self, state):
        self.twilight_generator.set_state(state)
        self.update_image()
        self.block_ui_signals(True)
        self.time_slider.setValue(int(state.time_of_day * 100))
        self.latitude_slider.setValue(int(state.latitude * 10))
        self.longitude_slider.setValue(int(state.longitude * 10))
        self.density_slider.setValue(int(state.star_density * 100))
        self.transition_slider.setValue(int(state.transition_ratio * 100))
        render_type_index = self.render_combo.findText(state.render_type.capitalize())
        if render_type_index != -1:
            self.render_combo.setCurrentIndex(render_type_index)
        self.block_ui_signals(False)
        # self.update_labels_from_state(state) # TODO: Implement
        self.twilight_state = state.copy()

    def block_ui_signals(self, block):
        self.time_slider.blockSignals(block)
        self.latitude_slider.blockSignals(block)
        self.longitude_slider.blockSignals(block)
        self.density_slider.blockSignals(block)
        self.transition_slider.blockSignals(block)
        self.render_combo.blockSignals(block)

    def show_warning(self, message):
        QMessageBox.warning(self, "Warning", message)

    def closeEvent(self, event):
        if self.animation_thread and self.animation_thread.isRunning():
            self.animation_thread.stop()
            self.animation_thread.wait()
        event.accept()


if __name__ == "__main__":
    from PIL import Image  # Ensure PIL is imported
    app = QApplication(sys.argv)
    window = MainWindow()

    default_keyframes = [
        Keyframe(TwilightState(time_of_day=0.0, latitude=0.0, longitude=0.0, star_density=2.5, render_type='flat'), 0),
        Keyframe(TwilightState(time_of_day=12.0, latitude=45.0, longitude=180.0, star_density=5.0, render_type='flat'), 120),
        Keyframe(TwilightState(time_of_day=24.0, latitude=0.0, longitude=360.0, star_density=2.5, render_type='flat'), 240)
    ]
    for kf in default_keyframes:
        window.timeline.add_keyframe(kf)
    window.update_ui_from_state(window.timeline.keyframes[0].state)
    window.update_keyframes_list()
    window.update_frame_slider_range()
    window.show()
    sys.exit(app.exec())
