# Contributing and hardware testing

Thank you for helping keep classic Palm OS devices usable on modern Linux.

## Testing on another Palm model

A report is valuable even if installation fails. Please open a GitHub Issue and include:

- Palm model and Palm OS version
- Linux distribution and version
- Bluetooth adapter or USB connection (and transport selection: Automatic / Bluetooth / USB)
- Whether the Palm is discovered by the system
- Which step succeeds or fails, and relevant **redacted** logs
- Whether a small PRC/PDB transfer completes

**Privacy:** Logs can contain local paths, device identifiers, user names, or other sensitive information. Remove those before attaching them. Do not share proprietary PRC/PDB files, ROM images, passwords, or Bluetooth pairing secrets.

This application currently recognizes the Tungsten T3 USB vendor/product ID `0830:0060`; other models may require changes. Do not claim compatibility with a model until it has been tested.

## Pull requests

Keep changes small. Explain what changed and how you tested it. Please do not break the verified Bluetooth and USB paths. When possible, test with a real device, and identify any AI-generated portions that have not been independently reviewed.

The project is released under GPL-3.0-only. By contributing, you agree to submit your contribution under that project's license to the extent you have the necessary rights. Do not contribute material copied from incompatible licenses.

## Roadmap

- Confirm support on additional Palm models and Linux distributions
- Improve USB device detection without special-casing every device
- Eventually provide an AppImage, after a binary dependency and licensing review
