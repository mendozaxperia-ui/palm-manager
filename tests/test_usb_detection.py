import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from palm_manager import inspect_palm_usb_port, detect_palm_usb_port, usb_port_access_issue


class UsbDetectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sys_root = self.root / "sys" / "class" / "tty"
        self.dev_root = self.root / "dev"
        self.sys_root.mkdir(parents=True)
        self.dev_root.mkdir()
        self.visordriver = self.root / "drivers" / "visor"
        self.otherdriver = self.root / "drivers" / "ch341"
        self.visordriver.mkdir(parents=True)
        self.otherdriver.mkdir(parents=True)

    def device(self, name, vendor, product, ports, driver="visor"):
        usb = self.root / "devices" / name
        usb.mkdir(parents=True)
        (usb / "idVendor").write_text(vendor)
        (usb / "idProduct").write_text(product)
        interface = usb / f"{name}:1.0"
        interface.mkdir()
        if driver:
            (interface / "driver").symlink_to(
                self.visordriver if driver == "visor" else self.otherdriver)
        for tty_name, port_number in ports:
            serial = interface / tty_name
            serial.mkdir()
            if port_number is not None:
                (serial / "port_number").write_text(str(port_number))
            link = self.sys_root / tty_name
            link.mkdir()
            (link / "device").symlink_to(serial)
            (self.dev_root / tty_name).touch()

    def inspect(self):
        return inspect_palm_usb_port(self.sys_root, self.dev_root)

    def test_tungsten_t3_selects_port_one_not_highest_global_tty(self):
        self.device("palm", "0830", "0060", [("ttyUSB3", 0), ("ttyUSB7", 1)])
        self.device("unrelated", "1a86", "7523", [("ttyUSB99", 0)], driver="ch341")
        self.assertEqual(self.inspect(), (str(self.dev_root / "ttyUSB7"), None))

    def test_visordriver_recognizes_non_palm_vendor(self):
        self.device("sony", "054c", "0169", [("ttyUSB4", 0), ("ttyUSB5", 1)])
        self.assertEqual(self.inspect(), (str(self.dev_root / "ttyUSB5"), None))

    def test_visordriver_single_port_is_allowed(self):
        self.device("single", "0830", "0061", [("ttyUSB2", 0)])
        self.assertEqual(self.inspect(), (str(self.dev_root / "ttyUSB2"), None))

    def test_unrelated_serial_device_is_never_selected(self):
        self.device("unrelated", "1a86", "7523", [("ttyUSB9", 0)], driver="ch341")
        self.assertIsNone(self.inspect()[0])

    def test_ambiguous_multiple_palms_not_guessed(self):
        self.device("palm1", "0830", "0060", [("ttyUSB0", 0), ("ttyUSB1", 1)])
        self.device("palm2", "0830", "0061", [("ttyUSB2", 0), ("ttyUSB3", 1)])
        selected, issue = self.inspect()
        self.assertIsNone(selected)
        self.assertIn("More than one", issue)

    def test_two_ports_without_port_number_use_higher_within_device(self):
        self.device("palm", "0830", "0060", [("ttyUSB10", None), ("ttyUSB11", None)])
        self.assertEqual(self.inspect()[0], str(self.dev_root / "ttyUSB11"))

    def test_fallback_sorts_numeric_usb_suffix(self):
        self.device("palm", "0830", "0060", [("ttyUSB9", None), ("ttyUSB10", None)])
        self.assertEqual(self.inspect()[0], str(self.dev_root / "ttyUSB10"))

    def test_ambiguous_unlabeled_ports_not_guessed(self):
        self.device("palm", "0830", "0060", [
            ("ttyUSB0", None), ("ttyUSB1", None), ("ttyUSB2", None)])
        self.assertIsNone(self.inspect()[0])

    def test_unidentified_single_vendor_port_not_guessed(self):
        self.device("palm", "0830", "0060", [("ttyUSB3", None)], driver=None)
        self.assertIsNone(self.inspect()[0])

    def test_permission_message_does_not_request_root(self):
        with patch("palm_manager.os.access", return_value=False):
            msg = usb_port_access_issue("/dev/ttyUSB3")
        self.assertIn("No permission", msg)
        self.assertIn("/dev/ttyUSB3", msg)
        self.assertIn("do not run Palm Manager as root", msg)


if __name__ == "__main__":
    unittest.main()
