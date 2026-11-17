from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from dataclasses import replace as dataclass_replace

from norashot.config import NoraShotConfig, save_config
from norashot.core.sharing.base import SharingError
from norashot.core.sharing.credentials import save_credentials
from norashot.core.sharing.worker import S3CheckWorker


class SettingsWindow(QDialog):
    """S3 settings only; future managed NoraShot server is not selectable yet."""

    config_saved = Signal()

    def __init__(self, config: NoraShotConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("NoraShot — Хранилище")
        self.setMinimumWidth(510)
        self.check_worker: S3CheckWorker | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Публикация скриншотов в собственном S3-совместимом хранилище"))
        form = QFormLayout()
        self.enabled = QCheckBox("Разрешить кнопку «Поделиться»")
        self.enabled.setChecked(config.upload.enabled)
        form.addRow("Загрузка:", self.enabled)

        self.endpoint = QLineEdit(config.upload.endpoint)
        self.endpoint.setPlaceholderText("https://s3.ru-1.storage.selcloud.ru")
        form.addRow("Endpoint:", self.endpoint)

        self.bucket = QLineEdit(config.upload.bucket)
        self.bucket.setPlaceholderText("Имя приватного бакета")
        form.addRow("Bucket:", self.bucket)

        self.region = QLineEdit(config.upload.region)
        form.addRow("Region:", self.region)

        self.prefix = QLineEdit(config.upload.prefix_template)
        self.prefix.setToolTip("Допускаются шаблоны strftime, например %Y/%m/%d")
        form.addRow("Префикс:", self.prefix)

        self.ttl = QSpinBox()
        self.ttl.setRange(1, 168)
        self.ttl.setSuffix(" ч")
        self.ttl.setValue(max(1, min(168, config.upload.link_ttl_seconds // 3600)))
        form.addRow("Срок ссылки:", self.ttl)

        self.access = QLineEdit()
        self.access.setPlaceholderText("Access Key — не сохраняется в YAML")
        self.secret = QLineEdit()
        self.secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret.setPlaceholderText("Secret Key — не сохраняется в YAML")
        form.addRow("Access Key:", self.access)
        form.addRow("Secret Key:", self.secret)
        layout.addLayout(form)

        layout.addWidget(QLabel(
            "Ключи отдельно сохраняются в защищённом хранилище Windows. "
            "Пустые поля ключей не удаляют уже сохранённые значения."
        ))

        buttons = QHBoxLayout()
        save_keys_button = QPushButton("Сохранить ключи")
        save_keys_button.clicked.connect(self.store_keys)
        buttons.addWidget(save_keys_button)
        self.check_button = QPushButton("Проверить подключение")
        self.check_button.clicked.connect(self.check_connection)
        buttons.addWidget(self.check_button)
        buttons.addStretch(1)

        save_button = QPushButton("Сохранить настройки")
        save_button.clicked.connect(self.save)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

    def _draft_upload_config(self):
        return dataclass_replace(
            self.config.upload,
            provider="s3",
            enabled=True,
            endpoint=self.endpoint.text().strip().rstrip("/"),
            bucket=self.bucket.text().strip(),
            region=self.region.text().strip(),
            prefix_template=self.prefix.text().strip(),
            link_ttl_seconds=self.ttl.value() * 3600,
        )

    def check_connection(self) -> None:
        if self.check_worker is not None:
            return
        self.check_button.setText("Проверка…")
        self.check_button.setEnabled(False)
        self.check_worker = S3CheckWorker(self._draft_upload_config(), parent=self)
        self.check_worker.completed.connect(self._check_completed)
        self.check_worker.failed.connect(self._check_failed)
        self.check_worker.finished.connect(self._check_finished)
        self.check_worker.start()
        logger.info("S3 connectivity check requested from settings")

    def _check_completed(self, result) -> None:
        if result.category == "ok":
            QMessageBox.information(self, "NoraShot — S3", result.message)
        else:
            QMessageBox.warning(self, "NoraShot — S3", result.message)

    def _check_failed(self, message: str) -> None:
        QMessageBox.warning(self, "NoraShot — S3", message)

    def _check_finished(self) -> None:
        worker = self.check_worker
        self.check_worker = None
        if worker is not None:
            worker.deleteLater()
        self.check_button.setText("Проверить подключение")
        self.check_button.setEnabled(True)

    def reject(self) -> None:
        if self.check_worker is not None and self.check_worker.isRunning():
            QMessageBox.information(self, "NoraShot", "Дождитесь завершения проверки S3.")
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self.check_worker is not None and self.check_worker.isRunning():
            event.ignore()
            QMessageBox.information(self, "NoraShot", "Дождитесь завершения проверки S3.")
            return
        super().closeEvent(event)

    def store_keys(self) -> None:
        try:
            save_credentials(
                self.endpoint.text().strip(),
                self.bucket.text().strip(),
                self.access.text(),
                self.secret.text(),
            )
        except SharingError as exc:
            QMessageBox.warning(self, "NoraShot", str(exc))
            return
        self.access.clear()
        self.secret.clear()
        logger.info("S3 access credentials updated via settings dialog")
        QMessageBox.information(self, "NoraShot", "Ключи S3 сохранены в Windows.")

    def save(self) -> None:
        if self.check_worker is not None and self.check_worker.isRunning():
            QMessageBox.information(self, "NoraShot", "Дождитесь завершения проверки S3.")
            return
        endpoint = self.endpoint.text().strip().rstrip("/")
        bucket = self.bucket.text().strip()
        if self.enabled.isChecked():
            if not endpoint.startswith("https://") or not bucket:
                QMessageBox.warning(self, "NoraShot", "Укажите HTTPS Endpoint и Bucket.")
                return

        cfg = self.config.upload
        cfg.enabled = self.enabled.isChecked()
        cfg.provider = "s3"
        cfg.endpoint = endpoint
        cfg.bucket = bucket
        cfg.region = self.region.text().strip()
        cfg.prefix_template = self.prefix.text().strip()
        cfg.link_ttl_seconds = self.ttl.value() * 3600

        try:
            save_config(self.config)
        except Exception as exc:
            logger.error("S3 settings save failed | error_type={}", type(exc).__name__)
            QMessageBox.critical(self, "NoraShot", "Не удалось записать настройки.")
            return

        logger.info("S3 settings saved | enabled={} | bucket={}", cfg.enabled, cfg.bucket)
        self.config_saved.emit()
        self.accept()
