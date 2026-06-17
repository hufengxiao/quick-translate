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
        (os.path.join(ROOT, 'data'), 'data'),
    ],
    hiddenimports=[
        'src', 'src.core', 'src.core.index', 'src.core.cache',
        'src.core.lazy', 'src.core.dict', 'src.ui', 'src.ui.theme',
        'src.utils', 'src.utils.config', 'src.utils.errors',
        'src.utils.logging', 'src.utils.performance',
        'src.services', 'src.services.clipboard',
        'src.services.dict_sources', 'src.services.dict_sources.sources',
        'src.core.dict.mdx_dict', 'src.core.dict.dictionary',
        'src.core.index.exact', 'src.core.index.trie', 'src.core.index.bktree',
        'src.core.cache.lru',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL',
        'tkinter.test', 'unittest', 'test', 'doctest',
        'xmlrpc', 'pydoc', 'pdb',
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
    upx=True,           # compress with UPX if available
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
