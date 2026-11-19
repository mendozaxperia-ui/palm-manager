# Experimental direct USB / libusb HotSync

This build adds **USB direct (libusb, experimental)** to Connection. It does
not replace the working legacy USB serial or Bluetooth modes.

## Test on Manjaro and Ubuntu in VirtualBox

1. Start the Palm Manager test AppImage, choose **USB direct (libusb,
   experimental)**, and add one small PRC/PDB file you can safely install.
   Back up important Palm databases first.
2. Click **Install to Palm**, confirm, and **then start USB HotSync on Palm**.
   Palm Manager starts \`pilot-xfer -p usb:\` immediately and waits for the
   incoming HotSync, without requiring any \`/dev/ttyUSB*\` port.
3. Report your distribution, Palm model, whether the transfer succeeds,
   and the text in the Progress log (redact private information).

## Troubleshooting

- VirtualBox: attach the Palm USB device to the **guest** from Devices → USB
  while HotSync is active. The device often appears only while syncing.
  A USB filter can help. Confirm its presence using \`lsusb\` in the guest.
- libusb needs permissions for the raw \`/dev/bus/usb/...\` device. The
  \`dialout\`/\`uucp\` serial-port groups alone do not grant that access.
  A specific udev rule may be needed, depending on your distribution.
- The kernel's legacy \`visor\` module can claim the USB interface and
  conflict with libusb. Inspect \`lsmod | grep visor\` first. Do not
  permanently blacklist or unload drivers without checking their effects.
- Close other HotSync clients, including J-Pilot, before trying this mode.
- Automatic USB detection deliberately still uses the old ttyUSB logic;
  choose the new mode explicitly so we can compare the mechanisms.

No real-hardware validation has yet been completed for this experimental mode.
