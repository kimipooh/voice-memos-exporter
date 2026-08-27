# -*- mode: python ; coding: utf-8 -*-
# Build with a universal2 Python (the python.org macOS universal2 installer).
# Homebrew Python is single-architecture and cannot produce this bundle.

a = Analysis(
    ['voice_memos_exporter.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='voice_memos_exporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns'  # Added icon
)
app = BUNDLE(
    exe,
    name='Voice Memos Exporter.app',
    icon='icon.icns',
    bundle_identifier='com.rudrakabir.voicememosexporter',
    version='1.0.3',
    info_plist={
        'LSMinimumSystemVersion': '12.0',
        'CFBundleShortVersionString': '1.0.3',
        'CFBundleVersion': '1.0.3'
    }
)
