# MOX-004 — Offline CSV Draft Intake

Date: 2026-11-02. Scope: improve local MOXIE opportunity intake throughput. No APIs, no publishing, no RVSC mission requeue.

## Features

- `Import CSV` button within Opportunity & Brief.
- Required CSV headers (any order): `opportunity_id,topic,audience,signal_source,evidence_id,evidence_source,evidence_finding,brief_title,brief_body`.
- Each valid row becomes a saved **draft**, not a submitted QA item. Existing IDs and repeated IDs in the same CSV are rejected, not overwritten.
- Header mismatch fails before any draft is written. Invalid individual rows are counted and entered into local `activity.jsonl` without copying the whole row.
- Imported drafts are selectable from `Saved draft` and still require a human operator to evaluate and queue them.

## Install — LEFT administrator PowerShell

Close MOXIE before installation, keep RIGHT RVSC supervisor stopped. Save `MOX004_INCREMENT.zip` into `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX004_INCREMENT.zip'
$Expected = '0c664315ddf92177410dcba029036252f08aad29'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX004 archive missing' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'Working tree not clean; stopped' }
$Targets = @('src/moxie/batch_import.py','src/moxie/operator_app.py','tests/test_batch_import.py','MOX004_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX004_stage'
if (Test-Path -LiteralPath $Stage) { throw 'MOX004 staging folder exists; inspect before rerun' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX004_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $Backup | Out-Null
foreach ($Relative in $Targets) {
    $Destination = Join-Path $Repo $Relative
    if (Test-Path -LiteralPath $Destination) {
        $CopyTo = Join-Path $Backup $Relative
        New-Item -ItemType Directory -Path (Split-Path $CopyTo) -Force | Out-Null
        Copy-Item -LiteralPath $Destination -Destination $CopyTo
    }
    Copy-Item -LiteralPath (Join-Path $Stage $Relative) -Destination $Destination
}
$env:PYTHONPATH = Join-Path $Repo 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $Repo
try {
    & 'C:\Python314\python.exe' -m unittest discover -s tests -p 'test_*.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; no commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): import offline CSV opportunities as drafts'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX004-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX004 CSV draft intake';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='25 author-side tests and Windows regression';status='COMMITTED';qa='independent Quinn QA pending'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX004 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## Single Windows acceptance check

Use this simple CSV in a separate editor as `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE\moxie_sample.csv`:

```csv
opportunity_id,topic,audience,signal_source,evidence_id,evidence_source,evidence_finding,brief_title,brief_body
demo-mox004,Home gardening,Home gardeners,Operator note,ev-demo,Operator note,Assess local planting conditions,Garden planning,Prepare an evidence-based gardening checklist.
```

In the GUI click **Import CSV**, select that file, and verify `Saved drafts` increases by one while `Awaiting human review` does **not** increase. Load the draft to inspect the populated fields. No repeating the import needed.

## Boundaries

MOX-004 does not perform web collection, AI inference, validation of evidence truth, or automatic content publishing. The full operator end-to-end approval sequence from MOX-003 and independent Quinn QA remain pending until explicitly confirmed. The output artifact contains only changed/new source and tests; existing SQLite state is preserved.
