# Palm Manager v0.2.0-beta.1: community test guide

**Experimental Linux x86_64 AppImage. Not a stable release.** This utility installs
Palm OS PRC/PDB files over USB HotSync or Bluetooth HotSync. It does not
synchronize contacts or calendars.

## Quick start (no compilation needed)

1. Back up anything important on your Palm before testing.
2. Download Palm_Manager-0.2.0-beta.1-x86_64.AppImage from the GitHub
   pre-release assets (not the repository's green Code button).
3. Open the file's Properties and enable **Allow executing as a program**.
   Alternatively, open a terminal in the download directory and run:

       chmod +x Palm_Manager-0.2.0-beta.1-x86_64.AppImage
       ./Palm_Manager-0.2.0-beta.1-x86_64.AppImage

4. Click **Add files…** and select one small PRC/PDB you are permitted to install.
5. Leave **Connection: Automatic (Bluetooth or USB)** selected.
6. Click **Install to Palm**, confirm, and **then** start USB or Bluetooth
   HotSync on the Palm. Read the Progress messages.

Never start Palm Manager using sudo. The AppImage includes Palm Manager,
pilot-xfer and Bluetooth bridge helpers, but Linux device access and BlueZ
service availability still depend on the host computer.

## USB troubleshooting

The Palm Tungsten T3 normally appears as USB serial ports **only while USB
HotSync runs**. Port numbering may vary. Ubuntu/Debian commonly uses group
dialout; Manjaro/Arch often uses group uucp.

If you see a USB permission error, inspect the port during HotSync:

    id -nG
    ls -l /dev/ttyUSB*

If the device belongs to dialout but your user is not in that group, you may
choose to add it (on distributions that use sudo):

    sudo usermod -aG dialout "$USER"

Substitute uucp if the device belongs to that group. **Sign out and back in**
afterwards. Group membership grants access to other devices owned by that
group too. Do not use chmod 777 or run the program as root.

**VirtualBox:** after HotSync begins, attach the Palm USB device to the guest.
A VirtualBox USB filter for vendor 0830, product 0060 can automate attachment
for the tested T3. Configure it in the VirtualBox host.

If the Palm disconnects mid-transfer, check the cable, guest USB attachment
and whether another HotSync tool is running.

## Bluetooth troubleshooting

Bluetooth needs a working Linux Bluetooth adapter, BlueZ service and a paired
Palm set up for Bluetooth HotSync to the computer. In Automatic mode, Palm
Manager should continue waiting for USB if Bluetooth is unavailable.
USB-only testers do not need to configure Bluetooth.

## The AppImage won't start?

Check executable permission first. Some Linux installations may need FUSE
compatibility or Qt/X11 desktop libraries. Report the exact terminal error
and distribution version instead of installing random dependencies.

## Confirmed test coverage

- Tungsten T3 on Manjaro: USB and Bluetooth transfers confirmed;
  Automatic selected Bluetooth successfully.
- Tungsten T3 on Ubuntu 26.10 in VirtualBox: USB transfer confirmed;
  Automatic continued through USB when Bluetooth was unavailable.
- Other Palm models, Zorin OS and MX Linux: **not yet verified**.

## How to report a test

Open an issue at https://github.com/mendozaxperia-ui/palm-manager/issues
and include:

- Palm model and Palm OS version
- Linux distro/version and whether a virtual machine is used
- AppImage version: v0.2.0-beta.1
- Palm Manager mode and actual connection (USB/Bluetooth)
- Whether installation completed and the app appears on the Palm
- Relevant Progress messages or error text

Remove private paths, user names and device identifiers from logs before
posting. Do not publish your complete install history or copyrighted
Palm OS applications/ROMs.

## Source, licenses and credits

Source: https://github.com/mendozaxperia-ui/palm-manager
Palm Manager itself is GPL-3.0-only. The AppImage bundles third-party
components subject to their own licenses; see the included
usr/share/palm-manager/licenses and source directories, and the repository's
DEPENDENCIES.md for details.

This is AI-assisted, human-directed experimental software. Back up your Palm.
