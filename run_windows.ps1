param(
    [switch]$Check
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-SupportedPython {
    param(
        [Parameter(Mandatory)] [string]$FilePath,
        [string[]]$PrefixArguments = @()
    )
    $code = 'import sys; raise SystemExit(sys.version_info[:2] not in ((3, 11), (3, 12), (3, 13)))'
    try {
        $arguments = @($PrefixArguments) + @('-c', $code)
        & $FilePath $arguments *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Find-SupportedPython {
    $candidates = @(
        [pscustomobject]@{ FilePath = 'py'; PrefixArguments = @('-3.12') },
        [pscustomobject]@{ FilePath = 'py'; PrefixArguments = @('-3.11') },
        [pscustomobject]@{ FilePath = 'py'; PrefixArguments = @('-3.13') },
        [pscustomobject]@{ FilePath = 'python'; PrefixArguments = @() }
    )
    foreach ($candidate in $candidates) {
        if (Test-SupportedPython -FilePath $candidate.FilePath -PrefixArguments $candidate.PrefixArguments) {
            return $candidate
        }
    }
    return $null
}

function Test-DiaWiseEnvironment {
    param([Parameter(Mandatory)] [string]$PythonPath)
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        return $false
    }
    if (-not (Test-SupportedPython -FilePath $PythonPath)) {
        return $false
    }
    $imports = 'import fastapi, uvicorn, pydantic, numpy, pandas, sklearn, lightgbm, xgboost, joblib; import app.main'
    try {
        & $PythonPath -c $imports *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Backup-BrokenEnvironment {
    param([Parameter(Mandatory)] [string]$EnvironmentPath)
    if (-not (Test-Path -LiteralPath $EnvironmentPath -PathType Container)) {
        throw "Cannot preserve missing environment: $EnvironmentPath"
    }
    $parent = Split-Path -Parent $EnvironmentPath
    $leaf = Split-Path -Leaf $EnvironmentPath
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = Join-Path $parent "$leaf.broken-$stamp"
    $counter = 2
    while (Test-Path -LiteralPath $backup) {
        $backup = Join-Path $parent "$leaf.broken-$stamp-$counter"
        $counter++
    }
    Move-Item -LiteralPath $EnvironmentPath -Destination $backup
    if ((Test-Path -LiteralPath $EnvironmentPath) -or -not (Test-Path -LiteralPath $backup -PathType Container)) {
        throw "Could not preserve the broken environment at $backup"
    }
    return $backup
}

function Invoke-DiaWiseBootstrap {
    param([switch]$CheckOnly)

    $root = $PSScriptRoot
    Set-Location -LiteralPath $root
    $environmentPath = Join-Path $root '.venv'
    $venvPython = Join-Path $environmentPath 'Scripts\python.exe'

    if ((Test-Path -LiteralPath $environmentPath -PathType Container) -and
        -not (Test-DiaWiseEnvironment -PythonPath $venvPython)) {
        $backup = Backup-BrokenEnvironment -EnvironmentPath $environmentPath
        Write-Host "Existing environment was unusable and was preserved as $backup"
    }

    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        $python = Find-SupportedPython
        if ($null -eq $python) {
            throw 'Python 3.11, 3.12, or 3.13 (64-bit) is required.'
        }
        Write-Host '[1/4] Creating Python environment...'
        $arguments = @($python.PrefixArguments) + @('-m', 'venv', $environmentPath)
        & $python.FilePath $arguments
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            throw 'Python could not create the local virtual environment.'
        }
    }

    Write-Host '[2/4] Checking dependencies...'
    if (-not (Test-DiaWiseEnvironment -PythonPath $venvPython)) {
        Write-Host '[3/4] Installing dependencies - internet is required for this repair...'
        & $venvPython -m pip install -r (Join-Path $root 'requirements.txt')
        if ($LASTEXITCODE -ne 0 -or -not (Test-DiaWiseEnvironment -PythonPath $venvPython)) {
            throw 'DiaWise dependencies could not be installed or imported.'
        }
    } else {
        Write-Host '[3/4] Dependencies are ready.'
    }

    if (-not (Test-Path -LiteralPath (Join-Path $root 'models\food_model.pkl') -PathType Leaf)) {
        throw 'Models are missing. Run train_models_windows.bat first.'
    }
    if ($CheckOnly) {
        Write-Host 'Environment is ready.'
        return 0
    }

    Write-Host '[4/4] Loading models and starting DiaWise...'
    & $venvPython -m app.launcher
    return $LASTEXITCODE
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $exitCode = Invoke-DiaWiseBootstrap -CheckOnly:$Check
        exit $exitCode
    } catch {
        Write-Error $_.Exception.Message
        exit 1
    }
}
