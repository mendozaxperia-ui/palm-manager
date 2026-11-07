# Dependency licensing review (source-only distribution)

Palm Manager itself is distributed as source under **GPL-3.0-only**, to the extent applicable rights permit. The complete GNU GPL v3 license text is in `LICENSE`.

The following are *external dependencies*, **not included in this repository or its source archive**. Use the packages and license notices supplied by your Linux distribution.

| Component | Relationship | License / notes |
| --- | --- | --- |
| PyQt6 (Riverbank Computing) | Python GUI library imported at runtime | GPL v3 or separate commercial license. Palm Manager uses the GPL-compatible source-release route. |
| Qt 6 | GUI toolkit used through PyQt6 | Many relevant modules available under LGPL v3 / GPL v3; other Qt modules may use other licenses. |
| dbus-python | Python D-Bus bindings imported at runtime | MIT/Expat per project metadata; check installed version's notice. |
| PyGObject / GLib | Python introspection and GLib main loop | LGPL-family licenses for relevant libraries; inspect installed package notices. |
| BlueZ | External Linux Bluetooth service accessed through D-Bus | Multiple GPL/LGPL-family component licenses; not redistributed here. |
| socat | Separate executable launched by `bridge.py` | Common Linux packages identify socat as GPL-2.0-only. It is called as an external program, not bundled or linked here. |
| pilot-link / pilot-xfer | Separate executable launched by `palm_manager.py` | pilot-xfer utilities use GPL licensing (some versions/components GPLv2), libraries are LGPL; the external program is not bundled or linked here. |

Sources and documentation:

- PyQt6: https://en.riverbankcomputing.com/software/pyqt/intro
- Qt: https://doc.qt.io/qt-6/licensing.html
- dbus-python: https://dbus.freedesktop.org/doc/dbus-python/
- PyGObject: https://pygobject.gnome.org/
- BlueZ: https://www.bluez.org/
- socat packaging: https://packages.fedoraproject.org/pkgs/socat/socat/
- pilot-link packaging: https://packages.fedoraproject.org/pkgs/pilot-link/pilot-link/

**Scope of review:** The source distribution contains only project-authored Python scripts, shell launcher, documentation, and the GPL v3 text. It does not copy or bundle proprietary Palm OS programs, ROMs, other projects' source code, or third-party executables. Merely invoking an external GPLv2 tool as a separate program is different from copying or linking its code into the GPLv3 project. Distribution of **binary bundles or AppImages** will require a fresh license and notice audit covering everything bundled, including Qt libraries, the LGPL's applicable requirements, and each external utility.

**Authorship limitation:** Some project material was generated with AI under human direction. Copyrightability of specific AI-generated material may vary by jurisdiction. The project's license states the intended permission for copyrightable contributions, not a guarantee of exclusive ownership or an independent legal opinion.

This is a practical compliance review, not legal advice or a certification. Before public release, recheck upstream notices against the exact versions packaged.
