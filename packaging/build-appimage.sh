#!/usr/bin/env bash
# Experimental AppImage build on Ubuntu 22.04 x86_64.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
APPDIR="$ROOT/build/AppDir"
rm -rf "$ROOT/build" "$ROOT/dist"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/palm-manager/licenses" "$APPDIR/usr/share/palm-manager/source"
export PATH="$HOME/.local/bin:$PATH"
python3 -m PyInstaller --noconfirm --clean --onedir --windowed --name PalmManager palm_manager.py
python3 -m PyInstaller --noconfirm --clean --onedir --console --name PalmBridge --hidden-import=dbus.mainloop.glib --collect-all gi --collect-all dbus bridge.py
cp -a dist/PalmManager dist/PalmBridge "$APPDIR/usr/bin/"
git clone --depth 1 https://github.com/desrod/pilot-link.git "$ROOT/build/pilot-link"
(
 cd "$ROOT/build/pilot-link"
 git rev-parse HEAD | tee "$APPDIR/usr/share/palm-manager/source/pilot-link-commit.txt"
 ./autogen.sh
 ./configure --prefix=/usr --enable-conduits
 make -j2
 make DESTDIR="$APPDIR" install
 # Palm Manager only needs pilot-xfer. Remove the other pilot-link command-line tools.
 find "$APPDIR/usr/bin" -maxdepth 1 -type f ! -name pilot-xfer -delete
 git archive --format=tar.gz -o "$APPDIR/usr/share/palm-manager/source/pilot-link-source.tar.gz" HEAD
 cp COPYING COPYING.LIB "$APPDIR/usr/share/palm-manager/licenses/"
)
test -x "$APPDIR/usr/bin/pilot-xfer"
export LD_LIBRARY_PATH="$APPDIR/usr/lib/x86_64-linux-gnu:$APPDIR/usr/lib:$APPDIR/usr/lib64:${LD_LIBRARY_PATH:-}"
cp /usr/bin/socat "$APPDIR/usr/bin/socat"
cp /usr/share/doc/socat/copyright "$APPDIR/usr/share/palm-manager/licenses/socat-Debian-copyright"
cp LICENSE "$APPDIR/usr/share/palm-manager/licenses/Palm-Manager-GPLv3"
cp README.md INSTALL.md DEPENDENCIES.md TESTING.md "$APPDIR/usr/share/palm-manager/"
cp packaging/palm-manager.svg "$APPDIR/palm-manager.svg"
cp packaging/palm-manager.desktop "$APPDIR/palm-manager.desktop"
rsvg-convert -w 256 -h 256 "$APPDIR/palm-manager.svg" -o "$APPDIR/palm-manager.png"
ln -s palm-manager.png "$APPDIR/.DirIcon"
cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib/x86_64-linux-gnu:$HERE/usr/lib:$HERE/usr/lib64:${LD_LIBRARY_PATH:-}"
exec "$HERE/usr/bin/PalmManager/PalmManager" "$@"
EOF
chmod +x "$APPDIR/AppRun"
# Copy non-glibc executable ELF dependencies, including pilot-link's libraries.
for executable in "$APPDIR/usr/bin/pilot-xfer" "$APPDIR/usr/bin/socat"; do
  while read -r lib; do
    [[ -f "$lib" ]] || continue
    soname="$(basename "$lib")"
    [[ "$soname" =~ ^(libc\.so|ld-linux|libpthread\.so|libdl\.so|libm\.so|librt\.so|libresolv\.so|libnss_) ]] && continue
    mkdir -p "$APPDIR/usr/lib"
    if [[ "$(realpath "$lib")" != "$(realpath -m "$APPDIR/usr/lib/$soname")" ]]; then
      cp -L "$lib" "$APPDIR/usr/lib/$soname"
    fi
  done < <(ldd "$executable" | awk '/=> \// {print $3}')
done
"$APPDIR/usr/bin/pilot-xfer" --version
QT_QPA_PLATFORM=offscreen timeout 8 "$APPDIR/AppRun" > "$ROOT/build/gui-smoke.log" 2>&1 && gui_exit=0 || gui_exit=$?
cat "$ROOT/build/gui-smoke.log"
if [[ "$gui_exit" != 124 ]]; then echo "GUI smoke test failed with exit $gui_exit" >&2; exit 1; fi
curl -fL --retry 3 -o "$ROOT/build/appimagetool.AppImage" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x "$ROOT/build/appimagetool.AppImage"
mkdir -p "$ROOT/dist"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$ROOT/build/appimagetool.AppImage" "$APPDIR" "$ROOT/dist/Palm_Manager-0.2.0-test2-x86_64.AppImage"
# Test the actual AppImage entrypoint, not only the unpacked AppDir.
QT_QPA_PLATFORM=offscreen APPIMAGE_EXTRACT_AND_RUN=1 timeout 10 "$ROOT/dist/Palm_Manager-0.2.0-test2-x86_64.AppImage" > "$ROOT/build/appimage-smoke.log" 2>&1 && image_exit=0 || image_exit=$?
cat "$ROOT/build/appimage-smoke.log"
if [[ "$image_exit" != 124 ]]; then echo "AppImage smoke test failed with exit $image_exit" >&2; exit 1; fi
echo "=== AppDir size report ==="
du -sh "$APPDIR" "$APPDIR/usr/bin/PalmManager" "$APPDIR/usr/bin/PalmBridge" "$APPDIR/usr/lib" "$APPDIR/usr/share" || true
echo "=== Built AppImage size ==="
ls -lh "$ROOT/dist/"*.AppImage
sha256sum "$ROOT/dist/"*.AppImage | tee "$ROOT/dist/SHA256SUMS"
