# MOX-010 — Claim-Level Evidence Traceability

Date: November 2, 2026. Base Windows commit `d871bd799d3966e34882035a08ccb3bdd860dee4`. Author-side tests: 44 passing.

## Functionality

- New **Claim Review** tab extracts nonempty nonheading draft lines, displaying exact line text and bracketed evidence references.
- A human operator records an immutable claim-specific decision: `supported_by_operator`, `unsupported_by_operator`, or `needs_more_research`, with reviewer and reason.
- A `supported_by_operator` decision requires that all referenced evidence IDs have source registrations and operator attestations. The operator still bears responsibility for checking actual semantic support.
- Each claim ID is derived from opportunity ID, line number and exact claim text. Editing text creates a new unreviewed claim rather than inheriting an old decision.
- Decisions persist locally in `claims.sqlite3`; the activity journal records each decision without duplicating the claim text.

**Limits:** These are line-level review units, not automated clause extraction. A known ID or an operator-supported decision is not independent factual proof. The current consolidated quality gate remains in force for desktop submissions; claim review is a separate operator aid, not yet a requirement for all submissions. No publishing or remote APIs.

## Installation — LEFT administrator PowerShell

Close MOXIE first. Keep RIGHT RVSC supervisor stopped. Save the archive at `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE\MOX010_INCREMENT.zip`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX010_INCREMENT.zip'
$Expected = 'd871bd799d3966e34882035a08ccb3bdd860dee4'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX010 archive missing' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'Working tree not clean; stopped' }
$Targets = @('src/moxie/claim_review.py','src/moxie/operator_service.py','src/moxie/operator_app.py','tests/test_mox010_claim_review.py','MOX010_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX010_stage'
if (Test-Path -LiteralPath $Stage) { throw 'MOX010 staging folder exists; inspect before rerun' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX010_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
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
    if ($LASTEXITCODE -ne 0) { throw 'MOX010 tests failed; no commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): add claim-level human evidence decisions'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX010-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX010 claim-level review and immutable decisions';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='44 functional tests';qa='independent Quinn QA pending';status='COMMITTED'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX010 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## Single Windows acceptance

Load `demo-mox004`, which has the operator-attested source `ev-demo`. Open **Claim Review**, click **Refresh Claims from Draft**, and select the checklist line with `[ev-demo]`. Enter reviewer `Ariel Ramos`, decision `supported_by_operator`, and reason `Reviewed sample gardening note for this demo claim`. Click **Record Claim Decision** and confirm the selected line displays `supported_by_operator`. Do not edit the content or review it again. This records an operator decision, not independent factual validation.
