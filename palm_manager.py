#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Palm Manager: simple PRC/PDB installer for USB or Bluetooth HotSync."""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QProcess, QSettings, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout,
    QWidget,
)

BASE = Path(__file__).resolve().parent
BRIDGE = BASE / "bridge.py"
PORT_BT = "/tmp/palm-hotsync"
PALM_USB_VENDOR = "0830"
PALM_USB_PRODUCT = "0060"
PORT_USB = "/dev/ttyUSB1"  # Legacy fallback/reference; not selected in automatic mode.


def detect_palm_usb_port(sys_root=Path("/sys/class/tty")):
    """Find the Palm USB serial *data* port, even if Linux renumbers it.

    The Tungsten T3 exposes two ttyUSB interfaces; pilot-link uses the second.
    Traverse sysfs to distinguish Palm ports from unrelated USB serial devices.
    """
    groups = {}
    for entry in sys_root.glob("ttyUSB*"):
        device = entry / "device"
        if not device.exists():
            continue
        parent = device.resolve()
        while parent != parent.parent:
            vendor, product = parent / "idVendor", parent / "idProduct"
            if vendor.is_file() and product.is_file():
                try:
                    if (vendor.read_text().strip().lower() == PALM_USB_VENDOR
                            and product.read_text().strip().lower() == PALM_USB_PRODUCT):
                        number = int(entry.name.removeprefix("ttyUSB"))
                        groups.setdefault(parent, []).append((number, str(Path("/dev") / entry.name)))
                except (OSError, ValueError):
                    pass
                break
            parent = parent.parent
    # A fully enumerated Palm presents a pair of serial interfaces.
    pairs = [sorted(ports) for ports in groups.values() if len(ports) >= 2]
    return max(pairs, key=lambda ports: ports[-1][0])[-1][1] if pairs else None


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
        self.mode.addItems(["Automatic (Bluetooth or USB)", "Bluetooth", "USB cable"])
        row.addWidget(self.mode)
        row.addStretch()
        layout.addLayout(row)

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
        ]
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
        else:
            self.start_usb_wait(paths)

    def start_usb_wait(self, paths, automatic=False):
        self.usb_paths = paths
        self.usb_wait_ticks = 0
        if automatic:
            self.say("Automatic mode: waiting for Bluetooth or USB HotSync.")
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

        port = detect_palm_usb_port()
        if port:
            self.say(f"Palm USB port detected: {port}. Selecting USB transfer.")
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
            self.usb_wait_ticks += 1
            # 200 ms ticks: automatic mode allows ten minutes to start
            # HotSync; manual USB retains its shorter two-minute timeout.
            if self.usb_wait_ticks >= (3000 if automatic else 600):
                self.usb_timer.stop()
                if automatic:
                    self.say("USB detection stopped after ten minutes; Bluetooth may still be available.")
                else:
                    self.say("Palm USB port did not appear within two minutes.")
                    self.finish(False)

    def start_bridge(self):
        self.bridge_buffer = ""
        self.bridge = QProcess(self)
        self.bridge.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.bridge.readyReadStandardOutput.connect(self.on_bridge_output)
        self.bridge.errorOccurred.connect(self.on_bridge_error)
        self.bridge.finished.connect(self.on_bridge_finished)
        self.bridge.start(sys.executable, ["-u", str(BRIDGE)])
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

    def on_bridge_error(self, error):
        if self.running and self.active_transport != "USB":
            self.say("Bluetooth server error: " + self.bridge.errorString())
            self.finish(False)

    def on_bridge_finished(self, code, status):
        if self.running and self.active_transport != "USB":
            self.say(f"Bluetooth server stopped unexpectedly (exit code {code}).")
            self.finish(False)

    def start_transfer(self, port, paths):
        self.active_transport = "USB" if port.startswith("/dev/ttyUSB") else "Bluetooth"
        self.transfer = QProcess(self)
        self.transfer.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.transfer.readyReadStandardOutput.connect(self.on_transfer_output)
        self.transfer.finished.connect(self.on_transfer_finished)
        self.transfer.errorOccurred.connect(self.on_transfer_error)
        timeout = "600" if self.mode.currentIndex() == 0 else "120"
        self.transfer.start("pilot-xfer", ["-p", port, "-t", timeout, "--install", *paths])
        self.say(f"pilot-xfer started for {self.active_transport}.")
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
            self.finish(code == 0 and status == QProcess.ExitStatus.NormalExit)

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
