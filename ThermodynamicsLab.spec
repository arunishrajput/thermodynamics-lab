# -*- mode: python ; coding: utf-8 -*-
# Single spec file that builds correctly on both Windows (.exe) and macOS (.app).

import sys
from PyInstaller.utils.hooks import collect_data_files

datas  = collect_data_files('customtkinter')   # themes, fonts, images
datas += collect_data_files('matplotlib')       # colormaps, fonts, style sheets

a = Analysis(
    ['dashboard.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'PIL',
        'PIL._tkinter_finder',
        '_tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# ── Windows — single portable .exe ───────────────────────────────────────────
if sys.platform == 'win32':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ThermodynamicsLab',
        debug=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,      # no black terminal window
        icon=None,          # swap for a .ico path if you have one
    )

# ── macOS — proper .app bundle ────────────────────────────────────────────────
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='ThermodynamicsLab',
        debug=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=False,
        icon=None,          # swap for a .icns path if you have one
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='ThermodynamicsLab',
    )
    app = BUNDLE(
        coll,
        name='ThermodynamicsLab.app',
        icon=None,
        bundle_identifier='com.thermodynamicslab.app',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleName': 'Thermodynamics Lab',
            'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1.0',
        },
    )
