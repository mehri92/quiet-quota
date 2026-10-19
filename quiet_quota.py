"""Quiet Quota: small, non-activating Windows quota notifications."""
import ctypes
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import sys
import time

from PySide6.QtCore import Qt, QPoint, QSize, QTimer, QPropertyAnimation, QEasingCurve, QLockFile, Signal, QUrl
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QFont, QFontMetrics, QPen, QDesktopServices
from PySide6.QtWidgets import (QApplication, QWidget, QSystemTrayIcon, QMenu,
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QDialogButtonBox, QMessageBox, QToolButton, QPushButton, QHBoxLayout)
from quota_core import DEFAULTS, validate_config, atomic_json, ThresholdPolicy, Poller
from i18n import LANGUAGES, CATALOGS, tr
from connection_ui import ConnectionDialog

DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "QuietQuota"
KOFI_URL = "https://ko-fi.com/st0nks"
WINDOWS_APP_ID = "mehri92.QuietQuota"


def set_taskbar_identity():
    """Give Windows our own taskbar group before Qt creates any windows."""
    if sys.platform != "win32":
        return
    try:
        set_app_id = ctypes.WinDLL("shell32").SetCurrentProcessExplicitAppUserModelID
        set_app_id.argtypes = [ctypes.c_wchar_p]
        set_app_id.restype = ctypes.c_long
        result = set_app_id(WINDOWS_APP_ID)
        if result != 0:
            raise OSError(f"SetCurrentProcessExplicitAppUserModelID failed: {result:#x}")
    except (OSError, AttributeError) as error:
        # Icon setup must not prevent quota monitoring. Diagnostics.cmd captures
        # this warning; pythonw may have no stderr stream.
        if sys.stderr is not None:
            print(f"Quiet Quota taskbar identity: {error}", file=sys.stderr)


def load_config():
    try:
        path = DATA / "settings.json"
        return (validate_config(json.loads(path.read_text("utf-8"))) if path.exists()
                else DEFAULTS.copy()), None
    except (ValueError, TypeError, OSError):
        return DEFAULTS.copy(), "bad_settings"


def notice(language, message, parent=None, warning=False):
    box = QMessageBox(parent)
    box.setWindowTitle("Quiet Quota")
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Information)
    box.addButton(tr(language, "ok"), QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def notification_blocked():
    """Ask Windows about presentation, fullscreen and quiet modes."""
    if os.name != "nt":
        return False
    state = ctypes.c_int()
    try:
        hr = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
        return hr == 0 and state.value in (1, 2, 3, 4, 6, 7)
    except (OSError, AttributeError):
        return False


def color_for(used):
    return "#ef7d84" if used >= 80 else "#e5bc68" if used >= 50 else "#70c6a3"


class Toast(QWidget):
    def __init__(self, cfg):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.WindowDoesNotAcceptFocus |
                         Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(264, 76)
        self.value_width = 84
        self.cfg, self.used, self.demo = cfg, 67, False
        self.animation = QPropertyAnimation(self, b"pos", self)
        self.animation.setDuration(260)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.animation_done)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)
        self.exiting = False

    def show_usage(self, used, demo=False):
        self.animation.stop()
        self.timer.stop()
        self.used, self.demo, self.exiting = used, demo, False
        self.refresh_text()
        self.target, self.start_pos = self.positions()
        self.move(self.start_pos if self.cfg["animations"] else self.target)
        self.update()
        self.show()
        if self.cfg["animations"]:
            self.animation.setStartValue(self.start_pos)
            self.animation.setEndValue(self.target)
            self.animation.start()
        else:
            self.timer.start(self.cfg["duration_ms"])

    def positions(self):
        screens = QApplication.screens()
        screen = screens[min(self.cfg["monitor"], len(screens)-1)]
        rect = screen.availableGeometry()
        right = self.cfg["corner"].endswith("right")
        bottom = self.cfg["corner"].startswith("bottom")
        x = rect.right() - self.width() - 16 if right else rect.left() + 16
        y = rect.bottom() - self.height() - 16 if bottom else rect.top() + 16
        target = QPoint(x, y)
        # Only 28 px of travel: a quiet slide, no bouncing or flashing.
        return target, target + QPoint(28 if right else -28, 0)

    def refresh_text(self):
        # Reserve separate text/value columns, including long translations.
        font = QFont("Segoe UI")
        font.setPixelSize(12)
        title = "Work / Codex" + (" · " + tr(self.cfg["language"], "demo") if self.demo else "")
        title_width = QFontMetrics(font).horizontalAdvance(title)
        font.setPixelSize(11)
        label_width = QFontMetrics(font).horizontalAdvance(tr(self.cfg["language"], "weekly_used"))
        font.setPixelSize(23)
        font.setWeight(QFont.Weight.DemiBold)
        self.value_width = max(84, QFontMetrics(font).horizontalAdvance("100 %") + 4)
        self.setFixedWidth(max(264, 39 + max(title_width, label_width) + 12 + self.value_width + 18))
        self.setAccessibleName(tr(self.cfg["language"], "usage_status", value=math.floor(self.used)))

    def refresh_presentation(self):
        """Apply visual settings without showing a toast or restarting its timeout."""
        self.refresh_text()
        if hasattr(self, "target"):
            self.target, self.start_pos = self.positions()
            running = self.animation.state() == QPropertyAnimation.State.Running
            if running and not self.cfg["animations"]:
                self.animation.stop()
                if self.exiting:
                    self.hide()
                else:
                    self.move(self.target)
                    # Entry was interrupted before the visible-period timer began.
                    self.timer.start(self.cfg["duration_ms"])
            elif running:
                elapsed = self.animation.currentTime()
                self.animation.setStartValue(self.target if self.exiting else self.start_pos)
                self.animation.setEndValue(self.start_pos if self.exiting else self.target)
                self.animation.setCurrentTime(elapsed)
            else:
                self.move(self.target)
        self.update()

    def animation_done(self):
        if self.exiting:
            self.hide()
        else:
            self.timer.start(self.cfg["duration_ms"])

    def dismiss(self):
        self.exiting = True
        if not self.cfg["animations"]:
            self.hide()
            return
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(self.start_pos)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#34383d"))
        p.setBrush(QColor("#22262b"))
        p.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 12, 12)
        color = QColor(color_for(self.used))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(18, 27, 9, 9)
        font = QFont("Segoe UI")
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(QColor("#c7cbd0"))
        p.drawText(39, 28, "Work / Codex" + (" · " + tr(self.cfg["language"], "demo") if self.demo else ""))
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QColor("#a3aab3"))
        p.drawText(39, 47, tr(self.cfg["language"], "weekly_used"))
        font.setPixelSize(23)
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        p.setPen(QColor("#f1f3f5"))
        p.drawText(self.width()-18-self.value_width, 13, self.value_width, 35, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   f"{math.floor(self.used)} %")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#3b4148"))
        p.drawRoundedRect(18, 61, self.width()-36, 3, 1.5, 1.5)
        p.setBrush(color)
        if self.used > 0:
            p.drawRoundedRect(18, 61, (self.width()-36)*self.used/100, 3, 1.5, 1.5)
        p.end()


def coffee_icon():
    """A small cup drawn locally at native sizes, without font or image dependencies."""
    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(size / 20, size / 20)
        p.setPen(QPen(QColor("#df806f"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(12, 7, 6, 6, -90 * 16, 180 * 16)
        p.drawRoundedRect(3, 7, 11, 9, 2, 2)
        p.drawLine(2, 18, 16, 18)
        p.drawLine(6, 2, 6, 4)
        p.drawLine(10, 2, 10, 4)
        p.end()
        icon.addPixmap(pix)
    return icon


class Settings(QDialog):
    presentation_changed = Signal(dict)
    connection_requested = Signal()

    def __init__(self, cfg):
        super().__init__()
        self.setWindowIcon(tray_icon())
        self.setMinimumWidth(440)
        self.layout = QFormLayout(self)
        self.layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        self.language.setCurrentIndex(self.language.findData(cfg["language"]))
        self.layout.addRow("Language", self.language)
        self.thresholds = QLineEdit(", ".join(map(str, cfg["thresholds"])))
        self.layout.addRow(" ", self.thresholds)
        self.corner = QComboBox()
        for value in ("bottom-right", "bottom-left", "top-right", "top-left"):
            self.corner.addItem(value, value)
        self.corner.setCurrentIndex(self.corner.findData(cfg["corner"]))
        self.layout.addRow(" ", self.corner)
        self.monitor = QComboBox()
        for i, screen in enumerate(QApplication.screens()):
            self.monitor.addItem(f"{i+1}: {screen.name()}", i)
        self.monitor.setCurrentIndex(min(cfg["monitor"], self.monitor.count()-1))
        self.layout.addRow(" ", self.monitor)
        self.duration = QSpinBox()
        self.duration.setRange(1, 15)
        self.duration.setValue(cfg["duration_ms"]//1000)
        self.layout.addRow(" ", self.duration)
        self.interval = QSpinBox()
        self.interval.setRange(1, 30)
        self.interval.setValue(cfg["poll_seconds"]//60)
        self.layout.addRow(" ", self.interval)
        self.motion = QCheckBox()
        self.motion.setChecked(cfg["animations"])
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        self.support = QToolButton()
        self.support.setText("Ko-fi")
        self.support.setIcon(coffee_icon())
        self.support.setIconSize(QSize(16, 16))
        self.support.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.support.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.support.setCursor(Qt.CursorShape.PointingHandCursor)
        self.support.setStyleSheet("""
            QToolButton {
                color: palette(button-text);
                background-color: rgba(223, 128, 111, 18);
                border: 1px solid rgba(223, 128, 111, 95);
                border-radius: 8px;
                padding: 2px 8px;
                font-weight: 500;
            }
            QToolButton:hover { background-color: rgba(223, 128, 111, 38); }
            QToolButton:pressed { background-color: rgba(223, 128, 111, 62); }
            QToolButton:focus { border: 1px solid #df806f; }
        """)
        self.support.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(KOFI_URL)))
        self.motion_row = QWidget()
        motion_layout = QHBoxLayout(self.motion_row)
        motion_layout.setContentsMargins(0, 0, 0, 0)
        motion_layout.setSpacing(8)
        motion_layout.addWidget(self.motion)
        motion_layout.addStretch()
        motion_layout.addWidget(self.support)
        self.layout.addRow(" ", self.motion_row)
        self.connection_button = QPushButton()
        self.connection_button.setAutoDefault(False)
        # Remove the native tool-button inset so the text lines up with the
        # form labels above it, including Animation.
        self.connection_button.setStyleSheet("""
            QPushButton { border: none; padding: 3px 0px; background: transparent; text-align: left; }
            QPushButton:hover, QPushButton:focus { background: palette(midlight); }
            QPushButton:pressed { background: palette(mid); }
        """)
        self.connection_button.clicked.connect(lambda: self.connection_requested.emit())
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.connection_button)
        footer_layout.addStretch()
        footer_layout.addWidget(self.buttons)
        self.layout.addRow(footer)
        self.language.currentIndexChanged.connect(self.retranslate)
        self.corner.currentIndexChanged.connect(self.preview)
        self.monitor.currentIndexChanged.connect(self.preview)
        self.motion.toggled.connect(self.preview)
        self.retranslate()

    def preview(self):
        self.presentation_changed.emit({
            "language": self.language.currentData(),
            "corner": self.corner.currentData(),
            "monitor": self.monitor.currentData(),
            "animations": self.motion.isChecked(),
        })

    def retranslate(self):
        lang = self.language.currentData()
        self.setWindowTitle("Quiet Quota · " + tr(lang, "settings"))
        for widget, key in ((self.language, "language"), (self.thresholds, "thresholds"),
                            (self.corner, "corner"), (self.monitor, "monitor"),
                            (self.duration, "visible_for"), (self.interval, "poll_every"),
                            (self.motion_row, "animation")):
            self.layout.labelForField(widget).setText(tr(lang, key))
        for i in range(self.corner.count()):
            self.corner.setItemText(i, tr(lang, self.corner.itemData(i)))
        self.duration.setSuffix(" " + tr(lang, "seconds"))
        self.interval.setSuffix(" " + tr(lang, "minutes"))
        self.motion.setText(tr(lang, "slide"))
        self.support.setAccessibleName(tr(lang, "support"))
        self.support.setToolTip(tr(lang, "support") + "\n" + KOFI_URL)
        self.connection_button.setText(tr(lang, "connection") + " …")
        for standard, key in ((QDialogButtonBox.StandardButton.Save, "save"),
                              (QDialogButtonBox.StandardButton.Cancel, "cancel")):
            self.buttons.button(standard).setText(tr(lang, key))
        button_size = self.buttons.button(QDialogButtonBox.StandardButton.Cancel).sizeHint()
        self.support.setFixedSize(button_size)
        self.adjustSize()
        self.preview()

    def save(self):
        try:
            self.result_cfg = validate_config({
                "thresholds": [int(x.strip()) for x in self.thresholds.text().split(",")],
                "corner": self.corner.currentData(), "monitor": self.monitor.currentData(),
                "duration_ms": self.duration.value()*1000,
                "poll_seconds": self.interval.value()*60,
                "animations": self.motion.isChecked(), "language": self.language.currentData()})
        except (ValueError, TypeError):
            lang = self.language.currentData()
            notice(lang, tr(lang, "bad_thresholds"), self, warning=True)
            return
        self.accept()


def tray_icon(color="#70c6a3", used=None):
    """Draw the Q with remaining quota; no reading keeps the static brand mark."""
    remaining = None if used is None else 1 - max(0, min(100, used)) / 100
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(size / 32, size / 32)
        p.setBrush(QColor("#22262b"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(1, 1, 30, 30, 8, 8)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#59616b"), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(8, 7, 16, 16)
        p.setPen(QPen(QColor(color), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if remaining is None:
            p.drawArc(8, 7, 16, 16, 90 * 16, 265 * 16)
        elif remaining == 1:
            p.drawEllipse(8, 7, 16, 16)
        elif remaining > 0:
            # Flat ends preserve the proportion, especially near an empty ring.
            p.setPen(QPen(QColor(color), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(8, 7, 16, 16, 90 * 16, -round(360 * 16 * remaining))
        p.setPen(QPen(QColor(color), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(19, 20, 24, 25)
        p.end()
        icon.addPixmap(pix)
    return icon


class Controller:
    def __init__(self, app, demo=False):
        self.app, self.demo = app, demo
        self.events = queue.Queue()
        self.latest, self.identity, self.last_success = None, None, 0
        self.paused = False
        self.connection_dialog = None
        self.onboarding_offered = False
        self.retired_workers = []
        self.shutting_down = False
        self.cfg, self.error_key = load_config()
        self.policy = ThresholdPolicy(DATA / "state.json")
        self.toast = Toast(self.cfg)
        self.tray = QSystemTrayIcon(tray_icon("#a3aab3", used=100), app)
        self.menu = QMenu()
        self.status = self.menu.addAction("")
        self.status.setEnabled(False)
        self.reset = self.menu.addAction("")
        self.reset.setEnabled(False)
        self.menu.addSeparator()
        self.show_action = self.menu.addAction("", self.show_current)
        self.test_actions = []
        for value in (67, 92):
            action = self.menu.addAction("", lambda checked=False, v=value: self.toast.show_usage(v, True))
            self.test_actions.append((action, value))
        self.pause_action = self.menu.addAction("")
        self.pause_action.setCheckable(True)
        self.pause_action.toggled.connect(self.pause)
        self.settings_action = self.menu.addAction("", self.settings)
        self.connection_action = self.menu.addAction("", self.connect_account)
        self.menu.addSeparator()
        self.quit_action = self.menu.addAction("", app.quit)
        self.tray.setContextMenu(self.menu)
        self.retranslate()
        self.tray.activated.connect(self.activated)
        self.tray.show()
        self.timer = QTimer(app)
        self.timer.timeout.connect(self.consume)
        self.timer.start(500)
        self.worker = None
        if demo:
            QTimer.singleShot(500, lambda: self.toast.show_usage(67, True))
        else:
            self.worker = Poller(self.events, self.cfg["poll_seconds"])
            self.worker.start()
        app.aboutToQuit.connect(self.shutdown)

    def retranslate(self):
        lang = self.cfg["language"]
        self.show_action.setText(tr(lang, "show_current"))
        for action, value in self.test_actions:
            action.setText(tr(lang, "test_popup", value=value))
        self.pause_action.setText(tr(lang, "pause"))
        self.settings_action.setText(tr(lang, "settings") + " …")
        self.connection_action.setText(tr(lang, "connection") + " …")
        self.quit_action.setText(tr(lang, "quit"))
        self.refresh_status()

    def refresh_status(self):
        lang = self.cfg["language"]
        if self.error_key:
            self.status.setText(tr(lang, "unavailable"))
            self.reset.setText(tr(lang, self.error_key))
            self.tray.setToolTip("Quiet Quota · " + tr(lang, self.error_key))
            self.tray.setIcon(tray_icon("#a3aab3", used=100))
        elif self.latest:
            used = self.latest["used"]
            self.status.setText(tr(lang, "usage_status", value=math.floor(used)))
            self.reset.setText(tr(lang, "reset_at", date=datetime.fromtimestamp(
                self.latest["reset"]).strftime("%Y-%m-%d %H:%M")))
            self.tray.setToolTip("Quiet Quota · " + self.status.text())
            self.tray.setIcon(tray_icon(color_for(used), used=used))
        else:
            self.status.setText(tr(lang, "demo_mode" if self.demo else "checking"))
            self.reset.setText(tr(lang, "no_data"))
            self.tray.setToolTip("Quiet Quota · " + self.status.text())
            self.tray.setIcon(tray_icon("#a3aab3", used=100))

    def pause(self, value):
        self.paused = value
        if value:
            self.toast.hide()

    def activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_current()

    def show_current(self):
        if self.latest and time.time()-self.last_success < max(300, self.cfg["poll_seconds"]*2):
            self.toast.show_usage(self.latest["used"])
        elif self.demo:
            self.toast.show_usage(67, True)
        else:
            notice(self.cfg["language"], self.status.text() + "\n" + self.reset.text())

    def consume(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "error":
                self.error_key = event[1] if event[1] in CATALOGS["en"] else "connection_failed"
                self.refresh_status()
                if (not self.demo and not self.onboarding_offered and
                        self.error_key in ("missing_cli", "missing_entry", "sign_in")):
                    self.onboarding_offered = True
                    QTimer.singleShot(0, self.connect_account)
                continue
            _, self.identity, self.latest = event
            self.error_key = None
            self.last_success = time.time()
            used = self.latest["used"]
            self.refresh_status()
            try:
                show = self.policy.observe(self.identity, self.latest, self.cfg["thresholds"],
                    paused=self.paused or notification_blocked())
            except OSError:
                self.error_key = "state_error"
                self.refresh_status()
                continue  # Never risk repeated alerts when persistence fails.
            if show:
                self.toast.show_usage(used)

    def preview_language(self, language):
        self.preview_settings({"language": language})

    def preview_settings(self, changes):
        self.cfg = self.cfg | changes
        self.toast.cfg = self.cfg
        self.toast.refresh_presentation()
        self.retranslate()

    def settings(self):
        original = self.cfg.copy()
        dialog = Settings(self.cfg)
        dialog.presentation_changed.connect(self.preview_settings)
        dialog.connection_requested.connect(lambda: self.connect_account(dialog))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                atomic_json(DATA/"settings.json", dialog.result_cfg)
            except OSError:
                notice(self.cfg["language"], tr(self.cfg["language"], "save_error"), warning=True)
                self.preview_settings(original)
                return
            self.preview_settings(dialog.result_cfg)
            if self.worker:
                self.worker.interval = self.cfg["poll_seconds"]
                self.worker.wake.set()
        else:
            self.preview_settings(original)

    def connect_account(self, parent=None):
        if self.connection_dialog is not None:
            self.connection_dialog.raise_()
            self.connection_dialog.activateWindow()
            return
        self.onboarding_offered = True
        # A new queue isolates any late reply from the previous account reader.
        # Stop it without blocking the UI, then resume with a fresh process.
        self.retired_workers = [w for w in self.retired_workers if w.is_alive()]
        if self.worker:
            self.worker.stop()
            self.retired_workers.append(self.worker)
            self.worker = None
        self.events = queue.Queue()
        self.toast.hide()
        dialog = ConnectionDialog(self.cfg["language"], parent if isinstance(parent, QWidget) else None)
        self.connection_dialog = dialog
        dialog.usage_ready.connect(self.connection_ready)
        try:
            dialog.exec()
        finally:
            dialog.shutdown()
            dialog.deleteLater()
            self.connection_dialog = None
            if not self.demo and not self.shutting_down:
                self.worker = Poller(self.events, self.cfg["poll_seconds"])
                self.worker.start()

    def connection_ready(self, identity, snapshot):
        self.demo = False
        self.events.put(("usage", identity, snapshot))

    def shutdown(self):
        self.shutting_down = True
        self.tray.hide()
        if self.connection_dialog:
            self.connection_dialog.shutdown()
        workers = self.retired_workers + ([self.worker] if self.worker else [])
        for worker in workers:
            worker.stop()
        for worker in workers:
            # A normal request has a bounded 25 s timeout; daemon exit must not
            # orphan app-server. Wait while exiting, never during normal use.
            worker.join(timeout=15)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    set_taskbar_identity()
    app = QApplication(sys.argv)
    app.setApplicationName("Quiet Quota")
    app.setWindowIcon(tray_icon())
    app.setQuitOnLastWindowClosed(False)
    cfg, _ = load_config()
    lang = cfg["language"]
    lock = QLockFile(str(DATA/"quiet-quota.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        notice(lang, tr(lang, "already_running"))
        return 0
    if not QSystemTrayIcon.isSystemTrayAvailable():
        notice(lang, tr(lang, "no_tray"), warning=True)
        return 1
    controller = Controller(app, "--demo" in sys.argv)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
