$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$OdooBin = Join-Path $ProjectRoot "odoo-bin"
$Config = Join-Path $ProjectRoot "odoo.local.conf"

& $Python $OdooBin -c $Config
