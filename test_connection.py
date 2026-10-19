import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from quota_core import CodexReader, ConnectionWorker, valid_login_url, DEFAULTS
from connection_ui import ConnectionDialog
from i18n import LANGUAGES, tr
import quiet_quota as ui


# Exercise a real child process/stdin/stdout. The fake service permits only
# account operations, and writes the received method names (never auth data).
SERVER = r'''
import json, sys, time
from pathlib import Path
mode, log = sys.argv[1:]
signed = False
def emit(data):
 print(json.dumps(data), flush=True)
for line in sys.stdin:
 m = json.loads(line); method = m.get('method')
 with open(log, 'a') as f: f.write(str(method) + '\n')
 if method == 'initialize': result = {}
 elif method == 'initialized': continue
 elif method == 'account/login/start':
  result = {'type':'chatgpt', 'loginId':'ours', 'authUrl':'https://auth.openai.com/oauth/authorize?state=test'}
  if mode == 'bad_url': result['authUrl'] = 'https://evil.invalid/'
  if mode == 'early':
   signed = True
   emit({'method':'account/login/completed','params':{'loginId':'ours','success':True}})
  emit({'id':m['id'],'result':result})
  if mode not in ('wait','early','bad_url'):
   # An unrelated completion must never authenticate this request.
   emit({'method':'account/login/completed','params':{'loginId':'other','success':True}})
   if mode == 'wrong_only': continue
   signed = mode != 'failure'
   emit({'method':'account/login/completed','params':{'loginId':'ours','success':signed,'error':'SECRET upstream detail'}})
  continue
 elif method == 'account/login/cancel': result = {}
 elif method == 'account/read':
  result = {'account':{'type':'chatgpt','email':'test@example.invalid'} if signed else None}
 elif method == 'account/rateLimits/read':
  result = {'rateLimits':{'secondary':{'windowDurationMins':10080,'usedPercent':42,'resetsAt':int(time.time())+3600}}}
 else: sys.exit(9)
 emit({'id':m['id'],'result':result})
'''


class AuthenticationTests(unittest.TestCase):
    def run_login(self, mode, expected=None, cancel=False):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'methods.txt'
            event = threading.Event()
            reader = CodexReader([sys.executable, '-u', '-c', SERVER, mode, str(log)], cancel=event)
            opened = []
            def browser(url):
                opened.append(url)
                if cancel:
                    event.set()
            try:
                if expected:
                    with self.assertRaisesRegex(RuntimeError, '^' + expected + '$'):
                        reader.login(browser, timeout=.05)
                else:
                    reader.login(browser)
                    self.assertEqual(reader.read()[1]['used'], 42)
            finally:
                proc = reader.proc
                reader.close()
            self.assertIsNotNone(proc.poll())
            methods = log.read_text()
            self.assertNotIn('thread/', methods)
            self.assertNotIn('turn/', methods)
            self.assertNotIn('account/logout', methods)
            if expected:
                self.assertIn('account/login/cancel', methods)
            if mode == 'bad_url':
                self.assertEqual(opened, [])
            else:
                self.assertEqual(len(opened), 1)

    def test_login_completes_and_reads_real_snapshot_over_stdio(self):
        self.run_login('success')

    def test_early_completion_is_not_lost_during_rpc(self):
        self.run_login('early')

    def test_user_cancellation_and_timeout_cancel_owned_login(self):
        self.run_login('wait', 'cancelled', cancel=True)
        self.run_login('wait', 'login_timeout')

    def test_unrelated_completion_does_not_authenticate(self):
        self.run_login('wrong_only', 'login_timeout')

    def test_failure_is_sanitised_and_non_official_url_is_blocked(self):
        self.run_login('failure', 'login_failed')
        self.run_login('bad_url', 'login_failed')

    def test_auth_urls_restrict_host_scheme_and_credentials(self):
        for value in ('https://chatgpt.com/auth?state=abc', 'https://auth.openai.com/oauth/authorize'):
            self.assertEqual(valid_login_url(value), value)
        for value in (None, '', 'http://auth.openai.com/', 'file:///secret', 'javascript:alert(1)',
                      'https://auth.openai.com.evil.invalid/', 'https://auth.openai.com@evil.invalid/',
                      'https://evil.invalid@auth.openai.com/', 'https://auth.openai.com:999/',
                      'https://auth.openai.com\\@evil.invalid/', 'https://auth.openai.com/\n'):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                valid_login_url(value)

    def test_worker_distinguishes_missing_cli_and_signed_in_without_quota(self):
        for error, signed in (('missing_cli', False), ('no_week', True)):
            events = queue.Queue()
            reader = Mock()
            if signed:
                reader.account.return_value = {'email':'test@example.invalid'}
                reader.read.side_effect = ValueError(error)
            else:
                reader.account.side_effect = RuntimeError(error)
            worker = ConnectionWorker(events, reader_factory=lambda **kw: reader)
            worker.run()
            entries = list(events.queue)
            self.assertIn(('error', error, signed), entries)
            self.assertFalse(any(e[0] == 'connected' for e in entries))
            self.assertEqual(entries[-1], ('finished',))
            reader.login.assert_not_called()
            reader.close.assert_called_once()


class FakeWorker:
    instances = []

    def __init__(self, events, login=False):
        self.events, self.login = events, login
        self.stopped = False
        self.__class__.instances.append(self)

    def start(self):
        pass

    def stop(self):
        self.stopped = True

    def join(self, timeout=None):
        pass

    def is_alive(self):
        return False


class ConnectionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeWorker.instances.clear()
        self.dialog = ConnectionDialog(worker_factory=FakeWorker)
        self.dialog.show()
        self.app.processEvents()

    def tearDown(self):
        self.dialog.shutdown()
        self.dialog.busy = False
        self.dialog.reject()
        self.dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def emit(self, *events):
        for event in events:
            self.dialog.events.put(event)
        self.dialog.consume()
        self.app.processEvents()

    def test_no_browser_without_click_and_existing_sign_in_is_reused(self):
        with patch('connection_ui.QDesktopServices.openUrl') as browser:
            self.assertFalse(FakeWorker.instances[0].login)
            self.emit(('account', 'test@example.invalid'),
                ('connected', 'identity', {'used':42, 'reset':2000000000}), ('finished',))
            self.assertIn('42%', self.dialog.status.text())
            self.assertTrue(self.dialog.connected)
            browser.assert_not_called()

    def test_missing_cli_shows_guide_without_starting_installer(self):
        with patch('connection_ui.QDesktopServices.openUrl', return_value=True) as browser:
            self.emit(('error', 'missing_cli', False), ('finished',))
            self.assertTrue(self.dialog.guide.isVisible())
            self.assertFalse(self.dialog.connect_button.isEnabled())
            browser.assert_not_called()
            self.dialog.guide.click()
            self.assertEqual(browser.call_args.args[0].toString(), 'https://developers.openai.com/codex/cli/')

    def test_explicit_login_opens_browser_and_handles_browser_failure(self):
        self.emit(('error', 'sign_in', False), ('finished',))
        with patch('connection_ui.QDesktopServices.openUrl', return_value=False) as browser:
            self.dialog.connect_button.click()
            self.assertTrue(FakeWorker.instances[-1].login)
            browser.assert_not_called()
            self.emit(('browser', 'https://auth.openai.com/oauth/authorize?state=test'))
            browser.assert_called_once()
            self.assertEqual(self.dialog.detail.text(), tr('en','browser_failed'))
            self.dialog.reopen.click()
            self.assertEqual(browser.call_count, 2)

    def test_close_cancels_without_opening_late_browser_or_claiming_success(self):
        ready = Mock()
        self.dialog.usage_ready.connect(ready)
        with patch('connection_ui.QDesktopServices.openUrl') as browser:
            self.dialog.close()
            self.assertTrue(FakeWorker.instances[0].stopped)
            self.emit(('browser', 'https://auth.openai.com/oauth/authorize'),
                ('connected', 'id', {'used':42}), ('finished',))
            self.assertFalse(self.dialog.isVisible())
            browser.assert_not_called()
            ready.assert_not_called()

    def test_signed_in_without_weekly_data_is_not_connected(self):
        self.emit(('account', '<b>test@example.invalid</b>'), ('error', 'no_week', True), ('finished',))
        self.assertFalse(self.dialog.connected)
        self.assertEqual(self.dialog.status.text(), tr('en','signed_in_no_quota'))
        self.assertEqual(self.dialog.account.textFormat(), Qt.TextFormat.PlainText)
        self.assertTrue(self.dialog.check_button.isEnabled())

    def test_setup_is_translated_in_all_languages(self):
        for lang in LANGUAGES:
            dialog = ConnectionDialog(lang, worker_factory=FakeWorker)
            try:
                self.assertEqual(dialog.connect_button.text(), tr(lang,'connect_chatgpt'))
                self.assertIn(tr(lang,'connection'), dialog.windowTitle())
            finally:
                dialog.shutdown()
                dialog.busy = False
                dialog.reject()
                dialog.deleteLater()

    def test_settings_connection_action_does_not_save_or_close_settings(self):
        settings = ui.Settings(DEFAULTS.copy())
        opened = Mock()
        settings.connection_requested.connect(opened)
        settings.show()
        try:
            settings.thresholds.setText('60, 85')
            settings.connection_button.click()
            opened.assert_called_once_with()
            self.assertTrue(settings.isVisible())
            self.assertEqual(settings.thresholds.text(), '60, 85')
            self.assertFalse(hasattr(settings, 'result_cfg'))
        finally:
            settings.close()
            settings.deleteLater()

    def test_controller_isolates_old_account_replies_and_restarts_reader(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(ui, 'DATA', Path(folder)), \
                patch.object(ui.QSystemTrayIcon, 'show'), patch.object(ui.QSystemTrayIcon, 'setIcon'), \
                patch.object(ui.QTimer, 'singleShot'):
            controller = ui.Controller(self.app, demo=True)
            controller.timer.stop()
            old_queue = controller.events
            old_worker = FakeWorker(old_queue)
            controller.worker = old_worker
            dialog = Mock()
            dialog.usage_ready = Mock()
            dialog.exec.side_effect = lambda: controller.connection_ready('new-account',
                {'used':42, 'reset':2000000000})
            new_worker = FakeWorker(queue.Queue())
            try:
                with patch.object(ui, 'ConnectionDialog', return_value=dialog), \
                        patch.object(ui, 'Poller', return_value=new_worker):
                    controller.connect_account()
                self.assertTrue(old_worker.stopped)
                old_queue.put(('usage', 'old-account', {'used':99, 'reset':2000000000}))
                controller.consume()
                self.assertEqual(controller.identity, 'new-account')
                self.assertFalse(controller.demo)
                self.assertIs(controller.worker, new_worker)
            finally:
                controller.shutdown()
                self.app.aboutToQuit.disconnect(controller.shutdown)
                controller.toast.close()
                controller.menu.close()

    def test_first_missing_login_offers_setup_once_and_network_errors_stay_quiet(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(ui, 'DATA', Path(folder)), \
                patch.object(ui.QSystemTrayIcon, 'show'), patch.object(ui.QSystemTrayIcon, 'setIcon'), \
                patch.object(ui.QTimer, 'singleShot') as schedule:
            controller = ui.Controller(self.app, demo=True)
            controller.timer.stop()
            controller.demo = False
            schedule.reset_mock()
            try:
                controller.events.put(('error', 'connection_failed'))
                controller.consume()
                schedule.assert_not_called()
                for _ in range(2):
                    controller.events.put(('error', 'sign_in'))
                    controller.consume()
                schedule.assert_called_once_with(0, controller.connect_account)
            finally:
                controller.shutdown()
                self.app.aboutToQuit.disconnect(controller.shutdown)
                controller.toast.close()
                controller.menu.close()


if __name__ == '__main__':
    unittest.main()
