# Installing Palm Manager on Linux

This is a **source-only** archive, not a standalone executable. The application requires the installed system components below.

## Dependencies

- Python 3 (tested with 3.14)
- PyQt6 for the graphical interface
- dbus-python and PyGObject / GObject Introspection for the BlueZ ProfileManager
- BlueZ and an operating Bluetooth adapter for Bluetooth installations
- socat for the Bluetooth serial bridge
- pilot-link (the `pilot-xfer` command) for installation via Bluetooth or USB
- Linux kernel visor/USB serial driver and access to the Palm serial device for USB

On **Manjaro / Arch**, system dependencies used by the tested setup:

```bash
sudo pacman -S python-pyqt6 python-dbus python-gobject bluez socat
```

`pilot-xfer` must be installed separately. The tested setup used the AUR package **pilot-link-git**. Check the package sources and build instructions before using AUR packages. No automatic privileged installation is performed.

Package names differ on other Linux distributions; install the equivalents using your package manager.

On **Ubuntu / Debian**, the GUI dependencies are commonly available as:

```bash
sudo apt install python3-pyqt6 python3-dbus python3-gi bluez socat
```

Check whether `pilot-xfer` is already installed (`command -v pilot-xfer`). Availability of a `pilot-link` package varies by Ubuntu/Debian release and repository; install a compatible package or build from trusted upstream sources if necessary. `pilot-xfer` is essential, and Palm Manager cannot install files without it.

## Run without installation

Extract the archive and open a terminal in the `palm-manager` folder:

```bash
./run.sh
```

Or:

```bash
python3 palm_manager.py
```

## USB permissions

The Tungsten T3 typically appears as two ports such as `/dev/ttyUSB0` and `/dev/ttyUSB1` **only when HotSync begins**. The T3's data port is the second; this is not guaranteed for other models. The user's account must have permission to access the serial port; on Manjaro this commonly means membership in the `uucp` group, and on some other distributions `dialout`.

Do not run the whole graphical program as root. Prefer setting permissions and signing out/in for new group membership to take effect.

### Manual USB port for other Palm models

Choose **USB cable (manual port)** in Palm Manager. Enter the **data port** (for example, `/dev/ttyUSB1`), click Install, and start USB HotSync. Palm Manager waits up to two minutes for that port.

To discover possible ports, connect the Palm, start USB HotSync, and while it is trying to connect run in another terminal:

```bash
ls -l /dev/ttyUSB*
```

Ports may vanish again when HotSync stops. To inspect kernel messages if needed, use `journalctl -k` or `dmesg` (some distributions restrict reading the kernel log). Not all Palm models expose `ttyUSB` ports or use the same interface numbering. If no suitable port exists, **report that instead of guessing**; the manual mode currently accepts only `/dev/ttyUSBN`, and the application may need future changes for other device types. Avoid choosing a port that belongs to an unrelated USB device.

## Bluetooth

Pair the Palm to your Linux Bluetooth adapter in BlueZ. On the Palm, configure Bluetooth HotSync to connect to your Linux computer. The program registers an SPP service on RFCOMM channel 3 and uses `socat` to bridge it to `pilot-xfer`.

If automatic mode causes trouble, select Bluetooth or USB cable explicitly. Other devices may need adaptation. For other Palm models, try **USB cable (manual port)** only if Linux creates a suitable `/dev/ttyUSBN` data port.

See [TESTING.md](TESTING.md) for a focused first test and a report template.

## Data and backups

Installation history is stored in `~/.local/state/palm-manager/history.jsonl` and the last chooser folder is stored by Qt's QSettings in your user configuration. Neither file is included in this archive. Back up important Palm data before testing third-party PRC/PDB files.
