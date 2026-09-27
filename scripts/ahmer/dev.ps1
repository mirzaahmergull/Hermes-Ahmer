# Dot-source this file only in a development terminal, then activate Hermes.
$env:HERMES_HOME = "$env:LOCALAPPDATA\Hermes-Ahmer-dev"
$env:HERMES_RUNTIME_DIR = "$env:LOCALAPPDATA\Hermes-Ahmer-dev\tools"
Remove-Item Env:HERMES_INSTALL_ROOT -ErrorAction SilentlyContinue
Write-Host 'Development home selected. Run . C:\dev\Hermes-Ahmer\activate.ps1 to prepare development tools.'
