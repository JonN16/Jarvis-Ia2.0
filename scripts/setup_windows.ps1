$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not (Test-Path .venv)) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "Ambiente preparado."
Write-Host "Próximo passo: instalar o Ollama e rodar 'ollama pull qwen2.5:7b'"
