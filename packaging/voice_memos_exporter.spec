# Local-only packaging spec for the gui/local-app branch.
# Not for publication, redistribution, or release.
# Upstream license status is unresolved.

import os


repo_root = os.path.dirname(SPECPATH)
entry_point = os.path.join(repo_root, "voice_memos_exporter.py")

a = Analysis(
    [entry_point],
    pathex=[repo_root],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "setuptools", "pip"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Voice Memos Exporter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Voice Memos Exporter",
)
app = BUNDLE(
    coll,
    name="Voice Memos Exporter.app",
    icon=None,
    bundle_identifier="jp.kitani.voicememosexporter.local",
    info_plist={
        "CFBundleName": "Voice Memos Exporter",
        "CFBundleDisplayName": "Voice Memos Exporter",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
    },
)
