$git = "C:\Program Files\Git\cmd\git.exe"
$repo = "G:\Barberia"
$outdir = "G:\Barberia\_audit"

function GrepGit([string]$pat, [string]$rev, [string]$tag) {
  $o = "$outdir\_gg_$tag.out"; $e = "$outdir\_gg_$tag.err"
  Start-Process -FilePath $git -ArgumentList @("-C",$repo,"grep","-n","-I","-E","-e",$pat,$rev) `
    -NoNewWindow -Wait -RedirectStandardOutput $o -RedirectStandardError $e | Out-Null
  Write-Output "===== PATRON [$pat]  REV [$rev] ====="
  $so = Get-Content $o -Raw -ErrorAction SilentlyContinue
  if ($so) { $so } else { "(sin coincidencias)" }
}

Write-Output "############ ARBOL ACTUAL (HEAD) ############"
GrepGit "sb_publishable_" "HEAD" "1"
GrepGit "sb_secret_" "HEAD" "2"
GrepGit "AUTHENTICATION_API_KEY=" "HEAD" "3"
GrepGit "AIza[0-9A-Za-z_-]{35}" "HEAD" "4"
GrepGit "sk-[A-Za-z0-9]{20,}" "HEAD" "5"

Write-Output "############ COMMIT 1 (ff61da0) ############"
GrepGit "sb_publishable_" "ff61da0" "6"
GrepGit "AUTHENTICATION_API_KEY=" "ff61da0" "7"

Write-Output "############ TODOS LOS OBJETOS DEL HISTORIAL ############"
$o = "$outdir\_gg_objs.out"
Start-Process -FilePath $git -ArgumentList @("-C",$repo,"rev-list","--all","--objects") -NoNewWindow -Wait `
  -RedirectStandardOutput $o -RedirectStandardError "$outdir\_gg_objs.err" | Out-Null
Write-Output "Objetos en el historial:"
(Get-Content $o | Measure-Object).Count

Write-Output "############ NOMBRES SENSIBLES EN TODO EL HISTORIAL ############"
$o2 = "$outdir\_gg_names.out"
Start-Process -FilePath $git -ArgumentList @("-C",$repo,"log","--all","--pretty=format:@@%h|%ad|%s","--date=short","--name-only") -NoNewWindow -Wait `
  -RedirectStandardOutput $o2 -RedirectStandardError "$outdir\_gg_names.err" | Out-Null
$txt = Get-Content $o2 -Raw
$txt -split "`n" | Where-Object { $_ -match "env|key|pwd|pass|cred|secret|token|supabase|n8n-key|publishable" } | Sort-Object -Unique

Write-Output "############ LOG RESUMIDO ############"
Get-Content $o2 -Raw | Select-String -Pattern "@@" -AllMatches | ForEach-Object { $_.Line }