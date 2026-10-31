$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Creating virtual environment...'
    py -3 -m venv (Join-Path $PSScriptRoot '.venv')
}
Write-Host 'Installing / verifying dependencies...'
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
Write-Host 'Starting SlotZero at http://127.0.0.1:8000 ...'
& $python -m uvicorn app:app --app-dir $PSScriptRoot --reload --host 127.0.0.1 --port 8000
