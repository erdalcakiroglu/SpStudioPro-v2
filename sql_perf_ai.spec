# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SQL Performance AI Platform
"""

import sys
from pathlib import Path

block_cipher = None

# Version info
APP_VERSION = "1.0.0"
APP_NAME = "SQL Perf AI"
COMPANY_NAME = "SQL Perf AI"
FILE_DESCRIPTION = "AI-Powered SQL Server Performance Analysis Tool"
COPYRIGHT = "Copyright (c) 2024-2026 Erdal Cakiroglu"

# Project root
PROJECT_ROOT = Path(SPECPATH)

# Data files to include
added_files = [
    # Locales (when we add them)
    # ('locales/*.json', 'locales'),
    # Assets (when we add them)
    # ('assets/icons/*.png', 'assets/icons'),
]

# Hidden imports that PyInstaller might miss
hidden_imports = [
    'keyring.backends.Windows',
    'PyQt6.sip',
    'PyQt6.QtSvg',
    'sqlalchemy.dialects.mssql',
    'sqlalchemy.dialects.mssql.pyodbc',
    'pyodbc',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib.format',
    'pyqtgraph',
    'pyqtgraph.graphicsItems',
    'pyqtgraph.graphicsItems.PlotDataItem',
    'PyQt6.Qsci',
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'certifi',
    'openai',
    'anthropic',
    'pydantic',
    'pydantic_settings',
    'pydantic.fields',
    'pydantic_core',
]

# Modules to exclude (reduce size)
excluded_modules = [
    'PyQt6.QtWebEngine',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.QtCharts',
    'PyQt6.QtDataVisualization',
    'PyQt6.QtMultimedia',
    'PyQt6.QtBluetooth',
    'PyQt6.QtNfc',
    'PyQt6.QtPositioning',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtTest',
    'matplotlib',
    'pandas',
    'scipy',
    'PIL',
    'cv2',
    'tkinter',
    '_tkinter',
]

a = Analysis(
    ['app/main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows version info
version_info = None
if sys.platform == 'win32':
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
    )
    
    # Parse version
    v_parts = APP_VERSION.split('.')
    v_major = int(v_parts[0]) if len(v_parts) > 0 else 1
    v_minor = int(v_parts[1]) if len(v_parts) > 1 else 0
    v_patch = int(v_parts[2]) if len(v_parts) > 2 else 0
    
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=(v_major, v_minor, v_patch, 0),
            prodvers=(v_major, v_minor, v_patch, 0),
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0)
        ),
        kids=[
            StringFileInfo([
                StringTable('040904B0', [
                    StringStruct('CompanyName', COMPANY_NAME),
                    StringStruct('FileDescription', FILE_DESCRIPTION),
                    StringStruct('FileVersion', APP_VERSION),
                    StringStruct('InternalName', APP_NAME),
                    StringStruct('LegalCopyright', COPYRIGHT),
                    StringStruct('OriginalFilename', f'{APP_NAME}.exe'),
                    StringStruct('ProductName', APP_NAME),
                    StringStruct('ProductVersion', APP_VERSION),
                ])
            ]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])
        ]
    )

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app, no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon later: 'assets/icon.ico'
    version=version_info,
)
