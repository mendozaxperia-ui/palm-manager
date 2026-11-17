"""Automatic HotSync must remain usable when Bluetooth is unavailable."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QApplication
from palm_manager import PalmManager


class AutomaticFallbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = PalmManager()
        self.win.set_running(True)

    def tearDown(self):
        self.win.usb_timer.stop()
        self.win.set_running(False)
        self.win.close()

    def test_automatic_bridge_exit_keeps_usb_detection_active(self):
        self.win.mode.setCurrentIndex(0)
        self.win.usb_timer.start()
        with patch.object(self.win, "finish") as finish:
            self.win.on_bridge_finished(1, QProcess.ExitStatus.NormalExit)
            finish.assert_not_called()
        self.assertTrue(self.win.running)
        self.assertTrue(self.win.usb_timer.isActive())
        self.assertIn("Continuing to wait for USB", self.win.log.toPlainText())
        self.assertIn("USB: waiting", self.win.status.text())

    def test_automatic_bridge_error_and_exit_are_reported_once(self):
        self.win.mode.setCurrentIndex(0)
        self.win.usb_timer.start()
        self.win.bridge = QProcess(self.win)
        with patch.object(self.win.bridge, "errorString", return_value="No BlueZ service"), \
             patch.object(self.win, "finish") as finish:
            self.win.on_bridge_error(QProcess.ProcessError.FailedToStart)
            self.win.on_bridge_finished(1, QProcess.ExitStatus.CrashExit)
            finish.assert_not_called()
        self.assertEqual(self.win.log.toPlainText().count("Continuing to wait for USB"), 1)

    def test_bluetooth_only_bridge_exit_still_fails(self):
        self.win.mode.setCurrentIndex(1)
        with patch.object(self.win, "finish") as finish:
            self.win.on_bridge_finished(1, QProcess.ExitStatus.NormalExit)
            finish.assert_called_once_with(False)

    def test_bridge_exit_after_usb_selected_is_ignored(self):
        self.win.mode.setCurrentIndex(0)
        self.win.usb_timer.start()
        self.win.active_transport = "USB"
        with patch.object(self.win, "finish") as finish:
            self.win.on_bridge_finished(1, QProcess.ExitStatus.NormalExit)
            finish.assert_not_called()
        self.assertEqual(self.win.log.toPlainText(), "")

    def test_bridge_exit_after_bluetooth_connected_is_failure(self):
        self.win.mode.setCurrentIndex(0)
        self.win.usb_timer.start()
        self.win.bt_connected = True
        with patch.object(self.win, "finish") as finish:
            self.win.on_bridge_finished(1, QProcess.ExitStatus.NormalExit)
            finish.assert_called_once_with(False)

    def test_bluetooth_pilot_is_stopped_before_usb_fallback(self):
        self.win.mode.setCurrentIndex(0)
        self.win.usb_timer.start()
        self.win.active_transport = "Bluetooth"
        transfer = QProcess(self.win)
        transfer.finished.connect(self.win.on_transfer_finished)
        transfer.errorOccurred.connect(self.win.on_transfer_error)
        transfer.readyReadStandardOutput.connect(self.win.on_transfer_output)
        self.win.transfer = transfer
        with patch.object(self.win, "finish") as finish:
            self.win.on_bridge_finished(1, QProcess.ExitStatus.NormalExit)
            finish.assert_not_called()
        self.assertIsNone(self.win.transfer)
        self.assertIsNone(self.win.active_transport)
        self.assertTrue(self.win.usb_timer.isActive())


if __name__ == "__main__":
    unittest.main()
