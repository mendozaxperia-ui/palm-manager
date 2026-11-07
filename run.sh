#!/bin/sh
# Run Palm Manager from its extracted source directory.
set -eu
cd -- "$(dirname -- "$0")"
exec python3 palm_manager.py
