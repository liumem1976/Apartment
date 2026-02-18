param(
  [string]$repo = "liumem1976/Apartment",
  [string]$branch = "task-b-domain-models",
  [int]$limit = 20,
  [int]$sleep = 15
)

Write-Output "Starting CI poller for $repo branch $branch"
while ($true) {
  $raw = gh run list --repo $repo --limit $limit --json databaseId,workflowDatabaseId,number,headBranch,status,conclusion,createdAt 2>$null
  if (-not $raw) {
    Write-Output "gh run list returned nothing; sleeping $sleep seconds"
    Start-Sleep -Seconds $sleep
    continue
  }

  try {
    $runs = $raw | ConvertFrom-Json
  } catch {
    Write-Output "Failed to parse JSON from gh run list; raw output:"; Write-Output $raw
    Start-Sleep -Seconds $sleep
    continue
  }

  $match = $runs | Where-Object { $_.headBranch -eq $branch } | Select-Object -First 1
  if (-not $match) {
    Write-Output "No run found for branch $branch; listing recent runs for debug"
    $runs | ForEach-Object { Write-Output ("{0} {1} {2} {3}" -f ($_.databaseId -or $_.number), $_.headBranch, $_.status, $_.createdAt) }
    Start-Sleep -Seconds $sleep
    continue
  }

  $id = $match.databaseId
  if (-not $id) { $id = $match.number }
  Write-Output "Found run id: $id (branch: $($match.headBranch)) - fetching logs"

  gh run view $id --repo $repo --log | Out-File -FilePath gh_run_$id.log -Encoding utf8
  $log = Get-Content gh_run_$id.log -Raw
  Write-Output "Running CI auto-fix checker"
  & python .\scripts\ci_monitor_and_fix.py
  if ($log -match "pytest" -or $log -match "collecting" -or $log -match "Traceback" -or $log -match "FieldInfo.*in_") {
    Write-Output "MATCH_FOUND $id"
    break
  }

  Write-Output "No interesting matches in run $id; sleeping $sleep seconds"
  Start-Sleep -Seconds $sleep
}

Write-Output "Poller finished"
