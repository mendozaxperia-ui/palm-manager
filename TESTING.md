# Community hardware test: Palm Manager

Thank you for trying an early version! You do **not** need to test your entire collection. One Palm and one Linux computer is already valuable.

**Caution:** This is experimental software. Back up important data first. Use a small PRC you are legally allowed to install and share no proprietary applications or ROMs. Installing third-party software on a Palm is at your own risk.

## Minimal test (about one session)

1. Note your Palm model, Palm OS version, and Linux distribution/version.
2. Install the dependencies described in [INSTALL.md](INSTALL.md). Verify `command -v pilot-xfer` returns a path.
3. Run `./run.sh` from the extracted directory.
4. Select a small PRC file using **Add files…**.
5. Try **USB cable** (automatic T3 detection). If your model is not a Tungsten T3, this is expected to fail.
6. If the Palm exposes a USB serial port, try **USB cable (manual port)**. Determine the *Palm data port* using `ls -l /dev/ttyUSB*` while HotSync is starting. Enter it exactly, such as `/dev/ttyUSB1`.
7. Click **Install to Palm** and confirm, then initiate USB HotSync on the Palm.
8. Report whether the transfer completed and whether the application appears on the Palm.

**Optional:** Try Bluetooth after pairing your Palm with BlueZ. You can skip this and test just USB.

## Copyable report

- Palm model:
- Palm OS version:
- Linux distro/version:
- Palm Manager mode (auto / USB / manual USB / Bluetooth):
- Connection (USB / Bluetooth):
- USB ports seen while HotSync runs:
- Does `pilot-xfer` exist?:
- Transfer success or failure:
- Application appeared on Palm?:
- Short error message, if any:
- Anything else worth noting:

**Privacy:** Logs can contain local paths, device identifiers, usernames, and device data. Redact sensitive details before sharing. Do not send your private install history file.

This testing preview is currently **confirmed with a Tungsten T3 on Manjaro**; compatibility on other hardware remains unverified.
