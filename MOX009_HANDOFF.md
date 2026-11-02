# MOX-009 — Consolidated Content Quality and Submission Snapshot

Date: November 2, 2026. Expected MOX-008 baseline: `97b1c4d7108718826d780a15cbafd4ef901f0e01`. Author-side tests: 41 passing.

## Features

- **Quality Report** combines recognized bracketed citation coverage with registered-source count, attested-source count and unresolved issues.
- The desktop **Evaluate & Queue** button now blocks when citations are missing, evidence is unregistered, or registration lacks explicit operator attestation.
- A report without such flags is marked `READY_FOR_HUMAN_REVIEW`, **not** factually verified. Semantic truth/entailment is not checked.
- Every QA-accepted brief submitted through the service stores its first quality snapshot in local `operator.sqlite3`. Subsequent actions do not replace that snapshot.
- Pending and completed-review detail panels show the recorded quality status. Legacy approvals without snapshots are labeled `NOT RECORDED`.

The original headless workflow stays backward-compatible; callers using the service directly must enforce the same provenance policy themselves. No publishing, external source fetch, paid APIs, or RVSC mission-state changes are introduced.

## Installation — LEFT administrator PowerShell

Close MOXIE first. Keep the RIGHT RVSC supervisor stopped. Save `MOX009_INCREMENT.zip` to `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX009_INCREMENT.zip'
$Expected = '97b1c4d7108718826d780a15cbafd4ef901f0e01'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX009 archive not found' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected repository baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'MOXIE working tree not clean; stopped' }
$Targets = @('src/moxie/content_quality.py','src/moxie/operator_store.py','src/moxie/operator_service.py','src/moxie/operator_app.py','tests/test_mox009_content_quality.py','MOX009_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX009_stage'
if (Test-Path -LiteralPath $Stage) { throw 'MOX009 staging folder already exists; inspect before rerun' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX009_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $Backup | Out-Null
foreach ($Relative in $Targets) {
    $Destination = Join-Path $Repo $Relative
    if (Test-Path -LiteralPath $Destination) {
        $SaveTo = Join-Path $Backup $Relative
        New-Item -ItemType Directory -Path (Split-Path $SaveTo) -Force | Out-Null
        Copy-Item -LiteralPath $Destination -Destination $SaveTo
    }
    Copy-Item -LiteralPath (Join-Path $Stage $Relative) -Destination $Destination
}
$env:PYTHONPATH = Join-Path $Repo 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $Repo
try {
    & 'C:\Python314\python.exe' -m unittest discover -s tests -p 'test_*.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'MOX009 tests failed; do not commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): add consolidated quality gate and review snapshot'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX009-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX009 quality gate and immutable snapshot';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='41 functional tests';qa='independent Quinn QA pending';status='COMMITTED'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX009 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## One bounded acceptance check

Load `demo-mox004`, whose `[ev-demo]` source was registered and attested in MOX-008. Click **Quality Report**. Expect `READY_FOR_HUMAN_REVIEW`, one recognized citation line, one registered source, and one attested source. This is a structural/provenance readiness check, not an independent factual review. Avoid submitting another duplicate of an already reviewed brief merely to exercise the new report.
