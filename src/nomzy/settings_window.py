from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSlider, QTabWidget, QVBoxLayout, QWidget,
)

from .settings import DEFAULT_SETTINGS, INTEGER_LIMITS, normalize_settings, save_settings
from .scheduling import TICKS_PER_SECOND

SPRITE_ASPECT_RATIO = 85 / 110
MOVEMENT_AMOUNTS = {"Low": (5, 15), "Normal": (10, 35), "High": (25, 70)}


class NomzySettingsWindow(QWidget):
    """Edits are local until Apply; the last applied snapshot survives Cancel."""

    def __init__(self, settings: dict, on_save):
        super().__init__()
        self.on_save = on_save
        self.controls = {}
        self.numeric_scales = {}
        self.setWindowTitle("Nomzy Settings")
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.tabs = QTabWidget()
        general = self.section("General")
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(80)
        self.name_input.setPlaceholderText("friend")
        general.addRow("Your name", self.name_input)
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(60, 180)
        self.size_label = QLabel()
        self.size_slider.valueChanged.connect(self.update_size_label)
        general.addRow("Nomzy size", self.size_slider)
        general.addRow("", self.size_label)
        self.checkbox(general, "Always on top", "always_on_top")
        self.checkbox(general, "Remember position", "save_position")

        movement = self.section("Movement")
        self.checkbox(movement, "Enable movement", "movement_enabled")
        self.walk_interval_input = self.number(movement, "Walk about every", "walk_interval_seconds", 1, " seconds")
        self.movement_amount_input = QComboBox()
        self.movement_amount_input.addItems([*MOVEMENT_AMOUNTS, "Custom"])
        movement.addRow("Movement amount", self.movement_amount_input)
        self.controls["movement_enabled"].toggled.connect(self.update_enabled)

        idle = self.section("Idle behavior")
        self.range_rows(idle, "Rest interval", "rest_min_interval_ms", "rest_max_interval_ms", 1000, " seconds")
        self.number(idle, "Chance of sleeping instead of sitting", "sleep_chance_percent", 1, " %")
        self.range_rows(idle, "Blink interval", "blink_min_interval_ms", "blink_max_interval_ms", 1000, " seconds")

        speech = self.section("Speech")
        self.checkbox(speech, "Enable autonomous speech", "speech_enabled")
        self.speech_min_input, self.speech_max_input = self.range_rows(
            speech, "Speaking interval", "speech_min_ticks", "speech_max_ticks", TICKS_PER_SECOND, " seconds")
        self.range_rows(speech, "Bubble display time", "speech_min_duration_ticks", "speech_max_duration_ticks", TICKS_PER_SECOND, " seconds")
        opacity = self.number(speech, "Bubble opacity", "speech_bubble_opacity", 2.55, " %")
        opacity.setDecimals(0)
        opacity.setRange(10, 100)
        self.controls["speech_enabled"].toggled.connect(self.update_enabled)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_draft)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        self.reset_button = QPushButton("Restore Defaults")
        self.reset_button.clicked.connect(self.reset_defaults)
        buttons = QHBoxLayout()
        buttons.addWidget(self.reset_button)
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.apply_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        self.load_values(settings)

    def section(self, title):
        page = QWidget()
        form = QFormLayout(page)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.tabs.addTab(page, title)
        return form

    def checkbox(self, form, label, key):
        control = QCheckBox(label)
        self.controls[key] = control
        form.addRow(control)
        return control

    def number(self, form, label, key, scale, suffix):
        control = QDoubleSpinBox()
        control.setDecimals(3 if scale == 1000 else 2)
        low, high = INTEGER_LIMITS[key]
        control.setRange(low / scale, high / scale)
        control.setSuffix(suffix)
        self.controls[key] = control
        self.numeric_scales[key] = scale
        form.addRow(label, control)
        return control

    def range_rows(self, form, label, low_key, high_key, scale, suffix):
        low = self.number(form, f"{label} — minimum", low_key, scale, suffix)
        high = self.number(form, f"{label} — maximum", high_key, scale, suffix)
        low.valueChanged.connect(lambda value: high.setValue(max(value, high.value())))
        high.valueChanged.connect(lambda value: low.setValue(min(value, low.value())))
        return low, high

    def load_values(self, settings):
        self.settings = normalize_settings(settings)
        self.populate(self.settings)
        self.status_label.clear()

    def populate(self, settings):
        self.name_input.setText(settings["user_name"])
        self.size_slider.setValue(settings["sprite_width"])
        for key, control in self.controls.items():
            control.blockSignals(True)
            if key in self.numeric_scales:
                control.setValue(settings[key] / self.numeric_scales[key])
            else:
                control.setChecked(settings[key])
            control.blockSignals(False)
        amount = (settings["walk_min_ticks"], settings["walk_max_ticks"])
        self._custom_amount = amount
        self.movement_amount_input.setCurrentText(next(
            (name for name, values in MOVEMENT_AMOUNTS.items() if values == amount), "Custom"))
        self.update_size_label()
        self.update_enabled()

    def update_enabled(self):
        enabled = self.controls["movement_enabled"].isChecked()
        self.walk_interval_input.setEnabled(enabled)
        self.movement_amount_input.setEnabled(enabled)
        for key in ("speech_min_ticks", "speech_max_ticks"):
            self.controls[key].setEnabled(self.controls["speech_enabled"].isChecked())

    def update_size_label(self):
        self.size_label.setText(f"{round(self.size_slider.value() / 110 * 100)}% of standard size")

    def build_updated_settings(self):
        updated = dict(self.settings)
        updated["user_name"] = self.name_input.text()
        updated["sprite_width"] = self.size_slider.value()
        # Preserve imported dimensions unless the size was edited.
        if updated["sprite_width"] != self.settings["sprite_width"]:
            updated["sprite_height"] = round(updated["sprite_width"] * SPRITE_ASPECT_RATIO)
        for key, control in self.controls.items():
            updated[key] = (round(control.value() * self.numeric_scales[key])
                            if key in self.numeric_scales else control.isChecked())
        # Keep existing alpha precision when its displayed percentage is unchanged.
        if self.controls["speech_bubble_opacity"].value() == round(self.settings["speech_bubble_opacity"] / 2.55):
            updated["speech_bubble_opacity"] = self.settings["speech_bubble_opacity"]
        updated["walk_min_ticks"], updated["walk_max_ticks"] = MOVEMENT_AMOUNTS.get(
            self.movement_amount_input.currentText(), self._custom_amount)
        return normalize_settings(updated)

    def apply_draft(self):
        updated = self.build_updated_settings()
        try:
            save_settings(updated)
        except OSError:
            self.status_label.setText("Could not save settings. Your edits are still here; try Apply again.")
            return
        if self.on_save is not None:
            self.on_save(dict(updated))
        self.load_values(updated)
        self.status_label.setText("Settings applied.")

    def reset_defaults(self):
        # Restore only exposed settings; internal platform configuration stays intact.
        self.populate(DEFAULT_SETTINGS)
        self.status_label.setText("Defaults ready. Click Apply to save, or Cancel to discard.")

    def cancel(self):
        self.populate(self.settings)
        self.status_label.clear()
        self.hide()

    def closeEvent(self, event):
        self.cancel()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()
        else:
            super().keyPressEvent(event)
