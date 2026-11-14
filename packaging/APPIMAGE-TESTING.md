# Palm Manager AppImage, experimental preview

This workflow attempts to produce an **x86_64 AppImage**, aimed at Linux users who prefer not to install Python, Qt, \`pilot-xfer\` and \`socat\` manually.

This is an **experimental build pipeline**. Do not advertise the binary as tested on Zorin OS, MX Linux, Ubuntu, or real Palm hardware until its CI smoke tests and real-world transfer tests have passed. The existing source ZIP remains the known-working distribution on the maintainer's Manjaro system.

## Installing and trying it

1. Download the AppImage from the GitHub Actions build artifact.
2. Right-click the AppImage, choose Properties and enable **Allow executing file as program**. Depending on the distribution you may instead run \`chmod +x Palm_Manager-*.AppImage\` in a terminal.
3. Double-click to launch.
4. If an AppImage cannot start on your Linux distribution, check whether **FUSE** compatibility is missing or try \`./Palm_Manager-*.AppImage --appimage-extract-and-run\` as a diagnostic.
5. Start with a **backed-up** Palm and a small PRC file you are legally allowed to install. Do not assume that detection of a USB port proves that transferring files will work.

## Build design

The build runs on Ubuntu 22.04 to limit the minimum required glibc. PyInstaller packages two independent Python entry points: PalmManager and PalmBridge. The AppDir also packages the separate pilot-link \`pilot-xfer\` executable and \`socat\`, and carries license notices and an archive of the specific pilot-link source revision. The application still relies on host BlueZ and access permissions for USB/DBus. These system services **cannot** be made fully portable by AppImage.

## Licensing

Palm Manager code is GPL-3.0-only; pilot-xfer and socat are separate GPL-family executables with their own notices and their source obligations. LGPL libraries and Qt/PyQt6 have additional requirements. See DEPENDENCIES.md and the contents of the AppDir before distributing any binary more broadly. The pipeline is an exploratory proof of concept, not legal certification.
