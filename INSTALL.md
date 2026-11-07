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

The device typically appears as two ports such as `/dev/ttyUSB0` and `/dev/ttyUSB1` **only when HotSync begins**. The T3's data port is the second. The user's account must have permission to access the serial port; on Manjaro this commonly means membership in the `uucp` group, and on some other distributions `dialout`.

Do not run the whole graphical program as root. Prefer setting permissions and signing out/in for new group membership to take effect.

## Bluetooth

Pair the Palm to your Linux Bluetooth adapter in BlueZ. On the Palm, configure Bluetooth HotSync to connect to your Linux computer. The program registers an SPP service on RFCOMM channel 3 and uses `socat` to bridge it to `pilot-xfer`.

If automatic mode causes trouble, select Bluetooth or USB cable explicitly. Other devices may need adaptation.

## Data and backups

Installation history is stored in `~/.local/state/palm-manager/history.jsonl` and the last chooser folder is stored by Qt's QSettings in your user configuration. Neither file is included in this archive. Back up important Palm data before testing third-party PRC/PDB files.
