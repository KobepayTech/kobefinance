# Packaging — native installers (Windows / macOS / Linux)

KobeFinance Terminal ships as native installers built from a **PyInstaller**
one-folder bundle, per platform:

- **Windows** — Inno Setup wraps the bundle into a `.exe` installer.
- **macOS** — the bundle is built as a `.app` and packaged into a `.dmg`.
- **Linux** — the bundle is shipped as a `.tar.gz`.

The `Build release installers` GitHub Actions workflow builds all three on their
respective runners and publishes them to a single GitHub Release. Each OS's
installer can only be produced on that OS (a Windows `.exe`/macOS `.app` cannot
be built from Linux).

## Files

- `entrypoint.py` — frozen-app entry point (calls `kobefinance.app.main`).
- `kobefinance.spec` — cross-platform PyInstaller spec (Windows `.ico`, macOS
  `.app` + `.icns`, Linux one-folder; collects PySide6, yfinance, pdfplumber).
- `installer.iss` — Inno Setup script → `KobeFinanceTerminal-<ver>-windows-x64-setup.exe`.
- `kobefinance.ico` — Windows app icon (macOS `.icns` is generated in CI from
  `assets/kobefinance.png`).
- `SIGNING.md` — code-signing setup for each platform.

## Build locally

**Windows** (PowerShell):
```powershell
python -m pip install -e .
pip install pyinstaller
cd packaging; pyinstaller kobefinance.spec --noconfirm; cd ..
iscc /DAppVersion=0.1.0 packaging\installer.iss
# → packaging\dist\installer\KobeFinanceTerminal-0.1.0-windows-x64-setup.exe
```

**macOS**:
```bash
pip install -e . pyinstaller
sips -s format icns assets/kobefinance.png --out packaging/kobefinance.icns
cd packaging && pyinstaller kobefinance.spec --noconfirm
hdiutil create -volname "KobeFinance Terminal" -srcfolder dist/KobeFinanceTerminal.app \
  -ov -format UDZO KobeFinanceTerminal-0.1.0-macos.dmg
```

**Linux**:
```bash
pip install -e . pyinstaller
cd packaging && pyinstaller kobefinance.spec --noconfirm
tar -czf KobeFinanceTerminal-0.1.0-linux-x64.tar.gz -C dist KobeFinanceTerminal
# run: ./dist/KobeFinanceTerminal/KobeFinanceTerminal
```

## Build in CI

Push to the working branch, push a `v*` tag, or trigger the **Build release
installers** workflow manually (`workflow_dispatch`, pass a version). It builds
Windows/macOS/Linux in parallel, uploads each as a build artifact, and publishes
them all to the `v<version>` GitHub Release — which is what the website's
Download button links to.

## Code signing

Signing steps are wired into the workflow for Windows (Authenticode) and macOS
(Developer ID + notarization), gated on repository secrets. Until those secrets
are set, builds are produced **unsigned**. See `SIGNING.md` for how to obtain
certificates and which secrets to configure.
