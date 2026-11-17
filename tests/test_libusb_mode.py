import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication, QMessageBox
from palm_manager import PalmManager

class LibusbModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_direct_mode_launch_and_original_modes(self):
        win = PalmManager()
        self.assertEqual(win.mode.itemText(2), "USB cable")
        self.assertEqual(win.mode.itemText(3), "USB cable (manual port)")
        self.assertIn("libusb", win.mode.itemText(4))
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.prc"
            f.write_bytes(b"test; do not install")
            win.files.addItem(str(f))
            win.mode.setCurrentIndex(4)
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), patch.object(win, "start_transfer") as transfer:
                win.start_install()
                transfer.assert_called_once_with("usb:", [str(f)])
                self.assertFalse(win.usb_timer.isActive())
        win.set_running(False)
        win.close()

    def test_automatic_mode_keeps_usb_wait_and_bluetooth_bridge(self):
        win = PalmManager()
        win.files.addItem("/tmp/only_mocks.prc")
        win.mode.setCurrentIndex(0)
        with patch("palm_manager.Path.is_file", return_value=True), \
             patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(win, "start_bridge") as bridge, \
             patch.object(win, "start_usb_wait") as usb:
            win.start_install()
            bridge.assert_called_once()
            usb.assert_called_once_with(["/tmp/only_mocks.prc"], automatic=True)
        win.set_running(False)
        win.close()

    def test_bluetooth_only_does_not_launch_usb_detection(self):
        win = PalmManager()
        win.files.addItem("/tmp/only_mocks.prc")
        win.mode.setCurrentIndex(1)
        with patch("palm_manager.Path.is_file", return_value=True), \
             patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(win, "start_bridge") as bridge, \
             patch.object(win, "start_usb_wait") as usb:
            win.start_install()
            bridge.assert_called_once()
            usb.assert_not_called()
        win.set_running(False)
        win.close()

    def test_direct_usb_is_classified_usb(self):
        win = PalmManager()
        with patch("palm_manager.QProcess") as process:
            win.start_transfer("usb:", [])
            self.assertEqual(win.active_transport, "USB")
            process.return_value.start.assert_called_once()
        win.set_running(False)
        win.close()

if __name__ == "__main__":
    unittest.main()
