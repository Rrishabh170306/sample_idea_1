Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-Url {
    param([string]$url)
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Output "$url -> $($r.StatusCode)"
        return $true
    } catch {
        Write-Output "$url -> ERROR"
        return $false
    }
}

$urls = @(
    'http://127.0.0.1:8000/',
    'http://127.0.0.1:8000/health',
    'http://127.0.0.1:8000/api/schemes'
)

$allOk = $true
foreach ($u in $urls) {
    if (-not (Test-Url $u)) { $allOk = $false }
}

if (-not $allOk) { exit 1 } else { exit 0 }
