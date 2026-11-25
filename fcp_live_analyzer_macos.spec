# -*- mode: python ; coding: utf-8 -*-
# macOS build (must run ON a Mac; PyInstaller cannot cross-compile):
#   pyinstaller --noconfirm fcp_live_analyzer_macos.spec   ->  dist/FCP Live Analyzer.app
# See build_macos.sh (also makes the .dmg) and .github/workflows/build.yml.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('docs', 'docs'), ('LICENSE', '.'), ('NOTICE', '.'), ('examples', 'examples')],
    hiddenimports=['parselmouth', 'soundfile', 'sounddevice', 'scipy.signal'],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'IPython', 'pytest', 'pyqtgraph.opengl', 'OpenGL',
              'numba', 'llvmlite', 'pandas'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='FCP Live Analyzer',
          console=False, upx=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='FCP Live Analyzer')
app = BUNDLE(
    coll,
    name='FCP Live Analyzer.app',
    icon='assets/logo_fcp.png',
    bundle_identifier='br.ufmg.fcpliveanalyzer',
    version='2.0.0',
    info_plist={
        'CFBundleShortVersionString': '2.0.0',
        'CFBundleVersion': '2.0.0',
        'NSHumanReadableCopyright': 'Copyright 2025-2026 Tiago Lima Bicalho Cruz. Apache License 2.0.',
        'NSMicrophoneUsageDescription': 'FCP Live Analyzer uses the microphone to analyse the singing voice in real time.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
