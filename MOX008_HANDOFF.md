# MOX-008 — Local Evidence Source Registry and Operator Attestation

Date: 2026-11-02. Windows Git baseline `bf9c6756efdd156e5b84097567939b82813eb5fd`. Author-side functional tests: 38 passing.

## Change

- New **Evidence Sources** tab for each opportunity: evidence ID, source type (URL, local document, operator note), source reference, publication date, and excerpt.
- Each newly registered source starts `UNVERIFIED`. An operator may explicitly attest a registered source by name; the stored status changes to `ATTESTED`, with reviewer and UTC timestamp.
- The **Check Evidence** report now shows whether each listed evidence ID has a recorded operator attestation.
- Registration is immutable and duplicate IDs cannot overwrite previously registered provenance. Attestation is final and cannot be repeated.
- The activity log records source registration and attestation, without copying source content.

**Boundaries:** MOXIE does not fetch URLs, open documents, independently validate claims, or prove that an operator attestation is truthful. It does not auto-approve or publish content. `ATTESTED` means a human recorded having reviewed the source, not that external truth verification occurred. Existing draft and approval records remain unchanged.

## Install — LEFT administrator PowerShell

Close MOXIE and leave the RIGHT RVSC supervisor stopped. Download `MOX008_INCREMENT.zip` into `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX008_INCREMENT.zip'
$Expected = 'bf9c6756efdd156e5b84097567939b82813eb5fd'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX008 archive missing' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected repository baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'Working tree not clean; stopped' }
$Targets = @('src/moxie/evidence_registry.py','src/moxie/operator_service.py','src/moxie/operator_app.py','tests/test_mox008_evidence_registry.py','MOX008_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX008_stage'
if (Test-Path -LiteralPath $Stage) { throw 'MOX008 staging folder exists; inspect before rerun' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX008_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
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
    if ($LASTEXITCODE -ne 0) { throw 'MOX008 tests failed; no commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): register evidence sources and operator attestations'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX008-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX008 evidence registry and attestation';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='38 functional tests';qa='independent Quinn QA pending';status='COMMITTED'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX008 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## Single Windows acceptance

1. Load saved opportunity `demo-mox004` on **Opportunity & Brief**.
2. Open **Evidence Sources**. Enter evidence ID `ev-demo`, source type `Operator note`, reference `Sample operator gardening note`, excerpt `Assess local planting conditions`; leave publication date empty and reviewer initially blank.
3. Click **Register Source** and confirm it appears `UNVERIFIED`.
4. Enter your operator name, select `ev-demo`, click **Attest Selected Source**, and confirm the status changes to `ATTESTED`.
5. Return to **Opportunity & Brief** and click **Check Evidence**: the report should show `[ev-demo] ATTESTED by <your name>`.

This single check validates the newly installed UI pathway. It does not establish factual source truth or formal Quinn QA acceptance.
