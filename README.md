# Palm Manager for Linux

A small PyQt6 application for installing Palm OS PRC and PDB files over Bluetooth or USB. Developed and tested with a Palm Tungsten T3 on Manjaro Linux.

> **AI-assisted development:** This project was designed, developed and tested by its human maintainer in collaboration with OpenAI ChatGPT, which generated and edited substantial portions of the source code and documentation. The maintainer directed the work and verified transfers on real hardware. The project does not claim to be hand-written or independently audited. See [AUTHORS.md](AUTHORS.md).

## Features

- Install one or several PRC/PDB files in a single HotSync session.
- **Automatic (default):** prepare Bluetooth, detect the current Palm USB serial port, then use whichever connection is actually initiated. After Bluetooth connects, USB detection stops. Manual Bluetooth and USB modes remain available.
- Clear the file queue after a successful installation; retain it after failure.
- Show pilot-link's text progress and store installation history locally.
- Installation only: no PIM/calendar/contact synchronization.

## Requirements

Linux with Python 3, PyQt6, python-dbus, PyGObject/GLib, BlueZ, `socat` and `pilot-xfer` (pilot-link). Your user must be able to access the Palm USB serial device (typically the `uucp` or `dialout` group). Distribution package names may differ.

For Bluetooth, pair the Palm to your Linux computer and configure a Bluetooth HotSync connection on the Palm. The app registers an SPP server through BlueZ on RFCOMM channel 3.

See [INSTALL.md](INSTALL.md) for platform-specific setup.

## Start

```bash
python3 palm_manager.py
```

On the original Manjaro machine, Palm Manager also has a KDE application launcher.

## Install files

1. Add or drag PRC/PDB files into the list. The file chooser remembers the last selected directory across app restarts.
2. Leave **Automatic (Bluetooth or USB)** selected, or explicitly choose a transport.
3. Click **Install to Palm** and confirm.
4. Start HotSync on the Palm using the appropriate Bluetooth or USB connection. Automatic mode allows up to ten minutes for preparation; manual USB waits up to two minutes.
5. Read the result in **Progress**.

In automatic mode the app starts its Bluetooth listener and watches for USB serial interfaces belonging to the Tungsten T3 (USB vendor/product ID `0830:0060`). The second of the pair is used as the data port, even if Linux assigns `/dev/ttyUSB3` instead of `/dev/ttyUSB1`. On the T3 the USB device appears **only after USB HotSync begins**, not merely when the cable is plugged in. A connected Bluetooth Palm takes priority once its session begins. For troubleshooting, select a specific connection in the drop-down.

## Installation history

The **Installation history…** button displays past sessions (newest first), with the date, transport, filenames and result.

The full text log and session metadata are stored locally at:

```text
~/.local/state/palm-manager/history.jsonl
```

This JSON Lines file can be copied or backed up. It may contain local filenames or device output. Do **not** publish it in a public repository.

## Technical notes and limitations

- USB autodetection currently recognizes the tested Tungsten T3 USB ID (`0830:0060`). Other Palm models may need additional IDs or different port-selection logic. If the device disconnects before the transfer finishes, the app aborts the stalled transfer.
- Bluetooth communication depends on the Linux BlueZ D-Bus ProfileManager interface; this is **not** a native Windows application.
- The Bluetooth PTY bridge is in `bridge.py`. It registers the SPP service, creates `/tmp/palm-hotsync` and bridges the Bluetooth file descriptor using `socat`.
- Automatic transport selection and history are newer features. Test them on real hardware before calling this a stable release.
- Keep backups of valuable data before installing software.

## Verified hardware tests (2026-11-07)

- Single PRC installation over Bluetooth: `GoogleMaps_2_0_2_0.prc`, successful.
- Three PRCs over Bluetooth in one session: 599 KiB total, successful.
- Single PRC over USB: `RescoExplorer-5-03-3.prc`, 552 KiB, successful and visible on the Palm.
- File queue cleared after successful Bluetooth and USB transfers.

Automatic Bluetooth transfer and installation history were subsequently verified on real hardware. After fixing dynamic USB port detection and timeout handling, **automatic USB selection and a successful PRC installation were also verified** on the Tungsten T3 (Filez.prc, 183 KiB). The first automatic USB tests failed and were used to improve the implementation. Testing on other Palm models or Linux distributions is still needed.

## Maintainer, contributors and AI disclosure

Maintained by [@mendozaxperia-ui](https://github.com/mendozaxperia-ui). Substantial code and documentation were produced with OpenAI ChatGPT under the maintainer's direction, then tested with a real Palm Tungsten T3. See [AUTHORS.md](AUTHORS.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

If you have a different Palm OS device or use another Linux distribution, **testing reports are especially welcome**. Please do not upload proprietary Palm applications or ROMs.

## License

Palm Manager source code is distributed under the **GNU General Public License, version 3** (GPL-3.0-only), to the extent the contributors hold applicable rights. See [LICENSE](LICENSE) and [DEPENDENCIES.md](DEPENDENCIES.md).

Dependencies are separate projects with their own licenses; the archive does not include binaries or source copies of PyQt6, Qt, BlueZ, dbus-python, PyGObject, socat or pilot-link.

This is a **development preview (v0.1.0)**, tested primarily on Manjaro Linux with a Palm Tungsten T3. The USB detection logic is T3-specific. It is not yet a generally tested release for all Palm models and distributions.
