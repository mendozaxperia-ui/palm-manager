"""Regression tests for the short udev permission race on USB serial ports."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication

from palm_manager import PalmManager, USB_PERMISSION_GRACE_SECONDS


class UsbPermissionWaitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = PalmManager()
        self.win.mode.setCurrentIndex(2)  # USB cable, not libusb
        self.win.usb_paths = ["/tmp/example.prc"]
        self.win.set_running(True)

    def tearDown(self):
        self.win.usb_timer.stop()
        self.win.set_running(False)
        self.win.close()

    def test_waits_until_udev_grants_access_then_transfers_once(self):
        with patch("palm_manager.inspect_palm_usb_port", return_value=("/dev/ttyUSB1", None)), \
             patch("palm_manager.usb_port_access_issue", side_effect=[
                 "Permission denied", "Permission denied", None]), \
             patch("palm_manager.time.monotonic", side_effect=[100.0, 100.5]), \
             patch.object(self.win, "start_transfer") as transfer, \
             patch.object(self.win, "finish") as finish:
            self.win.check_usb_port()
            self.win.check_usb_port()
            transfer.assert_not_called()
            finish.assert_not_called()
            self.assertIn("waiting for device permissions", self.win.log.toPlainText())
            self.win.check_usb_port()
            transfer.assert_called_once_with("/dev/ttyUSB1", ["/tmp/example.prc"])
            finish.assert_not_called()
        self.assertIsNone(self.win.usb_permission_port)

    def test_persistent_denial_is_reported_after_grace_only(self):
        with patch("palm_manager.inspect_palm_usb_port", return_value=("/dev/ttyUSB1", None)), \
             patch("palm_manager.usb_port_access_issue", return_value="No permission to access /dev/ttyUSB1."), \
             patch("palm_manager.time.monotonic", side_effect=[
                 100.0, 100.0 + USB_PERMISSION_GRACE_SECONDS - 0.1,
                 100.0 + USB_PERMISSION_GRACE_SECONDS + 0.1]), \
             patch.object(self.win, "start_transfer") as transfer, \
             patch.object(self.win, "finish") as finish:
            self.win.check_usb_port()
            self.win.check_usb_port()
            finish.assert_not_called()
            self.win.check_usb_port()
            finish.assert_called_once_with(False)
            transfer.assert_not_called()
            self.assertIn("No permission", self.win.log.toPlainText())

    def test_unplugging_resets_grace_period(self):
        with patch("palm_manager.inspect_palm_usb_port", side_effect=[
                 ("/dev/ttyUSB1", None), (None, "No Palm USB serial port was detected."),
                 ("/dev/ttyUSB1", None)]), \
             patch("palm_manager.usb_port_access_issue", return_value="Permission denied"), \
             patch("palm_manager.time.monotonic", side_effect=[100.0, 200.0]), \
             patch.object(self.win, "start_transfer") as transfer, \
             patch.object(self.win, "finish") as finish:
            self.win.check_usb_port()
            self.win.check_usb_port()
            self.assertIsNone(self.win.usb_permission_since)
            self.win.check_usb_port()
            self.assertEqual(self.win.usb_permission_since, 200.0)
            finish.assert_not_called()
            transfer.assert_not_called()

    def test_bluetooth_only_is_unchanged(self):
        self.win.mode.setCurrentIndex(1)
        # USB waiting is never started by the Bluetooth-only path.
        self.assertFalse(self.win.usb_timer.isActive())


if __name__ == "__main__":
    unittest.main()
