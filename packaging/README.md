# Packaging — Windows installer

KobeFinance Terminal ships as a Windows installer built from a **PyInstaller**
one-folder bundle wrapped by an **Inno Setup** script. The build runs on a
Windows machine (or the `Build Windows installer` GitHub Actions workflow on a
`windows-latest` runner) — a Windows `.exe` cannot be produced from Linux/macOS.

## Files

- `entrypoint.py` — frozen-app entry point (calls `kobefinance.app.main`).
- `kobefinance.spec` — PyInstaller spec (collects PySide6, yfinance, pdfplumber).
- `installer.iss` — Inno Setup script → `KobeFinanceTerminal-<ver>-windows-x64-setup.exe`.
- `kobefinance.ico` — app icon.

## Build locally on Windows

```powershell
python -m pip install -e .
pip install pyinstaller
cd packaging
pyinstaller kobefinance.spec --noconfirm
# then, with Inno Setup installed (https://jrsoftware.org/isdl.php):
cd ..
iscc /DAppVersion=0.1.0 packaging\installer.iss
# → dist\installer\KobeFinanceTerminal-0.1.0-windows-x64-setup.exe
```

## Build in CI

Trigger the **Build Windows installer** workflow manually
(`workflow_dispatch`, pass a version) or push a `v*` tag. The workflow uploads
the installer as a build artifact and, for tag builds, attaches it to the
GitHub Release — which is exactly what the website's Download button links to.

## macOS / Linux

The same PyInstaller spec works on macOS/Linux to produce native one-folder
builds (`pyinstaller kobefinance.spec`); packaging into `.dmg` / `.AppImage`
would be a follow-up. For now, non-Windows users run from source:
`pip install -e . && kobefinance`.
