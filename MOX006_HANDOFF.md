# MOX-006 — Structured Local Drafts and Draft Version History

Date: 2026-11-02. Base Windows SHA `b05c86b02338c6db2c3b708a07c0efbd73ed22f2`. Author-side tests: 31 passing. No paid API, automated publication, or changes to RVSC qualifications.

## What changed

- Content format selection: Informational article, Checklist, Social media post, Video outline.
- Tone selection: Professional, Friendly, Educational, Concise.
- Local Ollama prompt requests bracketed evidence IDs and `[VERIFY]` for unsupported claims. This is **not** a verified factual citation gate. Operators must review generated statements.
- Every changed Save Draft creates an immutable revision in local `draft_versions`; unchanged repeated saves do not create redundant versions.
- **Versions** button previews saved draft bodies and lets operators restore a chosen version into the editable form. A restored version is persisted only when the operator clicks Save Draft.
- Previous approval decisions, mission-store data, and existing SQLite drafts remain preserved.

## Installation — LEFT administrator PowerShell

Close MOXIE and leave the RIGHT RVSC supervisor stopped. Save `MOX006_INCREMENT.zip` to `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX006_INCREMENT.zip'
$Expected = 'b05c86b02338c6db2c3b708a07c0efbd73ed22f2'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX006 archive missing' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected repository baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'Working tree not clean; stopped' }
$Targets = @('src/moxie/operator_store.py','src/moxie/operator_service.py','src/moxie/local_drafter.py','src/moxie/operator_app.py','tests/test_mox006_versions_and_formats.py','MOX006_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX006_stage'
if (Test-Path -LiteralPath $Stage) { throw 'MOX006 stage already exists; inspect before rerun' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX006_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $Backup | Out-Null
foreach ($Relative in $Targets) {
    $Destination = Join-Path $Repo $Relative
    if (Test-Path -LiteralPath $Destination) {
        $BackupFile = Join-Path $Backup $Relative
        New-Item -ItemType Directory -Path (Split-Path $BackupFile) -Force | Out-Null
        Copy-Item -LiteralPath $Destination -Destination $BackupFile
    }
    Copy-Item -LiteralPath (Join-Path $Stage $Relative) -Destination $Destination
}
$env:PYTHONPATH = Join-Path $Repo 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $Repo
try {
    & 'C:\Python314\python.exe' -m unittest discover -s tests -p 'test_*.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'MOX006 tests failed; do not commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): add configurable drafting and saved revisions'
    if ($LASTEXITCODE -ne 0) { throw 'MOX006 commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX006-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX006 draft versions and configurable Ollama';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='31 functional tests';qa='independent Quinn QA pending';status='COMMITTED'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX006 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## Single acceptance action

Load an existing draft (for example `demo-mox004`), choose **Checklist** and **Friendly**, then click **Local Ollama Draft** once. Verify text is editable and does not automatically enter review. Click **Save Draft**, then **Versions**. Confirm an earlier version is available and can be viewed; you need not restore it. If Ollama is not available, the app should leave the current body intact and report a bounded error.

## Limits and next work

Evidence IDs are operator-supplied; prompt-level `[VERIFY]` guidance is not independent source authentication. Draft version records contain full draft text in the local `operator.sqlite3` database. No change to the original RVSC repository or formal Quinn QA acceptance is implied.
