#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Palm Manager: simple PRC/PDB installer for USB or Bluetooth HotSync."""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QProcess, QSettings, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QLineEdit, QVBoxLayout,
    QWidget,
)

BASE = Path(__file__).resolve().parent
BRIDGE = (Path(sys.executable).resolve().parent.parent / "PalmBridge" / "PalmBridge" if getattr(sys, "frozen", False) else BASE / "bridge.py")
PORT_BT = "/tmp/palm-hotsync"
PALM_USB_VENDOR = "0830"
PALM_USB_PRODUCT = "0060"
PORT_USB = "/dev/ttyUSB1"  # Legacy fallback/reference; not selected in automatic mode.
USB_PERMISSION_GRACE_SECONDS = 3.0  # udev may set group/mode after ttyUSB appears.


def inspect_palm_usb_port(sys_root=Path("/sys/class/tty"), dev_root=Path("/dev")):
    """Find a Palm USB serial data port, or explain why selection is unsafe.

    Prefer the kernel's visor driver, which handles several Palm-compatible
    manufacturers. Also accept Palm Inc.'s USB vendor ID when two ports exist.
    A matching USB serial port is not necessarily the *data* port: use the
    per-device port_number (1 on the known Tungsten T3), not global ttyUSB IDs.
    """
    devices = {}
    for entry in sorted(sys_root.glob("ttyUSB*")):
        if not entry.name.removeprefix("ttyUSB").isdigit():
            continue
        try:
            parent = (entry / "device").resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        usb_device = None
        visor_driver = False
        probe = parent
        while probe != probe.parent:
            try:
                driver = probe / "driver"
                if driver.is_symlink() and driver.resolve().name == "visor":
                    visor_driver = True
                vendor_file, product_file = probe / "idVendor", probe / "idProduct"
                if vendor_file.is_file() and product_file.is_file():
                    vendor = vendor_file.read_text().strip().lower()
                    product = product_file.read_text().strip().lower()
                    usb_device = (probe, vendor, product)
                    break
            except OSError:
                break
            probe = probe.parent
        if usb_device is None:
            continue
        usb_path, vendor, _ = usb_device
        # Match USB serial ports driven by visor, or Palm Inc. hardware.
        if not visor_driver and vendor != PALM_USB_VENDOR:
            continue
        number_file = parent / "port_number"
        try:
            port_number = int(number_file.read_text().strip()) if number_file.is_file() else None
        except (OSError, ValueError):
            port_number = None
        devices.setdefault(usb_path, []).append(
            (str(dev_root / entry.name), port_number, visor_driver))

    if not devices:
        return None, "No Palm USB serial port was detected."
    if len(devices) > 1:
        return None, "More than one Palm USB device was found. Select a port manually."

    ports = next(iter(devices.values()))
    # Only trust a single port belonging to the visor driver. Other Palm
    # vendor devices with one port may expose a non-HotSync interface.
    if len(ports) == 1:
        if ports[0][2]:
            return ports[0][0], None
        return None, "The USB device has no identifiable Palm data port."
    data_ports = [port for port, number, _ in ports if number == 1]
    if len(data_ports) == 1:
        return data_ports[0], None
    if len(ports) == 2 and all(number is None for _, number, _ in ports):
        # Older kernel layouts may omit port_number; the T3 data port is
        # the higher ttyUSB within its *own* USB device, never globally.
        return max((port for port, _, _ in ports),
                   key=lambda path: int(Path(path).name.removeprefix("ttyUSB"))), None
    return None, "Could not identify the Palm data port. Select it manually."


def detect_palm_usb_port(sys_root=Path("/sys/class/tty")):
    """Compatibility helper returning the safe automatic port, if any."""
    return inspect_palm_usb_port(sys_root)[0]


def usb_port_access_issue(port):
    """Do not request privileges; diagnose missing access instead."""
    if not os.access(port, os.R_OK | os.W_OK):
        return (f"No permission to access {port}. Your Linux user needs "
                "read/write access to this USB serial device. Check the "
                "device's group and udev permissions; do not run Palm Manager as root.")
    return None


def stop_process(proc):
    """Terminate a child and forcibly kill it if termination is ignored."""
    if proc is None or proc.state() == QProcess.ProcessState.NotRunning:
        return
    proc.terminate()
    QTimer.singleShot(700, lambda p=proc: p.kill()
                      if p.state() != QProcess.ProcessState.NotRunning else None)

HISTORY = Path.home() / ".local" / "state" / "palm-manager" / "history.jsonl"


class FileList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.setToolTip("Drag PRC or PDB files here.")

    def add_paths(self, paths):
        existing = {self.item(i).text() for i in range(self.count())}
        for path in paths:
            p = Path(path).expanduser().resolve()
            if p.is_file() and p.suffix.lower() in (".prc", ".pdb"):
                if str(p) not in existing:
                    self.addItem(str(p))
                    existing.add(str(p))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.add_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()


class PalmManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Palm Manager")
        self.resize(760, 560)
        self.bridge = None
        self.transfer = None
        self.running = False
        self.bridge_buffer = ""
        self.bridge_failure_reported = False
        self.usb_timer = QTimer(self)
        self.usb_timer.setInterval(200)
        self.usb_timer.timeout.connect(self.check_usb_port)
        self.usb_wait_ticks = 0
        self.usb_paths = []
        self.session_paths = []
        self.active_transport = None
        self.bt_connected = False
        self.settings = QSettings("PalmManager", "PalmManager")
        self.active_usb_port = None
        self.usb_disconnected_at = None
        self.usb_detection_issue = None
        self.usb_permission_port = None
        self.usb_permission_since = None
        self.setup_ui()

    def setup_ui(self):
        outer = QWidget()
        layout = QVBoxLayout(outer)
        self.setCentralWidget(outer)

        heading = QLabel("Palm Manager  🌴")
        heading.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Install Palm OS applications and databases (PRC/PDB)"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Connection:"))
        self.mode = QComboBox()
        self.mode.addItems([
            "Automatic (Bluetooth or USB)", "Bluetooth", "USB cable",
            "USB cable (manual port)", "USB direct (libusb, experimental)"
        ])
        row.addWidget(self.mode)
        row.addStretch()
        layout.addLayout(row)

        self.manual_port_row = QWidget()
        port_layout = QHBoxLayout(self.manual_port_row)
        port_layout.setContentsMargins(0, 0, 0, 0)
        port_layout.addWidget(QLabel("USB data port:"))
        self.usb_port = QLineEdit()
        self.usb_port.setPlaceholderText("/dev/ttyUSB1")
        self.usb_port.setToolTip("Enter the data port shown by Linux after starting USB HotSync (for example /dev/ttyUSB1).")
        port_layout.addWidget(self.usb_port)
        layout.addWidget(self.manual_port_row)

        layout.addWidget(QLabel("Files to install (drag and drop supported):"))
        self.files = FileList()
        layout.addWidget(self.files, stretch=2)
        file_buttons = QHBoxLayout()
        add = QPushButton("Add files…")
        add.clicked.connect(self.pick_files)
        remove = QPushButton("Remove selected")
        remove.clicked.connect(self.remove_selected)
        clear = QPushButton("Clear list")
        clear.clicked.connect(self.files.clear)
        file_buttons.addWidget(add)
        file_buttons.addWidget(remove)
        file_buttons.addWidget(clear)
        layout.addLayout(file_buttons)

        self.status = QLabel("Ready.")
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.install = QPushButton("Install to Palm")
        # Primary action: use the active Qt palette for light/dark theme support.
        self.install.setMinimumHeight(42)
        self.install.setStyleSheet("""
            QPushButton {
                background-color: palette(highlight);
                color: palette(highlighted-text);
                border: 1px solid palette(highlight);
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 18px;
            }
            QPushButton:disabled {
                background-color: palette(button);
                color: palette(mid);
                border-color: palette(mid);
            }
        """)
        self.install.clicked.connect(self.start_install)
        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.cancel_install)
        self.cancel.setEnabled(False)
        actions.addWidget(self.install)
        actions.addWidget(self.cancel)
        history_button = QPushButton("Installation history…")
        history_button.clicked.connect(self.show_history)
        actions.addWidget(history_button)
        layout.addLayout(actions)

        layout.addWidget(QLabel("Progress:"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=2)
        self.mode.currentIndexChanged.connect(self.update_mode_hint)
        self.update_mode_hint()

    def update_mode_hint(self):
        hints = [
            "Automatic: click Install, then start HotSync on your Palm (Bluetooth or USB).",
            "Bluetooth: click Install, then start Bluetooth HotSync on your Palm.",
            "USB: connect the cable, click Install, then start USB HotSync on your Palm.",
            "Manual USB: enter the Palm data port, click Install, then start USB HotSync.",
            "Direct USB: click Install first, then start USB HotSync. No /dev/ttyUSB port needed.",
        ]
        self.manual_port_row.setVisible(self.mode.currentIndex() == 3)
        self.status.setText(hints[self.mode.currentIndex()])

    def pick_files(self):
        directory = str(self.settings.value("last_file_directory", str(Path.home())))
        if not Path(directory).is_dir():
            directory = str(Path.home())
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PRC/PDB files", directory,
            "Palm files (*.prc *.pdb *.PRC *.PDB)"
        )
        if paths:
            self.files.add_paths(paths)
            self.settings.setValue("last_file_directory", str(Path(paths[0]).parent))

    def remove_selected(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))

    def say(self, message):
        self.log.appendPlainText(message.rstrip())

    def set_running(self, value):
        self.running = value
        self.install.setEnabled(not value)
        self.cancel.setEnabled(value)
        self.mode.setEnabled(not value)
        self.usb_port.setEnabled(not value)

    def start_install(self):
        if self.running:
            return
        paths = [self.files.item(i).text() for i in range(self.files.count())]
        if not paths:
            QMessageBox.information(self, "No files selected", "Add PRC/PDB files first.")
            return
        if not all(Path(p).is_file() for p in paths):
            QMessageBox.warning(self, "Missing file", "One or more selected files no longer exist.")
            return
        if self.mode.currentIndex() == 3:
            requested_port = self.usb_port.text().strip()
            if not re.fullmatch(r"/dev/ttyUSB[0-9]+", requested_port):
                QMessageBox.warning(
                    self, "Invalid USB port",
                    "Enter a Linux USB serial port such as /dev/ttyUSB1. "
                    "Check which port your Palm creates when USB HotSync starts."
                )
                return
        answer = QMessageBox.question(
            self, "Confirm installation",
            f"Install {len(paths)} file(s) via "
            f"{self.mode.currentText()}?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Forget the previous completed transfer before starting another session.
        self.transfer = None
        self.active_transport = None
        self.bt_connected = False
        self.active_usb_port = None
        self.usb_disconnected_at = None
        self.session_paths = list(paths)
        self.log.clear()
        self.say(f"Preparing to install {len(paths)} file(s).")
        self.set_running(True)
        if self.mode.currentIndex() == 0:
            self.start_bridge()
            self.start_usb_wait(paths, automatic=True)
        elif self.mode.currentIndex() == 1:
            self.start_bridge()
        elif self.mode.currentIndex() == 2:
            self.start_usb_wait(paths)
        elif self.mode.currentIndex() == 3:
            self.start_usb_wait(paths, manual_port=requested_port)
        else:
            # libusb uses raw USB, without waiting for any ttyUSB node.
            self.say("Experimental direct USB mode (libusb) selected.")
            self.say("Waiting on usb:. Start USB HotSync on your Palm now.")
            self.say("Direct USB requires access to the raw USB device. "
                     "If it fails, the visor kernel driver or USB permissions "
                     "may prevent libusb access. Palm Manager will not modify "
                     "your system settings.")
            self.start_transfer("usb:", paths)

    def start_usb_wait(self, paths, automatic=False, manual_port=None):
        self.usb_paths = paths
        self.requested_usb_port = manual_port
        self.usb_wait_ticks = 0
        self.usb_detection_issue = None
        self.usb_permission_port = None
        self.usb_permission_since = None
        if automatic:
            self.say("Automatic mode: waiting for Bluetooth or USB HotSync.")
        elif manual_port:
            self.status.setText(f"USB: waiting for {manual_port}…")
            self.say(f"Manual USB port {manual_port}: start USB HotSync on your Palm.")
        else:
            self.status.setText("USB: waiting for HotSync on your Palm…")
            self.say("Start USB HotSync on your Palm. Detecting the Palm USB port…")
        self.usb_timer.start()
        self.check_usb_port()

    def check_usb_port(self):
        if not self.running:
            self.usb_timer.stop()
            return
        if self.active_transport == "USB":
            # The port can disappear when a session ends normally; give the
            # transfer a short chance to exit before treating this as failure.
            if self.active_usb_port and not Path(self.active_usb_port).exists():
                if self.usb_disconnected_at is None:
                    self.usb_disconnected_at = time.monotonic()
                elif time.monotonic() - self.usb_disconnected_at > 2.0:
                    self.say("Palm USB port disappeared before the transfer completed.")
                    self.finish(False)
            else:
                self.usb_disconnected_at = None
            return
        automatic = self.mode.currentIndex() == 0
        if automatic and self.bt_connected:
            self.usb_timer.stop()
            return

        # Manual mode bypasses device detection. Automatic mode selects only
        # a confidently identified Palm serial data port, never an unrelated
        # USB serial device.
        if self.mode.currentIndex() == 3:
            port = (self.requested_usb_port if Path(self.requested_usb_port).exists()
                    else None)
        else:
            port, self.usb_detection_issue = inspect_palm_usb_port()
        if port:
            issue = usb_port_access_issue(port)
            if issue:
                # A newly enumerated ttyUSB node can briefly have root-only
                # permissions before udev applies its final group and mode.
                # Wait without requiring admin rights or blocking Qt's event loop.
                now = time.monotonic()
                if self.usb_permission_port != port:
                    self.usb_permission_port = port
                    self.usb_permission_since = now
                    self.say(f"USB port {port} found; waiting for device permissions…")
                    self.status.setText("USB: waiting for device permissions…")
                elif now - self.usb_permission_since >= USB_PERMISSION_GRACE_SECONDS:
                    self.say(issue)
                    self.finish(False)
                return
            self.usb_permission_port = None
            self.usb_permission_since = None
            self.say(f"USB port selected: {port}. Starting transfer.")
            self.active_usb_port = port
            if automatic:
                old = self.transfer
                if old is not None:
                    old.finished.disconnect(self.on_transfer_finished)
                    old.errorOccurred.disconnect(self.on_transfer_error)
                    old.readyReadStandardOutput.disconnect(self.on_transfer_output)
                    stop_process(old)
                self.transfer = None
                stop_process(self.bridge)
            self.start_transfer(port, self.usb_paths)
        else:
            # A vanished device must not inherit the previous port's
            # permission grace period if USB reconnects.
            self.usb_permission_port = None
            self.usb_permission_since = None
            self.usb_wait_ticks += 1
            # 200 ms ticks: automatic mode allows ten minutes to start
            # HotSync; manual USB retains its shorter two-minute timeout.
            if self.usb_wait_ticks >= (3000 if automatic else 600):
                self.usb_timer.stop()
                if automatic:
                    self.say("USB detection stopped after ten minutes; Bluetooth may still be available.")
                else:
                    if self.mode.currentIndex() == 3:
                        self.say(f"Manual USB port {self.requested_usb_port} did not appear within two minutes.")
                    else:
                        self.say("Palm USB port did not appear within two minutes.")
                        self.say(self.usb_detection_issue or
                                 "Check the USB cable and start USB HotSync.")
                        self.say("In a virtual machine, attach the Palm USB device "
                                 "to the guest while HotSync is active.")
                    self.finish(False)

    def start_bridge(self):
        self.bridge_buffer = ""
        self.bridge_failure_reported = False
        self.bridge = QProcess(self)
        self.bridge.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.bridge.readyReadStandardOutput.connect(self.on_bridge_output)
        self.bridge.errorOccurred.connect(self.on_bridge_error)
        self.bridge.finished.connect(self.on_bridge_finished)
        self.bridge.start(str(BRIDGE), [] ) if getattr(sys, "frozen", False) else self.bridge.start(sys.executable, ["-u", str(BRIDGE)])
        self.status.setText("Starting Bluetooth server…")

    def on_bridge_output(self):
        if not self.bridge:
            return
        self.bridge_buffer += bytes(self.bridge.readAllStandardOutput()).decode(errors="replace")
        while "\n" in self.bridge_buffer:
            line, self.bridge_buffer = self.bridge_buffer.split("\n", 1)
            if "HotSync ready:" in line and self.transfer is None and self.running and self.active_transport != "USB":
                self.say("Bluetooth port ready; starting pilot-xfer.")
                self.start_transfer(PORT_BT, self.session_paths)
            elif "Palm connected:" in line and self.active_transport != "USB":
                self.bt_connected = True
                self.usb_timer.stop()
                self.say("Palm connected via Bluetooth.")
            elif "BlueZ error:" in line or "Traceback" in line:
                self.say(line)

    def handle_bridge_failure(self, detail):
        if not self.running or self.active_transport == "USB" or self.bridge_failure_reported:
            return
        self.bridge_failure_reported = True
        self.say(detail)
        # An unavailable Bluetooth service must not prevent automatic USB
        # detection. In particular, headless VMs often have no BlueZ adapter.
        if self.mode.currentIndex() == 0 and self.usb_timer.isActive() and not self.bt_connected:
            if self.active_transport == "Bluetooth" and self.transfer is not None:
                # pilot-xfer may already be waiting on the now-defunct BT PTY.
                old = self.transfer
                old.finished.disconnect(self.on_transfer_finished)
                old.errorOccurred.disconnect(self.on_transfer_error)
                old.readyReadStandardOutput.disconnect(self.on_transfer_output)
                self.transfer = None
                stop_process(old)
                self.active_transport = None
            self.say("Bluetooth unavailable. Continuing to wait for USB HotSync.")
            self.status.setText("USB: waiting for HotSync on your Palm…")
            return
        self.finish(False)

    def on_bridge_error(self, error):
        if self.bridge is not None:
            self.handle_bridge_failure("Bluetooth server error: " + self.bridge.errorString())

    def on_bridge_finished(self, code, status):
        self.handle_bridge_failure(f"Bluetooth server stopped unexpectedly (exit code {code}).")

    def start_transfer(self, port, paths):
        self.active_transport = "USB" if port == "usb:" or port.startswith("/dev/ttyUSB") else "Bluetooth"
        self.transfer = QProcess(self)
        self.transfer.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.transfer.readyReadStandardOutput.connect(self.on_transfer_output)
        self.transfer.finished.connect(self.on_transfer_finished)
        self.transfer.errorOccurred.connect(self.on_transfer_error)
        timeout = "600" if self.mode.currentIndex() == 0 else "120"
        self.transfer.start("pilot-xfer", ["-p", port, "-t", timeout, "--install", *paths])
        self.say(f"pilot-xfer started for {self.active_transport} (port: {port}).")
        self.status.setText("Waiting for Palm HotSync…")
        self.say("Start HotSync on your Palm if you haven't already.")

    def on_transfer_output(self):
        if self.transfer:
            data = bytes(self.transfer.readAllStandardOutput()).decode(errors="replace")
            self.say(data)

    def on_transfer_finished(self, code, status):
        if self.sender() is not self.transfer:
            return
        self.on_transfer_output()
        if self.running:
            success = code == 0 and status == QProcess.ExitStatus.NormalExit
            if not success:
                if self.active_transport == "USB":
                    self.say("USB HotSync failed. Verify that the Palm is "
                             "connected to this computer (or VM), the user "
                             "has access to its USB port, and no other "
                             "HotSync program is running.")
                    if self.mode.currentIndex() == 4:
                        self.say("Direct libusb may conflict with the visor "
                                 "driver. Try the regular USB cable mode "
                                 "before changing system settings.")
                else:
                    self.say("Bluetooth HotSync failed. Check pairing, "
                             "the Bluetooth connection and any other "
                             "running HotSync applications.")
            self.finish(success)

    def on_transfer_error(self, error):
        if self.running and self.sender() is self.transfer:
            self.say("pilot-xfer error: " + self.transfer.errorString())
            self.finish(False)

    def cancel_install(self):
        if self.running:
            self.say("Cancelled by user.")
            self.finish(False)

    def finish(self, success):
        self.usb_timer.stop()
        self.set_running(False)
        self.status.setText("Installation complete." if success else "Installation did not complete.")
        self.say("✓ Done." if success else "Installation failed or was cancelled.")
        self.save_history(success)
        if success:
            self.files.clear()
            self.say("File list cleared after successful installation.")
        stop_process(self.transfer)
        stop_process(self.bridge)

    def save_history(self, success):
        record = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "transport": self.active_transport or self.mode.currentText(),
            "files": [Path(p).name for p in self.session_paths],
            "success": success,
            "log": self.log.toPlainText(),
        }
        try:
            HISTORY.parent.mkdir(parents=True, exist_ok=True)
            with HISTORY.open("a", encoding="utf-8") as history:
                history.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            self.say(f"Could not save installation history: {exc}")

    def show_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Installation history")
        dialog.resize(700, 470)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        rows = []
        try:
            if HISTORY.exists():
                for line in HISTORY.read_text(encoding="utf-8").splitlines():
                    record = json.loads(line)
                    result = "Success" if record.get("success") else "Failed / cancelled"
                    names = ", ".join(record.get("files", []))
                    rows.append(f'{record.get("timestamp", "?")}  |  {record.get("transport", "?")}  |  {result}\n{names}')
            view.setPlainText("\n\n".join(reversed(rows)) if rows else "No installations recorded yet.")
        except (OSError, ValueError) as exc:
            view.setPlainText(f"Could not read installation history: {exc}")
        layout.addWidget(view)
        dialog.exec()

    def closeEvent(self, event):
        if self.running:
            QMessageBox.information(self, "Installation in progress",
                                    "Please complete or cancel the installation first.")
            event.ignore()
            return
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PalmManager()
    window.show()
    sys.exit(app.exec())
