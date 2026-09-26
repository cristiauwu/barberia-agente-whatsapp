$git = "C:\Program Files\Git\cmd\git.exe"
$repo = "G:\Barberia"
function RunGit([string[]]$args_) {
  $o = "$env:TEMP\g_o.txt"; $e = "$env:TEMP\g_e.txt"
  Start-Process -FilePath $git -ArgumentList $args_ -NoNewWindow -Wait `
    -RedirectStandardOutput $o -RedirectStandardError $e | Out-Null
  $so = Get-Content $o -Raw -ErrorAction SilentlyContinue
  $se = Get-Content $e -Raw -ErrorAction SilentlyContinue
  if ($so) { $so.TrimEnd() }
  if ($se) { "[stderr] " + $se.TrimEnd() }
}
Write-Output "===== REMOTES ====="
RunGit @("-C",$repo,"remote","-v")
Write-Output "===== BRANCH TRACKING ====="
RunGit @("-C",$repo,"branch","-vv")
Write-Output "===== LOG ====="
RunGit @("-C",$repo,"log","--oneline","-20")
Write-Output "===== FICHEROS RASTREADOS (total) ====="
$files = RunGit @("-C",$repo,"ls-files")
($files -split "`n").Count
Write-Output "===== FICHEROS RASTREADOS (lista) ====="
$files
Write-Output "===== BUSCAR FICHEROS SENSIBLES RASTREADOS ====="
$files -split "`n" | Where-Object { $_ -match '\.env|key|pwd|pass|cred|secret|token|supabase|\.db-roles|journal' }