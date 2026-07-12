# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for KobeFinance Terminal (Windows one-folder build).

Build:  pyinstaller packaging/kobefinance.spec --noconfirm
Output: dist/KobeFinanceTerminal/KobeFinanceTerminal.exe
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Pull in packages that resolve modules/data dynamically.
for pkg in ("kobefinance", "yfinance", "pdfplumber", "pdfminer", "curl_cffi"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += collect_submodules("PySide6")

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
    icon="kobefinance.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="KobeFinanceTerminal",
)
