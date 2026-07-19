from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .settings import DEFAULT_SETTINGS, save_settings
from .scheduling import TICKS_PER_SECOND


SPRITE_ASPECT_RATIO = 85 / 110


def ticks_to_minutes(ticks: int) -> int:
    seconds = int(ticks) / TICKS_PER_SECOND
    minutes = round(seconds / 60)
    return max(1, minutes)


def minutes_to_ticks(minutes: int) -> int:
    return int(minutes) * 60 * TICKS_PER_SECOND


class NomzySettingsWindow(QWidget):
    def __init__(self, settings: dict, on_save):
        super().__init__()

        self.settings = dict(settings)
        self.on_save = on_save

        self.setWindowTitle("Nomzy Settings")
        self.setMinimumWidth(380)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self.size_label = QLabel()
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(60)
        self.size_slider.setMaximum(180)
        self.size_slider.valueChanged.connect(self.update_size_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("friend")

        self.walk_interval_input = QSpinBox()
        self.walk_interval_input.setMinimum(5)
        self.walk_interval_input.setMaximum(300)
        self.walk_interval_input.setSuffix(" sec")

        self.speech_min_input = QSpinBox()
        self.speech_min_input.setMinimum(1)
        self.speech_min_input.setMaximum(120)
        self.speech_min_input.setSuffix(" min")

        self.speech_max_input = QSpinBox()
        self.speech_max_input.setMinimum(1)
        self.speech_max_input.setMaximum(120)
        self.speech_max_input.setSuffix(" min")

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666666;")

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)

        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self.reset_defaults)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.hide)

        form = QFormLayout()
        form.addRow("Your name:", self.name_input)
        form.addRow("Nomzy size:", self.size_slider)
        form.addRow("", self.size_label)
        form.addRow("Walk about every:", self.walk_interval_input)
        form.addRow("Speak at least every:", self.speech_min_input)
        form.addRow("Speak at most every:", self.speech_max_input)

        button_row = QHBoxLayout()
        button_row.addWidget(reset_button)
        button_row.addStretch()
        button_row.addWidget(save_button)
        button_row.addWidget(close_button)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Customize Nomzy"))
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addLayout(button_row)

        self.setLayout(layout)
        self.load_values(self.settings)

    def load_values(self, settings: dict):
        self.settings = dict(settings)

        self.name_input.setText(str(self.settings.get("user_name", "")))

        self.size_slider.setValue(
            int(self.settings.get("sprite_width", DEFAULT_SETTINGS["sprite_width"]))
        )

        self.walk_interval_input.setValue(
            int(
                self.settings.get(
                    "walk_interval_seconds",
                    DEFAULT_SETTINGS["walk_interval_seconds"],
                )
            )
        )

        self.speech_min_input.setValue(
            ticks_to_minutes(
                int(
                    self.settings.get(
                        "speech_min_ticks",
                        DEFAULT_SETTINGS["speech_min_ticks"],
                    )
                )
            )
        )

        self.speech_max_input.setValue(
            ticks_to_minutes(
                int(
                    self.settings.get(
                        "speech_max_ticks",
                        DEFAULT_SETTINGS["speech_max_ticks"],
                    )
                )
            )
        )

        self.update_size_label()

    def update_size_label(self):
        self.size_label.setText(f"{self.size_slider.value()} px wide")

    def build_updated_settings(self) -> dict:
        min_minutes = self.speech_min_input.value()
        max_minutes = self.speech_max_input.value()

        if min_minutes > max_minutes:
            min_minutes, max_minutes = max_minutes, min_minutes

        sprite_width = self.size_slider.value()
        sprite_height = round(sprite_width * SPRITE_ASPECT_RATIO)

        updated_settings = dict(self.settings)
        updated_settings["user_name"] = self.name_input.text().strip()
        updated_settings["sprite_width"] = sprite_width
        updated_settings["sprite_height"] = sprite_height
        updated_settings["walk_interval_seconds"] = self.walk_interval_input.value()
        updated_settings["speech_min_ticks"] = minutes_to_ticks(min_minutes)
        updated_settings["speech_max_ticks"] = minutes_to_ticks(max_minutes)

        return updated_settings

    def apply_settings(self, settings: dict):
        save_settings(settings)
        self.settings = dict(settings)

        if self.on_save is not None:
            self.on_save(dict(settings))

    def save_and_close(self):
        updated_settings = self.build_updated_settings()
        self.apply_settings(updated_settings)
        self.hide()

    def reset_defaults(self):
        default_settings = DEFAULT_SETTINGS.copy()
        self.load_values(default_settings)
        self.apply_settings(default_settings)
        self.status_label.setText("Defaults restored.")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
