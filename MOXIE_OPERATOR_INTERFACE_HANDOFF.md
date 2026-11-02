# MOXIE Operator Interface — incremental Windows installation

Date: 2026-11-02. Scope: MOX-002 author-side interface increment, **not** independent Quinn QA or RVSC mission acceptance.

## Installation — LEFT administrator PowerShell only

Keep the RIGHT RVSC supervisor shell stopped. Save `MOXIE_OPERATOR_INTERFACE_INCREMENT.zip` to `D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE` first.

This package adds exactly `src/moxie/operator_service.py`, `src/moxie/operator_app.py`, `tests/test_operator_service.py`, and this handoff. It does not replace existing source, mission-store state, or Git history.

```powershell
$Repo = 'D:\Py_Proj\RAMTech-MOXIE'
$LogDir = 'D:\RAMTech\RVSC_NOV2026_DEVELOPMENT_INTELLIGENCE'
$Zip = Join-Path $LogDir 'MOXIE_OPERATOR_INTERFACE_INCREMENT.zip'
$Expected = '8f292b89daf9c6c41a2cb83f61e8ab171823f447'
if (-not (Test-Path -LiteralPath $Zip)) { throw "Archive absent: $Zip" }
if ((git -C $Repo rev-parse HEAD).Trim() -ne $Expected) { throw 'Unexpected MOXIE revision; stopped.' }
if ((git -C $Repo status --porcelain)) { throw 'MOXIE working tree not clean; stopped.' }
foreach ($Relative in @('src/moxie/operator_service.py','src/moxie/operator_app.py','tests/test_operator_service.py','MOXIE_OPERATOR_INTERFACE_HANDOFF.md')) {
    if (Test-Path -LiteralPath (Join-Path $Repo $Relative)) { throw "Target exists: $Relative" }
}
Expand-Archive -LiteralPath $Zip -DestinationPath $Repo -Force
$env:PYTHONPATH = (Join-Path $Repo 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $Repo
try {
    & 'C:\Python314\python.exe' -m unittest discover -s tests -p 'test_*.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'Test verification failed; do not commit.' }
    git status --short
    git add -- src/moxie/operator_service.py src/moxie/operator_app.py tests/test_operator_service.py MOXIE_OPERATOR_INTERFACE_HANDOFF.md
    git commit -m 'feat(moxie): add local operator review interface'
    if ($LASTEXITCODE -ne 0) { throw 'Git commit failed.' }
    $NewSHA = (git rev-parse HEAD).Trim()
    $Record = [ordered]@{ action_id='RVSC-NOV26-MOX-UI-001'; timestamp=(Get-Date).ToUniversalTime().ToString('o'); action='Install and verify MOXIE Tkinter operator UI'; repository=$Repo; previous_sha=$Expected; new_sha=$NewSHA; tests='17 headless tests'; qa='author-side only'; status='COMMITTED' }
    $Record | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $LogDir 'actions.jsonl') -Encoding utf8
    Write-Host "COMMITTED MOXIE OPERATOR UI: $NewSHA"
    Write-Host 'Opening local operator interface. Close the window to return to this shell.'
    & 'C:\Python314\python.exe' -m moxie.operator_app
}
finally { Pop-Location }
```

## One bounded graphical acceptance check

Once the window opens, verify the three tabs: Opportunity & Brief, Pending Human Review, and Activity History. Enter an opportunity and its single evidence record, a nonempty title and body, then click **Evaluate & Queue for Human Review**. The pending item should appear and an accepted entry should appear in history. Close the UI. No requeue, publishing, or repeated runtime investigation is authorized by this step.

## Local state and limits

- Data: `%LOCALAPPDATA%\RAMTech\MOXIE\approvals.sqlite3` and `activity.jsonl` (outside Git).
- The activity log captures timestamp, opportunity ID, outcome, and rejection reasons, omitting draft body and evidence findings. The approvals SQLite database retains accepted brief content.
- This is **not** formal independent Quinn QA, nor does it repair or automatically clear the authoritative `MOX-002` blocked mission in RVSC.
- The current form supports one evidence record per draft. The underlying workflow remains capable of multi-evidence input; extending the UI is future work.
