<#
.SYNOPSIS
    Runs the Python sales updater, then commits and pushes data.json to GitHub.

.DESCRIPTION
    This script does NOT fetch any sales data itself. All data collection
    happens inside update_sales.py. The script only:
      1. runs the Python file
      2. checks that data.json is valid and actually changed
      3. commits + pushes data.json (which triggers your static host to redeploy)

.EXAMPLE
    .\update_and_deploy.ps1                      # run once, push to current branch
    .\update_and_deploy.ps1 -Branch main         # refuse to run unless on 'main'
    .\update_and_deploy.ps1 -IntervalSeconds 300 # repeat every 5 minutes
#>
param(
    [string]$Branch = '',                    # optional: required branch; empty = use current branch
    [string]$PythonScript = 'update_sales.py',
    [string]$DataFile = 'data.json',
    [int]$IntervalSeconds = 0                # 0 = run once; >0 = loop forever
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath  = Join-Path $ProjectRoot $PythonScript
$DataPath    = Join-Path $ProjectRoot $DataFile

function Invoke-Git {
    param([string[]]$GitArgs)
    & git -C $ProjectRoot @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($GitArgs -join ' ')"
    }
}

function Invoke-Deploy {
    # --- Sanity checks ---
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git'))) {
        throw "Not a Git repository: $ProjectRoot"
    }
    if (-not (Test-Path -LiteralPath $PythonPath)) {
        throw "Python script not found: $PythonPath"
    }

    $currentBranch = (& git -C $ProjectRoot branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $currentBranch) {
        throw 'Unable to determine the current Git branch.'
    }
    if ($Branch -and $currentBranch -ne $Branch) {
        throw "Current branch is '$currentBranch' but -Branch '$Branch' was required."
    }

    # --- 1. Run the Python file (it fetches the sales and writes data.json) ---
    Write-Host "Running $PythonScript ..."
    & python $PythonPath
    if ($LASTEXITCODE -ne 0) {
        throw "$PythonScript failed (exit code $LASTEXITCODE). Nothing was committed."
    }

    # --- 2. Validate the output ---
    if (-not (Test-Path -LiteralPath $DataPath)) {
        throw "$DataFile was not found after running the Python script."
    }
    try {
        Get-Content -LiteralPath $DataPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop | Out-Null
    } catch {
        throw "$DataFile is not valid JSON: $($_.Exception.Message)"
    }

    # --- 3. Commit + push only if the data file changed ---
    $changes = @(& git -C $ProjectRoot status --porcelain -- $DataFile)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to check Git status.' }

    if ($changes.Count -eq 0) {
        Write-Host "$DataFile did not change. Nothing to commit."
        return
    }

    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
    Invoke-Git -GitArgs @('add', '--', $DataFile)
    # Passing the path again makes sure ONLY this file is committed,
    # even if other files happen to be staged.
    Invoke-Git -GitArgs @('commit', '-m', "Update sales data ($stamp)", '--', $DataFile)
    Invoke-Git -GitArgs @('push', 'origin', $currentBranch)

    Write-Host "Pushed to origin/$currentBranch. Your static site should redeploy shortly."
}

# --- Main ---
if ($IntervalSeconds -le 0) {
    Invoke-Deploy
} else {
    while ($true) {
        Write-Host "`n[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting update cycle."
        try {
            Invoke-Deploy
        } catch {
            # In loop mode, report the error but keep going so one bad run doesn't kill the schedule.
            Write-Warning $_.Exception.Message
        }
        Write-Host "Next run in $IntervalSeconds seconds. Press Ctrl+C to stop."
        Start-Sleep -Seconds $IntervalSeconds
    }
}
