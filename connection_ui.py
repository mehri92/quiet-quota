"""Responsive account setup; Codex owns browser authentication and credentials."""
import math
import queue

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

from i18n import tr
from quota_core import ConnectionWorker, valid_login_url

INSTALL_GUIDE = "https://developers.openai.com/codex/cli/"


class ConnectionDialog(QDialog):
    usage_ready = Signal(str, dict)

    def __init__(self, language="en", parent=None, worker_factory=ConnectionWorker):
        super().__init__(parent)
        self.language, self.worker_factory = language, worker_factory
        self.events = queue.Queue()
        self.worker = None
        self.busy, self.closing, self.connected = False, False, False
        self.auth_url = None
        self.signed_in = False
        self.setWindowTitle("Quiet Quota · " + tr(language, "connection"))
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        self.intro = self.label(tr(language, "connect_intro"))
        self.status = self.label(tr(language, "checking_connection"))
        self.status.setStyleSheet("font-weight: 600;")
        self.account = self.label("")
        self.account.hide()
        self.detail = self.label("")
        self.detail.hide()
        self.shared = self.label(tr(language, "shared_login"))
        for label in (self.intro, self.status, self.account, self.detail, self.shared):
            layout.addWidget(label)
        self.guide = QPushButton(tr(language, "install_guide"))
        self.guide.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(INSTALL_GUIDE)))
        self.guide.hide()
        layout.addWidget(self.guide)
        self.reopen = QPushButton(tr(language, "browser_open"))
        self.reopen.clicked.connect(self.open_browser)
        self.reopen.hide()
        layout.addWidget(self.reopen)
        row = QHBoxLayout()
        self.connect_button = QPushButton(tr(language, "connect_chatgpt"))
        self.connect_button.clicked.connect(lambda: self.begin(True))
        self.check_button = QPushButton(tr(language, "check_again"))
        self.check_button.clicked.connect(lambda: self.begin(False))
        row.addWidget(self.connect_button)
        row.addWidget(self.check_button)
        layout.addLayout(row)
        bottom = QHBoxLayout()
        bottom.addStretch()
        self.close_button = QPushButton(tr(language, "close"))
        self.close_button.clicked.connect(self.reject)
        bottom.addWidget(self.close_button)
        layout.addLayout(bottom)
        # Return must never initiate authentication unexpectedly.
        for button in (self.guide, self.reopen, self.connect_button, self.check_button, self.close_button):
            button.setAutoDefault(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.consume)
        self.timer.start(100)
        self.begin(False)

    @staticmethod
    def label(text):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def begin(self, login):
        if self.busy or self.closing:
            return
        self.busy = True
        self.connected = self.signed_in = False
        self.auth_url = None
        self.guide.hide()
        self.reopen.hide()
        self.account.clear()
        self.account.hide()
        self.detail.clear()
        self.detail.hide()
        self.status.setText(tr(self.language, "checking_connection"))
        self.connect_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.close_button.setText(tr(self.language, "cancel"))
        self.worker = self.worker_factory(self.events, login=login)
        self.worker.start()

    def open_browser(self):
        if not self.auth_url or self.closing:
            return
        try:
            url = valid_login_url(self.auth_url)
        except RuntimeError:
            self.detail.setText(tr(self.language, "login_failed"))
            return
        if not QDesktopServices.openUrl(QUrl(url)):
            self.detail.setText(tr(self.language, "browser_failed"))
        else:
            self.detail.setText(tr(self.language, "awaiting_login"))
        self.detail.setVisible(not self.detail.text() == self.status.text())

    def consume(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if self.closing and kind != "finished":
                continue
            if kind == "browser":
                self.auth_url = event[1]
                self.status.setText(tr(self.language, "awaiting_login"))
                self.reopen.show()
                self.open_browser()
            elif kind == "account":
                self.signed_in = True
                if event[1]:
                    self.account.setText(tr(self.language, "account_label", email=event[1]))
                    self.account.show()
            elif kind == "connected":
                self.connected = True
                self.status.setText(tr(self.language, "connected_usage", value=math.floor(event[2]["used"])))
                self.detail.setText(tr(self.language, "monitoring_ready"))
                self.detail.show()
                self.usage_ready.emit(event[1], event[2])
            elif kind == "error":
                key, self.signed_in = event[1:]
                status_key = "signed_in_no_quota" if self.signed_in else (
                    "ready_to_connect" if key == "sign_in" else key)
                self.status.setText(tr(self.language, status_key))
                if self.signed_in:
                    self.detail.setText(tr(self.language, key))
                    self.detail.show()
                if key in ("missing_cli", "missing_entry"):
                    self.guide.show()
                    self.detail.setText(tr(self.language, "install_help"))
                    self.detail.show()
            elif kind == "finished":
                self.busy = False
                self.auth_url = None
                self.reopen.hide()
                self.check_button.setEnabled(True)
                self.connect_button.setEnabled(self.guide.isHidden())
                self.connect_button.setText(tr(self.language,
                    "reconnect_chatgpt" if self.signed_in else "connect_chatgpt"))
                self.close_button.setText(tr(self.language, "close"))
                if self.closing:
                    self.timer.stop()
                    super().reject()

    def reject(self):
        if self.busy:
            self.closing = True
            self.auth_url = None
            self.reopen.hide()
            self.status.setText(tr(self.language, "cancelling"))
            self.close_button.setEnabled(False)
            self.worker.stop()
        else:
            self.timer.stop()
            super().reject()

    def shutdown(self):
        self.closing = True
        self.auth_url = None
        self.timer.stop()
        if self.worker:
            self.worker.stop()
            self.worker.join(timeout=15)
