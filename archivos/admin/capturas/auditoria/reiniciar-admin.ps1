$ErrorActionPreference = "Stop"
$envFile = "G:\Barberia\archivos\admin\.env-admin"
$script  = "G:\Barberia\archivos\admin\servidor-admin.py"
$logDir  = "G:\Barberia\archivos\admin"
$uv      = "C:\Users\kimbo\.cherrystudio\bin\uv.exe"

# 1) matar TODO proceso servidor-admin.py
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
         Where-Object { $_.CommandLine -like "*servidor-admin*" }
foreach ($p in $procs) {
    "MATANDO PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

# 2) cargar .env-admin
$vars = @{}
foreach ($line in Get-Content $envFile) {
    $line = $line.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { continue }
    $i = $line.IndexOf("=")
    if ($i -lt 1) { continue }
    $vars[$line.Substring(0,$i).Trim()] = $line.Substring($i+1).Trim()
}
"VARIABLES CARGADAS: " + ($vars.Keys -join ", ")

# 3) lanzar UNA instancia, con el entorno del archivo
$envNames = $vars.Keys
$prev = @{}
foreach ($k in $envNames) { $prev[$k] = [Environment]::GetEnvironmentVariable($k); [Environment]::SetEnvironmentVariable($k,$vars[$k]) }
$out = "$logDir\.servidor.log"
$err = "$logDir\.servidor.err.log"
$p = Start-Process -FilePath $uv -ArgumentList @("run","--with","psycopg[binary]","python",$script) `
     -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
"LANZADO PID: $($p.Id)"
foreach ($k in $envNames) { [Environment]::SetEnvironmentVariable($k,$prev[$k]) }

Start-Sleep -Seconds 6
"--- listeners 8765 ---"
Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table -AutoSize
"--- procesos servidor-admin ---"
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like "*servidor-admin*" } |
  Select-Object ProcessId,ParentProcessId | Format-Table -AutoSize
"--- log ---"
Get-Content $out -Raw
Get-Content $err -Raw