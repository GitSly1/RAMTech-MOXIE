# MOX-003 — Operator Workflow Enhancement

2026-11-02 | Author-side increment | Windows 11 | Standard library only | No API / publisher

## Scope

- Additional evidence records, supplied as `ID | Source | Finding` per line and all cited by deterministic QA.
- Save/reopen local opportunity drafts across app restarts (`operator.sqlite3`).
- Dashboard counters for drafts, pending review and reviewed decisions.
- Human reviewer approves or rejects a QA-accepted item with required reviewer identity and reason. Decisions are final and recorded; **no publishing**.
- Local event journal extended to draft and decision actions.

The existing `approvals.sqlite3` is preserved. Reviewed items are filtered from the pending list through the separate `operator_decisions` table. RVSC `MOX-002` authoritative mission state remains untouched, and independent Quinn QA is still outstanding.

## Installation — LEFT administrator PowerShell

First close the running MOXIE window. Keep the RIGHT RVSC supervisor stopped. Download this increment as `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE\MOX003_INCREMENT.zip`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX003_INCREMENT.zip'
$Expected = '87c760644fc3c7eb5ead2a32c983e2d2376db33c'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX003 archive not found' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected baseline revision; stop' }
if (git -C $Repo status --porcelain) { throw 'Dirty MOXIE working tree; stop' }
$Stage = Join-Path $LogDir 'MOX003_stage'
if (Test-Path -LiteralPath $Stage) { throw 'Staging folder already exists; stop and inspect before rerun' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
$Targets = @(
    'src/moxie/operator_store.py',
    'src/moxie/operator_service.py',
    'src/moxie/operator_app.py',
    'tests/test_operator_workflow_mox003.py',
    'MOX003_HANDOFF.md'
)
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX003_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
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
    if ($LASTEXITCODE -ne 0) { throw 'MOX003 tests failed; do not commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): persist drafts and auditable human review'
    if ($LASTEXITCODE -ne 0) { throw 'MOX003 commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{
        action_id='RVSC-NOV26-MOX003-001'; timestamp=(Get-Date).ToUniversalTime().ToString('o');
        action='MOX003 enhanced local operator workflow'; repository=$Repo;
        previous_sha=$Expected; new_sha=$SHA; backup=$Backup;
        tests='21 passed (Linux author environment + Windows operator acceptance required)';
        qa='author-side; independent Quinn QA outstanding'; status='COMMITTED'
    } | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX003 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## Single Windows acceptance

Verify dashboard counts; save one draft containing an extra evidence line, then load it from the draft selector. Evaluate and queue it; approve it as a named reviewer with a reason. Verify the pending count decreases and the reviewed count rises, and that the activity tab records events. No repeat submission or unnecessary RVSC requeue required.

## Constraints

No web/API dependency, no publishing, no automatic content generation. The identity text is operator-entered rather than OS-authenticated; formal authorization and independent Quinn QA are still pending. SQLite decision recording and JSONL activity are separate writes, so a disk error may cause activity logging to fail after a decision has been persisted; inspect the review counts before retrying, never assume a missing journal entry means the decision did not occur.
