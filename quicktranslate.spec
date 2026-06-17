# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Quick Translate — single-file EXE."""
import os
import sys

block_cipher = None

# Project root
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'data', 'dict', 'ecdict.json'), os.path.join('data', 'dict')),
        (os.path.join(ROOT, 'data', 'icon.ico'), 'data'),
    ],
    hiddenimports=[
        'config', 'dictionary', 'translator', 'hotkey', 'history', 'tray', 'ui',
        'styles', 'animations', 'error_handler',
        'src', 'src.core', 'src.core.dict', 'src.core.dict.mdx_dict',
        'src.ui', 'src.ui.theme', 'src.ui.animator', 'src.ui.layout',
        'src.utils', 'src.utils.config', 'src.utils.errors',
        'src.utils.logging', 'src.utils.performance',
        'src.services', 'src.services.clipboard',
        'src.services.dict_sources', 'src.services.dict_sources.sources',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL',
        'tkinter.test', 'unittest', 'test', 'doctest',
        'xmlrpc', 'pydoc', 'pdb',
        'mdict_utils', 'readmdict',  # MDX CLI tools (not needed at runtime)
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QuickTranslate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'data', 'icon.ico'),
)
