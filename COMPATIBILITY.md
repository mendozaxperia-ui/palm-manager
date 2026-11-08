# Hardware and Linux compatibility

Palm Manager is an experimental application. **A volunteer offering to test a device is not a successful compatibility test.** All results below are based on actual reported runs, not on assumed capabilities of a Palm model.

## Verified hardware

| Palm model | Linux distribution | USB install | Bluetooth install | Notes |
| --- | --- | --- | --- | --- |
| Tungsten T3 | Manjaro Linux | **Passed** | **Passed** | Real-device PRC installations, including automatic connection selection and a multi-file Bluetooth batch, verified by the maintainer on 2026-11-07. |

**Passed** means a PRC/PDB transfer completed successfully and was confirmed on the Palm. It does not guarantee that all modes, USB adapters, or Linux distributions work.

## Devices mentioned by potential community testers

The following are **not tested**. They are included only to help organize future reports. Linux distribution and connection type are deliberately not guessed.

| Palm model | Linux distribution used for test | USB | Bluetooth | Notes |
| --- | --- | --- | --- | --- |
| Garmin iQue 3600 | Not reported | Not tested | Not tested | A volunteer is awaiting delivery; new to Palm OS |
| Palm TX | Not reported | Not tested | Not tested | Volunteer owns device |
| Tungsten E2 | Not reported | Not tested | Not tested | Volunteer owns device |
| LifeDrive | Not reported | Not tested | Not tested | Mentioned by more than one volunteer |
| Treo (model unspecified) | Not reported | Not tested | Not tested | Volunteer owns one or more models |
| Centro (model unspecified) | Not reported | Not tested | Not tested | Volunteer owns one or more models |
| Zire 72 | Not reported | Not tested | Not tested | Volunteer owns device |
| Palm Vx | Not reported | Not tested | Not tested | Older serial cradle may require a USB-to-serial adapter |
| Palm IIIc | Not reported | Not tested | Not tested | Older serial cradle may require a USB-to-serial adapter |

Other devices mentioned by volunteers (Foleo and webOS hardware) are **outside the present Palm OS PRC/PDB installation scope**, so they are not compatibility-test targets here.

## Linux distributions

| Distribution | GUI startup | pilot-xfer available | PRC/PDB installation | Notes |
| --- | --- | --- | --- | --- |
| Manjaro Linux | Passed | Passed | Passed | Maintainer's Tungsten T3; pilot-link-git installed from AUR |
| Ubuntu | Not tested | Not tested | Not tested | Volunteers have Ubuntu systems, but no results have been reported |
| Other distributions | Not tested | Not tested | Not tested | Test reports welcome |

**Potential issues to verify on Ubuntu:** whether `pilot-link` / `pilot-xfer` is provided for that Ubuntu version, Python/PyQt6/D-Bus package availability, BlueZ SPP setup, USB driver support and `dialout` permissions. None of these is currently confirmed to be broken.

## Reporting results

Please follow [TESTING.md](TESTING.md) and include the **Palm model**, **Palm OS version**, **Linux distribution and version**, **Palm Manager version**, **transport mode**, **USB device and port information if applicable**, **result of the transfer**, and **whether the application appeared on the Palm**.

Suggested status vocabulary: `Passed`, `Failed`, `Partial`, `Not tested`. Do not convert a volunteer's offer, a device being detected, or a successful GUI launch into a passed installation.

File a report in [hardware testing issue #1](https://github.com/mendozaxperia-ui/palm-manager/issues/1) once you have access to the repository, or send your results privately to the maintainer. Redact private paths, identifiers and log content before publishing.

All compatibility reports should note the tested version. The first community preview is `v0.2.0-test1`, which includes a manual `/dev/ttyUSB*` mode; unlike the original Tungsten T3 auto-detection, it has not yet been validated on other real devices.
