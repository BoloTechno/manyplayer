# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Spec for ManyPlayer Windows Desktop Application
# Usage: pyinstaller build_windows.spec

import sys
import os

block_cipher = None

added_files = [
    ('config/cameras.example.json', 'config'),
]
if os.path.exists('config/cameras.json'):
    added_files.append(('config/cameras.json', 'config'))

# Bundle offline YOLO weights if present for air-gapped deployments (Resolves Audit Finding 3)
if os.path.exists('yolov8n.pt'):
    added_files.append(('yolov8n.pt', '.'))

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'cv2',
        'numpy',
        'ultralytics',
        'torch',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ManyPlayer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set False for GUI desktop application on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ManyPlayer',
)
