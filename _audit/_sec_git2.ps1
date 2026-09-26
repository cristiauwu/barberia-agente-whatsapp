$git = "C:\Program Files\Git\cmd\git.exe"
$repo = "G:\Barberia"
$outdir = "G:\Barberia\_audit"
function RunGit([string[]]$args_, [string]$tag) {
  $o = "$outdir\_g_$tag.out"; $e = "$outdir\_g_$tag.err"
  Start-Process -FilePath $git -ArgumentList $args_ -NoNewWindow -Wait `
    -RedirectStandardOutput $o -RedirectStandardError $e | Out-Null
  Write-Output "### git $($args_ -join ' ')  [out=$o]"
  Get-Content $o -Raw -ErrorAction SilentlyContinue
  $se = Get-Content $e -Raw -ErrorAction SilentlyContinue
  if ($se) { Write-Output "[stderr] $se" }
}

Write-Output "########## 1) git grep de patrones en el ARBOL ACTUAL ##########"
RunGit @("-C",$repo,"grep","-n","-I","-E","-e","sk-[A-Za-z0-9]{16,}","-e","sb_publishable_","-e","sb_secret_","-e","AUTHENTICATION_API_KEY=","-e","password=","-e","AIza[0-9A-Za-z_-]{35}","-e","postgresql://[^ ]","HEAD") "grep_head"

Write-Output "########## 2) git grep del historial completo (todos los commits) ##########"
RunGit @("-C",$repo,"grep","-n","-I","-E","-e","sk-[A-Za-z0-9]{16,}","-e","sb_publishable_","-e","sb_secret_","-e","AUTHENTICATION_API_KEY=","-e","password=","-e","AIza[0-9A-Za-z_-]{35}","-e","postgresql://[^ ]","$(git rev-list --all)") "grep_all"

Write-Output "########## 3) Archivos rastreados que coinciden; comprobar ignorados ##########"
$o = "$outdir\_g_ls.out"
Start-Process -FilePath $git -ArgumentList @("-C",$repo,"ls-files","--cached","--others","--ignored","--exclude-standard") -NoNewWindow -Wait -RedirectStandardOutput $o -RedirectStandardError "$outdir\_g_ls.err" | Out-Null
$o2 = "$outdir\_g_ls2.out"
Start-Process -FilePath $git -ArgumentList @("-C",$repo,"ls-files","--cached") -NoNewWindow -Wait -RedirectStandardOutput $o2 -RedirectStandardError "$outdir\_g_ls2.err" | Out-Null
Write-Output "--- ARCHIVOS IGNORADOS ---"
Get-Content $o -Raw -ErrorAction SilentlyContinue

Write-Output "########## 4) HISTORIAL: commits y si algun blob sensible estuvo versionado ##########"
RunGit @("-C",$repo,"log","--all","--name-status","--pretty=format:COMMIT %h %ad %s","--date=short") "log_all"
Write-Output "########## 5) Estado de los ficheros con secretos localizados ##########"
$sensibles = @(
 "INFRAESTRUCTURA.md","GUIA-CREDENCIALES.md","_audit_dump.py","_audit_final.py",
 "_audit_pg_report.txt","_audit_sheet.csv","_audit_csv.py","_audit_sheets.py",
 "_audit_pg.py","archivos\SUPABASE-GUIA.md","archivos\supabase-esquema.sql",
 "archivos\supabase-esquema-real.sql","archivos\supabase-conectar.py",
 "archivos\supabase-pooler.py","archivos\supabase-verificar.py",
 "archivos\supabase-crear-esquema.py","archivos\_t_tables.txt","archivos\_r_d3.txt",
 "_inspeccion.py","_inspeccion2.py","_audit_names.py","_audit_broad.py",
 "archivos\unc-cred-id.txt","table_name","archivos\.n8n-key.txt","archivos\.supabase-conn.txt",
 "archivos\admin\.env-admin","archivos\admin\.pwd-sitio.txt","archivos\admin\.db-roles.txt",
 ".env",".env.evolution","archivos\admin\.journal\sends.sqlite3"
)
foreach ($s in $sensibles) {
  $p = Join-Path $repo $s
  $exists = Test-Path $p
  $tracked = "NO-TEST"
  $ignored = "?"
  if ($exists) {
    $o3 = "$outdir\_g_ck.out"
    Start-Process -FilePath $git -ArgumentList @("-C",$repo,"ls-files","--error-unmatch",$s) -NoNewWindow -Wait -RedirectStandardOutput $o3 -RedirectStandardError "$outdir\_g_ck.err" | Out-Null
    $t = Get-Content $o3 -Raw -ErrorAction SilentlyContinue
    $tracked = if ($t -and $t.Trim()) { "SI-RASTREADO" } else { "no" }
    Start-Process -FilePath $git -ArgumentList @("-C",$repo,"check-ignore","-v",$s) -NoNewWindow -Wait -RedirectStandardOutput $o3 -RedirectStandardError "$outdir\_g_ck2.err" | Out-Null
    $ig = Get-Content $o3 -Raw -ErrorAction SilentlyContinue
    $ignored = if ($ig -and $ig.Trim()) { "IGNORADO(" + ($ig.Trim() -split "\s+")[0] + ":" + ($ig.Trim() -split "\s+")[1] + ")" } else { "NO-IGNORADO" }
  } else { $tracked = "(no existe)"; $ignored = "-" }
  Write-Output ("{0,-45} existe={1,-6} git={2,-14} {3}" -f $s, $exists, $tracked, $ignored)
}