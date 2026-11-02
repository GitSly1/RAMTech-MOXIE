# MOX-007 — Local Evidence Citation Coverage Gate

Date: November 2, 2026. Windows baseline: `85b6a94b55ba75b645ad5d055f1ae71f2a26d101`. Author-side tests: 35 passing.

## What was implemented

- New deterministic evidence-quality report counts draft lines with known bracketed evidence references.
- Flags missing citations, unknown IDs, and `[VERIFY]` markers.
- Operator UI **Check Evidence** shows the report and logs a local action.
- **Evaluate & Queue for Human Review** in the UI blocks submission if the report has unresolved citations.
- No automatic source-truth verification, no publishing, no external APIs, no paid inference, and no RVSC mission-store changes.

## Scope and limits

Evidence references must be written as `[ev-demo]`, `[EV-001]`, etc. A claim may still be misleading despite carrying a known reference. The check examines nonempty nonheading lines; it is a conservative, syntactic coverage check and not semantic entailment verification. The current GUI enforces this guard, while the original `FirstSliceWorkflow` contract remains unchanged for backward compatibility; independent QA and direct non-GUI use require their own policy enforcement.

## Install — LEFT administrator PowerShell

Close MOXIE first. Keep the RIGHT RVSC supervisor stopped. Save ZIP as `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE\MOX007_INCREMENT.zip`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX007_INCREMENT.zip'
$Expected = '85b6a94b55ba75b645ad5d055f1ae71f2a26d101'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX007 archive missing' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'Dirty working tree; stopped' }
$Targets = @('src/moxie/evidence_quality.py','src/moxie/operator_service.py','src/moxie/operator_app.py','tests/test_mox007_evidence_quality.py','MOX007_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX007_stage'
if (Test-Path -LiteralPath $Stage) { throw 'Staging folder exists; inspect before rerunning' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX007_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
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
    if ($LASTEXITCODE -ne 0) { throw 'MOX007 tests failed; no commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): report citation coverage and guard operator submission'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX007-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX007 citation coverage guard';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='35 functional tests';qa='independent Quinn QA pending';status='COMMITTED'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX007 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## Single practical acceptance

Load `demo-mox004` and click **Check Evidence**. If the current checklist references `[ev-demo]`, the report should identify citation coverage. Edit one reference to `[UNKNOWN]` in the draft body and click **Check Evidence** again: the report must identify the unknown reference. Do not submit a purposely invalid draft. Restore the body or reload the saved draft afterward. This is a UI acceptance check only, not a verification that the gardening claim is true.
