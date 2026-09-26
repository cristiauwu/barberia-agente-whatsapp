param([Parameter(Mandatory=$true)][string]$Script)
$out = "$Script.out"
$err = "$Script.err"
if (Test-Path $out) { Remove-Item $out -Force }
if (Test-Path $err) { Remove-Item $err -Force }
Start-Process -FilePath "C:\Users\kimbo\.cherrystudio\bin\uv.exe" -ArgumentList "run","python",$Script -NoNewWindow -Wait -RedirectStandardOutput $out -RedirectStandardError $err
Get-Content $out -Encoding UTF8
$e = Get-Content $err -Encoding UTF8
if ($e) { "--- STDERR ---"; $e }