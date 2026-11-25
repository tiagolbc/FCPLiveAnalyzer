# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller --noconfirm fcp_live_analyzer.spec   (or run build_exe.ps1)
# Produces dist/FCP_Live_Analyzer/FCP_Live_Analyzer.exe (one-folder: starts fast, no temp unpacking).

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('docs', 'docs'), ('LICENSE', '.'), ('NOTICE', '.'), ('examples', 'examples')],
    hiddenimports=['parselmouth', 'soundfile', 'sounddevice', 'scipy.signal'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'IPython', 'jupyter', 'notebook', 'pytest',
              'pyqtgraph.opengl', 'OpenGL', 'numba', 'llvmlite', 'win32com', 'pythonwin', 'yaml', 'pandas', 'torch', 'tensorflow', 'cv2', 'sklearn'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='FCP_Live_Analyzer',
    debug=False, strip=False, upx=False,
    console=False,
    icon='assets/logo_fcp.ico',
    version='version_info.txt',
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name='FCP_Live_Analyzer')
