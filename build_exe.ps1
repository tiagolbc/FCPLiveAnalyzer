# Builds dist\FCP_Live_Analyzer\FCP_Live_Analyzer.exe and a zip for distribution.
# Usage (PowerShell, in this folder):  .\build_exe.ps1
$ErrorActionPreference = "Stop"
python -m pip install -r requirements.txt pyinstaller pytest
python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw "tests failed" }
python tools\build_manuals.py
python -m PyInstaller --noconfirm --clean fcp_live_analyzer.spec
Compress-Archive -Path dist\FCP_Live_Analyzer -DestinationPath dist\FCP_Live_Analyzer_2.0.0_win64.zip -Force
Write-Host "OK: dist\FCP_Live_Analyzer\FCP_Live_Analyzer.exe"
