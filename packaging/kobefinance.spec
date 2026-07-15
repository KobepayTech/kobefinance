# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for KobeFinance Terminal (cross-platform one-folder build).

Build:  pyinstaller packaging/kobefinance.spec --noconfirm
Output:
  Windows/Linux: dist/KobeFinanceTerminal/KobeFinanceTerminal[.exe]
  macOS:         dist/KobeFinanceTerminal.app  (plus the one-folder COLLECT)
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Pull in packages that resolve modules/data dynamically.
for pkg in ("kobefinance", "yfinance", "pdfplumber", "pdfminer", "curl_cffi", "certifi"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += collect_submodules("PySide6")

# Per-platform icon: .ico on Windows, .icns on macOS (generated in CI), none on
# Linux. Fall back to no icon when the file is absent so the build never breaks.
_icon = None
if sys.platform == "win32" and os.path.exists("kobefinance.ico"):
    _icon = "kobefinance.ico"
elif sys.platform == "darwin" and os.path.exists("kobefinance.icns"):
    _icon = "kobefinance.icns"

_version = os.environ.get("KOBE_VERSION", "0.1.0")

a = Analysis(
    ["entrypoint.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KobeFinanceTerminal",
    console=False,
    icon=_icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="KobeFinanceTerminal",
)

# macOS: wrap the one-folder build in a proper .app bundle for the .dmg.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="KobeFinanceTerminal.app",
        icon=_icon,
        bundle_identifier="tech.kobepay.kobefinance",
        info_plist={
            "CFBundleName": "KobeFinance Terminal",
            "CFBundleDisplayName": "KobeFinance Terminal",
            "CFBundleShortVersionString": _version,
            "CFBundleVersion": _version,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
