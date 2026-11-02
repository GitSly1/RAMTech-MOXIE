# MOX-005 — Completed Review History + Optional Local Ollama Drafting

2026-11-02. This increment continues the MOXIE local-only product. Previous Windows repository baseline: `806ce35803d3b99e0d33d4f7d195db8fabfafcd2`.

## Functionality

- New **Completed Reviews** tab shows recorded human decisions, reviewer, date, reason, brief, and citations in read-only form.
- New **Local Ollama Draft** button generates optional editable prose from operator topic, audience and evidence notes.
- Calls local loopback `127.0.0.1:11434` only, with installed `qwen2.5:7b-instruct`, 280-token cap, 2048 context, temperature 0.3, request timeout 65 seconds, and automatic model unload after request.
- Runs in a background UI thread, one request at a time; no additional agents, paid APIs, remote hosts, or publisher.
- Generated text is neither automatically saved nor evaluated/approved; the operator must verify facts and explicitly run the existing QA workflow.

## Installation — LEFT administrator PowerShell

Close MOXIE before installation. Keep the RIGHT RVSC supervisor stopped. Save `MOX005_INCREMENT.zip` under `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE`.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOX005_INCREMENT.zip'
$Expected = '806ce35803d3b99e0d33d4f7d195db8fabfafcd2'
if (-not (Test-Path -LiteralPath $Zip)) { throw 'MOX005 archive not found' }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected MOXIE baseline; stopped' }
if (git -C $Repo status --porcelain) { throw 'MOXIE working tree not clean; stopped' }
$Targets = @('src/moxie/local_drafter.py','src/moxie/operator_app.py','src/moxie/operator_service.py','tests/test_mox005_local_drafting.py','MOX005_HANDOFF.md')
$Stage = Join-Path $LogDir 'MOX005_stage'
if (Test-Path -LiteralPath $Stage) { throw 'MOX005 staging folder already exists; inspect before rerunning' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage
foreach ($Relative in $Targets) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $Relative))) { throw "Archive missing $Relative" }
}
$Backup = Join-Path $LogDir ('MOX005_preinstall_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
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
    if ($LASTEXITCODE -ne 0) { throw 'MOX005 tests failed; no commit' }
    git add -- $Targets
    git commit -m 'feat(moxie): expose completed reviews and optional local drafting'
    if ($LASTEXITCODE -ne 0) { throw 'MOX005 commit failed' }
    $SHA = (git rev-parse HEAD).Trim()
    [ordered]@{action_id='RVSC-NOV26-MOX005-001';timestamp=(Get-Date).ToUniversalTime().ToString('o');action='MOX005 completed reviews and local drafting';previous_sha=$Expected;new_sha=$SHA;backup=$Backup;tests='28 author-side plus Windows';qa='independent Quinn QA pending';status='COMMITTED'} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "MOX005 COMMITTED: $SHA"
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## One bounded Windows acceptance

1. The **Completed Reviews** tab should display the already approved `MOX-TEST-001`, reviewer and decision reason. This reads existing data and does not modify the decision.
2. On **Opportunity & Brief**, load the existing `demo-mox004` draft. Click **Local Ollama Draft** once. It may take up to 65 seconds. If `ollama serve` is not already running, first start Ollama through your normal Windows installation; no extra model download is needed. Generated text must only populate the editable body—no new approval or publishing.
3. If local Ollama is unreachable, the UI should report the failure without erasing the existing draft.

Do not requeue RVSC or repeatedly rerun the model. Independently qualified Quinn QA and truth verification for evidence remain separate work.
