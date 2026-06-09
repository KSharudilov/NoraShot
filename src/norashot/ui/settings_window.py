from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from norashot.config import NoraShotConfig, save_config


class SettingsWindow(QDialog):
    config_saved = Signal()

    def __init__(self, config: NoraShotConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("NoraShot Settings")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings UI will be expanded in the next milestone."))
        save_button = QPushButton("Save current config")
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button)
        self.setLayout(layout)

    def save(self) -> None:
        save_config(self.config)
        self.config_saved.emit()
        self.accept()
