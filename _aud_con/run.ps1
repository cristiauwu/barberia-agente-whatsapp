$uv="C:\Users\kimbo\.cherrystudio\bin\uv.exe"
$script=$args[0]
$tag=[System.IO.Path]::GetFileNameWithoutExtension($script)
$o="$env:TEMP\$tag.out.txt"; $e="$env:TEMP\$tag.err.txt"
$p=Start-Process -FilePath $uv -ArgumentList @("run","--with","psycopg[binary]","python",$script) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $o -RedirectStandardError $e
Write-Output "=== STDOUT ==="
Get-Content $o -Raw
Write-Output "=== STDERR ==="
Get-Content $e -Raw
Write-Output "=== EXIT $($p.ExitCode) ==="