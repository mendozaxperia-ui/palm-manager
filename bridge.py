#!/usr/bin/env python3
"""Bluetooth HotSync bridge: create a PTY before the Palm connects."""
import os
import pty
import signal
import subprocess
import termios
import tty

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

PORT = "/tmp/palm-hotsync"
PROFILE_PATH = "/org/palm/SerialProfile"
SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"

# Create the PTY once so pilot-xfer can open it before Bluetooth connects.
master, slave = pty.openpty()
tty.setraw(slave)
slave_name = os.ttyname(slave)
os.chmod(slave_name, 0o660)
if os.path.lexists(PORT):
    if not os.path.islink(PORT):
        raise RuntimeError(f"Refusing to replace non-symlink {PORT}")
    os.unlink(PORT)
os.symlink(slave_name, PORT)

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
loop = GLib.MainLoop()


class PalmProfile(dbus.service.Object):
    def __init__(self):
        super().__init__(bus, PROFILE_PATH)
        self.bridge = None

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}")
    def NewConnection(self, device, fd, properties):
        bt_fd = fd.take()
        print(f"Palm connected: {device}; RFCOMM fd={bt_fd}", flush=True)
        if self.bridge and self.bridge.poll() is None:
            os.close(bt_fd)
            print("Connection refused: bridge already active", flush=True)
            return
        try:
            self.bridge = subprocess.Popen(
                ["socat", "-d", "-d", "-x", f"FD:{bt_fd}", f"FD:{master}"],
                pass_fds=(bt_fd, master),
            )
            print(f"Bridge PID={self.bridge.pid}", flush=True)
        finally:
            os.close(bt_fd)

    @dbus.service.method("org.bluez.Profile1", in_signature="o")
    def RequestDisconnection(self, device):
        print("Palm disconnected", flush=True)
        self.stop_bridge()

    @dbus.service.method("org.bluez.Profile1")
    def Release(self):
        print("Bluetooth profile released", flush=True)
        self.stop_bridge()
        loop.quit()

    def stop_bridge(self):
        if self.bridge and self.bridge.poll() is None:
            self.bridge.terminate()
            try:
                self.bridge.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.bridge.kill()
                self.bridge.wait()
        self.bridge = None


profile = PalmProfile()
manager = dbus.Interface(
    bus.get_object("org.bluez", "/org/bluez"),
    "org.bluez.ProfileManager1",
)
options = {
    "Name": dbus.String("Palm Manager HotSync"),
    "Role": dbus.String("server"),
    "Channel": dbus.UInt16(3),
    "RequireAuthentication": dbus.Boolean(False),
    "RequireAuthorization": dbus.Boolean(False),
}

signal.signal(signal.SIGINT, lambda *_: loop.quit())
signal.signal(signal.SIGTERM, lambda *_: loop.quit())
registered = False
try:
    manager.RegisterProfile(PROFILE_PATH, SPP_UUID, options)
    registered = True
    print(f"HotSync ready: {PORT} -> {slave_name}", flush=True)
    print("Start pilot-xfer now; then press HotSync on the Palm.", flush=True)
    loop.run()
except dbus.DBusException as error:
    print(f"BlueZ error: {error}", flush=True)
finally:
    profile.stop_bridge()
    if registered:
        try:
            manager.UnregisterProfile(PROFILE_PATH)
        except dbus.DBusException:
            pass
    if os.path.islink(PORT) and os.readlink(PORT) == slave_name:
        os.unlink(PORT)
    os.close(master)
    os.close(slave)
    print("Bluetooth server stopped", flush=True)
