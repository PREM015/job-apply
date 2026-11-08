Set-Location (Split-Path -Parent $PSScriptRoot)
$env:GIT_PAGER = "cat"
$py = ".\.venv\Scripts\python.exe"
$rows = @()
function Add-Row($c, $r, $d) { $script:rows += [pscustomobject]@{ CHECK = $c; RESULT = $r; DETAIL = $d } }
$v = (& $py -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>&1 | Out-String).Trim()
if ($v -in @("3.11","3.12","3.13")) { Add-Row "python version" "PASS" $v } else { Add-Row "python version" "FAIL" $v }
$t = (& $py -m pytest -q 2>&1 | Out-String)
$last = ($t -split "`n" | Where-Object { $_.Trim() } | Select-Object -Last 1).Trim()
if ($t -match "\d+ passed" -and $t -notmatch "\d+ (failed|error)") { Add-Row "pytest (FIXTURE)" "PASS" $last } else { Add-Row "pytest (FIXTURE)" "FAIL" $last }
$gs = @(git status --short)
if ($gs.Count -eq 0) { Add-Row "git status clean" "PASS" "clean" } else { Add-Row "git status clean" "WARN" ("{0} entries, first: {1}" -f $gs.Count, $gs[0]) }
$bad = @(git ls-files | Select-String -Pattern '(^|/)\.env$|profile\.yaml$|answers\.yaml$|\.(pdf|xlsx|sqlite|sqlite3|db|exe)$')
if ($bad.Count -eq 0) { Add-Row "no forbidden tracked files" "PASS" "none" } else { Add-Row "no forbidden tracked files" "FAIL" ($bad -join ", ") }
$base = [ordered]@{
  "Master_Job_Tracker_final.xlsx" = "26E8B200858392942FFF291E5574BEF57E78446E859E828368B87A48AEBF59C2"
  "Prem_resume_01.pdf" = "7F386B19A03F60A29E40896D1DA89F8220FB88653EFEDA3842D7B1F0A092EAC6"
  "config.yaml" = "FAAC29462943D3B12ACF05493165B2ECA5DD7279F837AB8D8C3B113308564BC9"
  "profile.yaml" = "CCD7F0C5208C9277CC9345F0356A6DD5ECA3BD3F9BF883BBCC1D2CEA5609E9B6"
  "answers.yaml" = "0652D75A03DEE41FCA345DD60C6AE2ED4D91B17FB35833CDEA7FB62AC8F93F6A"
}
foreach ($name in $base.Keys) {
  if ($name -like "Master_*") { $f = Get-Item "D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx" -ErrorAction SilentlyContinue }
  else { $f = Get-ChildItem -Recurse -File -Filter $name -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\(\.venv|archive|\.git)\\' } | Select-Object -First 1 }
  if (-not $f) { Add-Row ("protected: " + $name) "FAIL" "file not found"; continue }
  $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
  if ($h -eq $base[$name]) { Add-Row ("protected: " + $name) "PASS" "SAME" } else { Add-Row ("protected: " + $name) "FAIL" "CHANGED" }
}
$tg = @(Get-ChildItem -Recurse -File -Path job_agent,tests,config -Include *.py,*.yaml,*.example,*.bat -ErrorAction SilentlyContinue | Select-String -Pattern 'telegram|notify|TELEGRAM_')
if ($tg.Count -eq 0) { Add-Row "no telegram/notify in code" "PASS" "none" } else { Add-Row "no telegram/notify in code" "WARN" ("{0} hits, e.g. {1}:{2}" -f $tg.Count, (Split-Path $tg[0].Path -Leaf), $tg[0].LineNumber) }
$db = (& $py -c "import sqlite3,pathlib;c=sqlite3.connect(pathlib.Path('data/job_agent.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);v=max(r[0] for r in c.execute('select * from schema_migrations'));print(v,c.execute('select count(*) from companies').fetchone()[0],c.execute('select count(*) from jobs').fetchone()[0])" 2>&1 | Out-String).Trim()
if ($db -match "^6 \d+ \d+$") { Add-Row "real DB (schema, companies, jobs)" "PASS" $db } else { Add-Row "real DB (schema, companies, jobs)" "FAIL" $db }
$dr = (& $py -m job_agent doctor 2>&1 | Out-String)
if ($dr -match "(?i)disabled") { Add-Row "live mode disabled (doctor)" "PASS" "DISABLED seen" } else { Add-Row "live mode disabled (doctor)" "FAIL" "doctor did not show DISABLED" }
if ($dr -match "Preferences schema: VALID") { Add-Row "preferences schema valid" "PASS" "load_preferences accepted config/preferences.yaml" } else { Add-Row "preferences schema valid" "FAIL" (($dr -split "`n" | Where-Object { $_ -match "Preferences schema:" } | Select-Object -Last 1).Trim()) }
if (Test-Path "config\preferences.yaml") { Add-Row "preferences.yaml present" "INFO" "YES" } else { Add-Row "preferences.yaml present" "INFO" "NO" }
$rows | Format-Table -AutoSize -Wrap
if (@($rows | Where-Object { $_.RESULT -eq "FAIL" }).Count -gt 0) { Write-Host "SELFCHECK: FAIL"; exit 1 } else { Write-Host "SELFCHECK: OK (WARN items are not failures)"; exit 0 }
