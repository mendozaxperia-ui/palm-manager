# Dependency and license notes

The application imports PyQt6, dbus-python and PyGObject, and invokes BlueZ over D-Bus, socat, and pilot-xfer as separate system utilities.

- PyQt6: GPL v3 or commercial license; see https://riverbankcomputing.com/software/pyqt/intro
- Qt: separate licensing (many modules are LGPL); see https://www.qt.io/licensing/
- BlueZ: project licenses; see https://www.bluez.org/
- dbus-python: project license; see https://dbus.freedesktop.org/doc/dbus-python/
- PyGObject: project license; see https://pygobject.gnome.org/
- socat: project license; see http://www.dest-unreach.org/socat/
- pilot-link: project licensing varies by component; see upstream project sources.

This archive distributes **none** of these third-party dependencies. Their licenses and notices remain governed by the installed packages. Recheck bundled-dependency obligations before creating an AppImage or other binary distribution.

The `bridge.py` and `palm_manager.py` sources in this archive are newly prepared for this project; no Palm OS ROM, commercial application binaries, or system history is included.
