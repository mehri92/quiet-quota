import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from string import Formatter
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication, QDialog
from i18n import LANGUAGES, CATALOGS, tr
from quota_core import DEFAULTS, validate_config, atomic_json
import quiet_quota as ui


class LocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_keys_and_format_fields(self):
        def fields(value):
            return {name for _, name, _, _ in Formatter().parse(value) if name}
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(set(CATALOGS[language]), set(CATALOGS['en']))
                for key, value in CATALOGS[language].items():
                    self.assertTrue(value.strip())
                    self.assertEqual(fields(value), fields(CATALOGS['en'][key]))
                    tr(language, key, value=100, date='2026-10-26 12:00')

    def test_old_settings_and_unknown_languages(self):
        old = {k: v for k, v in DEFAULTS.items() if k != 'language'}
        old['thresholds'] = [60, 80, 95]
        self.assertEqual(validate_config(old)['language'], 'en')
        self.assertEqual(validate_config(old)['thresholds'], [60, 80, 95])
        self.assertEqual(validate_config({'language': 'unknown'})['language'], 'en')
        self.assertEqual(tr('unknown', 'settings'), 'Settings')

    def test_support_requires_click_and_does_not_save_or_close(self):
        with patch.object(ui.QDesktopServices, 'openUrl', return_value=True) as open_url:
            dialog = ui.Settings(DEFAULTS.copy())
            try:
                dialog.show()
                for language in LANGUAGES:
                    dialog.language.setCurrentIndex(dialog.language.findData(language))
                    self.app.processEvents()
                    self.assertEqual(dialog.support.accessibleName(), tr(language, 'support'))
                    self.assertFalse(dialog.windowIcon().isNull())
                open_url.assert_not_called()
                dialog.thresholds.setText('60, 85')
                dialog.support.click()
                open_url.assert_called_once()
                self.assertEqual(open_url.call_args.args[0].toString(), 'https://ko-fi.com/st0nks')
                self.assertTrue(dialog.isVisible())
                self.assertFalse(hasattr(dialog, 'result_cfg'))
                self.assertEqual(dialog.thresholds.text(), '60, 85')
            finally:
                dialog.close()

    def test_language_switch_preserves_edits_and_roundtrips(self):
        dialog = ui.Settings(DEFAULTS.copy())
        try:
            dialog.thresholds.setText('60, 85, 99')
            dialog.corner.setCurrentIndex(dialog.corner.findData('top-left'))
            dialog.duration.setValue(5)
            dialog.interval.setValue(3)
            dialog.motion.setChecked(False)
            for language in LANGUAGES:
                with self.subTest(language=language):
                    dialog.language.setCurrentIndex(dialog.language.findData(language))
                    self.assertEqual(dialog.thresholds.text(), '60, 85, 99')
                    self.assertEqual(dialog.corner.currentData(), 'top-left')
                    self.assertIn(tr(language, 'settings'), dialog.windowTitle())
                    dialog.save()
                    self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
                    expected = DEFAULTS | dict(language=language, thresholds=[60, 85, 99],
                        corner='top-left', duration_ms=5000, poll_seconds=180,
                        animations=False)
                    self.assertEqual(dialog.result_cfg, expected)
                    with tempfile.TemporaryDirectory() as folder, patch.object(ui, 'DATA', Path(folder)):
                        atomic_json(Path(folder)/'settings.json', dialog.result_cfg)
                        self.assertEqual(ui.load_config(), (expected, None))
        finally:
            dialog.close()

    def test_toast_fits_all_languages_and_does_not_take_focus(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                toast = ui.Toast(DEFAULTS | dict(language=language, animations=False))
                try:
                    toast.show_usage(100, demo=True)
                    self.app.processEvents()
                    font = QFont('Segoe UI')
                    for size, text in ((12, 'Work / Codex · ' + tr(language, 'demo')),
                                       (11, tr(language, 'weekly_used'))):
                        font.setPixelSize(size)
                        self.assertLessEqual(39 + QFontMetrics(font).horizontalAdvance(text), toast.width()-30-toast.value_width)
                    font.setPixelSize(23)
                    font.setWeight(QFont.Weight.DemiBold)
                    self.assertLessEqual(QFontMetrics(font).horizontalAdvance('100 %'), toast.value_width)
                    for flag in (Qt.WindowType.WindowStaysOnTopHint,
                                 Qt.WindowType.WindowDoesNotAcceptFocus,
                                 Qt.WindowType.WindowTransparentForInput):
                        self.assertTrue(toast.windowFlags() & flag)
                    self.assertTrue(toast.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))
                    self.assertEqual(toast.timer.interval(), 4000)
                    self.assertEqual(toast.accessibleName(), tr(language, 'usage_status', value=100))
                    toast.dismiss()
                    self.assertFalse(toast.isVisible())
                finally:
                    toast.timer.stop()
                    toast.close()

    def check_live_language(self, outcome):
        screens = [SimpleNamespace(name=lambda: 'First', availableGeometry=lambda: QRect(0, 0, 900, 700)),
                   SimpleNamespace(name=lambda: 'Second', availableGeometry=lambda: QRect(900, 0, 900, 700))]
        with tempfile.TemporaryDirectory() as folder, patch.object(ui, 'DATA', Path(folder)), \
                patch.object(ui.QSystemTrayIcon, 'show'), patch.object(ui.QTimer, 'singleShot'), \
                patch.object(ui.QApplication, 'screens', return_value=screens):
            atomic_json(Path(folder)/'settings.json', DEFAULTS)
            controller = ui.Controller(self.app, demo=True)
            controller.timer.stop()
            dialog = ui.Settings(controller.cfg)
            controller.toast.cfg = controller.cfg | {'animations': False}
            controller.toast.show_usage(42)
            timer_id = controller.toast.timer.timerId()
            edge = controller.toast.x() + controller.toast.width()

            def interact():
                for lang in ('pt', 'de', 'ja'):
                    dialog.language.setCurrentIndex(dialog.language.findData(lang))
                    self.assertEqual(controller.cfg['language'], lang)
                    self.assertEqual(controller.show_action.text(), tr(lang, 'show_current'))
                    self.assertEqual(controller.toast.accessibleName(), tr(lang, 'usage_status', value=42))
                    self.assertTrue(controller.toast.isVisible())
                    self.assertEqual(controller.toast.timer.timerId(), timer_id)
                    self.assertEqual(controller.toast.x() + controller.toast.width(), edge)
                    self.assertEqual(ui.load_config()[0]['language'], 'en')
                dialog.thresholds.setText('60, 85, 99')
                dialog.duration.setValue(7)
                dialog.interval.setValue(5)
                dialog.corner.setCurrentIndex(dialog.corner.findData('top-left'))
                dialog.monitor.setCurrentIndex(1)
                dialog.motion.setChecked(False)
                self.assertEqual(controller.toast.pos(), QPoint(916, 16))
                self.assertEqual(controller.cfg['corner'], 'top-left')
                self.assertEqual(controller.cfg['monitor'], 1)
                self.assertFalse(controller.cfg['animations'])
                self.assertEqual(controller.toast.timer.timerId(), timer_id)
                for key in ('thresholds', 'duration_ms', 'poll_seconds'):
                    self.assertEqual(controller.cfg[key], DEFAULTS[key])
                self.assertEqual(ui.load_config()[0], DEFAULTS)
                if outcome == 'cancel':
                    dialog.reject()
                else:
                    dialog.save()
                return dialog.result()

            try:
                with patch.object(ui, 'Settings', return_value=dialog), \
                        patch.object(dialog, 'exec', side_effect=interact):
                    if outcome == 'failure':
                        with patch.object(ui, 'atomic_json', side_effect=OSError('test')), patch.object(ui, 'notice'):
                            controller.settings()
                    else:
                        controller.settings()
                expected = 'ja' if outcome == 'save' else 'en'
                self.assertEqual(controller.cfg['language'], expected)
                self.assertEqual(controller.show_action.text(), tr(expected, 'show_current'))
                self.assertEqual(controller.toast.accessibleName(), tr(expected, 'usage_status', value=42))
                self.assertEqual(ui.load_config()[0]['language'], expected)
                expected_cfg = DEFAULTS | dict(language='ja', corner='top-left', monitor=1,
                    animations=False, thresholds=[60, 85, 99], duration_ms=7000, poll_seconds=300)
                self.assertEqual(controller.cfg, expected_cfg if outcome == 'save' else DEFAULTS)
                self.assertEqual(ui.load_config()[0], controller.cfg)
                self.assertEqual(controller.toast.pos(), controller.toast.positions()[0])
                controller.toast.hide()
                controller.preview_settings({'language': 'fr', 'corner': 'bottom-left', 'monitor': 0})
                self.assertFalse(controller.toast.isVisible())
            finally:
                controller.toast.timer.stop()
                controller.toast.animation.stop()
                controller.toast.close()
                controller.shutdown()
                self.app.aboutToQuit.disconnect(controller.shutdown)
                controller.menu.close()
                dialog.close()

    def test_live_language_save_and_restart(self):
        self.check_live_language('save')

    def test_live_language_cancel_restores_everywhere(self):
        self.check_live_language('cancel')

    def test_live_language_save_failure_restores_everywhere(self):
        self.check_live_language('failure')

    def test_visual_changes_during_animation_do_not_restart_it(self):
        toast = ui.Toast(DEFAULTS.copy())
        try:
            toast.show_usage(67)
            toast.animation.setCurrentTime(130)
            toast.cfg = toast.cfg | {'corner': 'top-left'}
            toast.refresh_presentation()
            self.assertEqual(toast.animation.currentTime(), 130)
            self.assertEqual(toast.animation.endValue(), toast.target)
            self.assertFalse(toast.timer.isActive())
            toast.cfg = toast.cfg | {'animations': False}
            toast.refresh_presentation()
            self.assertEqual(toast.animation.state(), ui.QPropertyAnimation.State.Stopped)
            self.assertEqual(toast.pos(), toast.target)
            self.assertTrue(toast.timer.isActive())
            timer_id = toast.timer.timerId()
            toast.cfg = toast.cfg | {'animations': True}
            toast.refresh_presentation()
            self.assertEqual(toast.timer.timerId(), timer_id)
            self.assertEqual(toast.animation.state(), ui.QPropertyAnimation.State.Stopped)
            toast.timer.stop()
            toast.dismiss()
            toast.animation.setCurrentTime(100)
            toast.cfg = toast.cfg | {'animations': False}
            toast.refresh_presentation()
            self.assertFalse(toast.isVisible())
            self.assertFalse(toast.timer.isActive())
        finally:
            toast.timer.stop()
            toast.animation.stop()
            toast.close()


if __name__ == '__main__':
    unittest.main()
