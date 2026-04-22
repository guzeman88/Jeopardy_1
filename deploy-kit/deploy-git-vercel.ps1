[CmdletBinding()]
param(
  [string]$ProjectPath = (Get-Location).Path,
  [string]$RepoName,
  [ValidateSet('private', 'public')]
  [string]$Visibility = 'private',
  [string]$VercelProjectName,
  [string]$VercelScope,
  [string]$CommitMessage = 'Initial deploy setup',
  [string]$VercelCliVersion = '51.7.0',
  [switch]$SkipVercel,
  [switch]$SkipGitConnect,
  [switch]$SkipProductionDeploy,
  [switch]$InstallGithubActionsWorkflow
)

$ErrorActionPreference = 'Stop'

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Body
  )

  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  & $Body
}

function Invoke-CommandChecked {
  param(
    [string]$Command,
    [string[]]$Arguments
  )

  Write-Host "+ $Command $($Arguments -join ' ')" -ForegroundColor DarkGray
  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $Command $($Arguments -join ' ')"
  }
}

function Test-Command {
  param([string]$Name)
  $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-GitIgnoreLine {
  param(
    [string]$Path,
    [string]$Line
  )

  if (!(Test-Path $Path)) {
    New-Item -ItemType File -Path $Path | Out-Null
  }

  $content = Get-Content -Path $Path -ErrorAction SilentlyContinue
  if ($content -notcontains $Line) {
    Add-Content -Path $Path -Value $Line
  }
}

function Get-CurrentBranch {
  $branch = (& git branch --show-current).Trim()
  if (!$branch) { $branch = 'main' }
  return $branch
}

if (!(Test-Path $ProjectPath)) {
  throw "ProjectPath does not exist: $ProjectPath"
}

$ProjectPath = (Resolve-Path $ProjectPath).Path
if (!$RepoName) {
  $RepoName = Split-Path $ProjectPath -Leaf
}
if (!$VercelProjectName) {
  $VercelProjectName = $RepoName
}

Invoke-Step "Checking tools" {
  foreach ($tool in @('git', 'gh', 'node', 'npm')) {
    if (!(Test-Command $tool)) {
      throw "Missing required tool: $tool"
    }
  }
  Invoke-CommandChecked git @('--version')
  Invoke-CommandChecked gh @('--version')
  Invoke-CommandChecked npm @('--version')
}

Push-Location $ProjectPath
try {
  Invoke-Step "Preparing .gitignore" {
    $gitignore = Join-Path $ProjectPath '.gitignore'
    foreach ($line in @('.vercel', 'node_modules', '.env', '.env.*', '!.env.example', 'recovered-dashboard-*.json', 'project-dashboard-backup-*.json')) {
      Ensure-GitIgnoreLine -Path $gitignore -Line $line
    }
  }

  Invoke-Step "Preparing .vercelignore" {
    $vercelignore = Join-Path $ProjectPath '.vercelignore'
    foreach ($line in @('.git', '.vercel', '.claude', '_design_refs', 'deploy-kit', 'node_modules', '.env', '.env.*', 'recovered-dashboard-*.json', 'project-dashboard-backup-*.json')) {
      Ensure-GitIgnoreLine -Path $vercelignore -Line $line
    }
  }

  Invoke-Step "Initializing Git" {
    if (!(Test-Path (Join-Path $ProjectPath '.git'))) {
      Invoke-CommandChecked git @('init')
      Invoke-CommandChecked git @('branch', '-M', 'main')
    }
    else {
      Write-Host "Git repo already exists."
    }
  }

  Invoke-Step "Committing local files" {
    Invoke-CommandChecked git @('add', '.')
    $changes = (& git status --porcelain)
    if ($changes) {
      Invoke-CommandChecked git @('commit', '-m', $CommitMessage)
    }
    else {
      Write-Host "Nothing to commit."
    }
  }

  Invoke-Step "Creating or using GitHub repo" {
    $origin = (& git remote get-url origin 2>$null)
    if ($LASTEXITCODE -eq 0 -and $origin) {
      Write-Host "Using existing origin: $origin"
    }
    else {
      $visibilityFlag = "--$Visibility"
      Invoke-CommandChecked gh @('repo', 'create', $RepoName, $visibilityFlag, '--source', '.', '--remote', 'origin')
    }

    $branch = Get-CurrentBranch
    Invoke-CommandChecked git @('push', '-u', 'origin', $branch)
  }

  if ($InstallGithubActionsWorkflow) {
    Invoke-Step "Installing GitHub Actions Vercel workflow template" {
      $workflowDir = Join-Path $ProjectPath '.github\workflows'
      New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
      $source = Join-Path $PSScriptRoot 'templates\vercel-prebuilt.yml'
      $target = Join-Path $workflowDir 'vercel-prebuilt.yml'
      Copy-Item -LiteralPath $source -Destination $target -Force
      Invoke-CommandChecked git @('add', '.github/workflows/vercel-prebuilt.yml')
      $changes = (& git status --porcelain)
      if ($changes) {
        Invoke-CommandChecked git @('commit', '-m', 'Add Vercel GitHub Actions deploy workflow')
        Invoke-CommandChecked git @('push')
      }
    }
  }

  if (!$SkipVercel) {
    $vercelPackage = 'vercel@' + $VercelCliVersion

    Invoke-Step "Checking Vercel login" {
      Invoke-CommandChecked npx @('--yes', $vercelPackage, 'whoami')
    }

    Invoke-Step "Linking Vercel project" {
      $linkArgs = @('--yes', $vercelPackage, 'link', '--yes', '--project', $VercelProjectName)
      if ($VercelScope) {
        $linkArgs += @('--scope', $VercelScope)
      }
      Invoke-CommandChecked npx $linkArgs
    }

    if (!$SkipGitConnect) {
      Invoke-Step "Connecting GitHub repo to Vercel" {
        $remote = (& git remote get-url origin).Trim()
        try {
          Invoke-CommandChecked npx @('--yes', $vercelPackage, 'git', 'connect', $remote)
        }
        catch {
          Write-Warning "Vercel could not connect the GitHub repo. If it is private, authorize it in Vercel Git integration, then rerun this script or run: npx vercel@$VercelCliVersion git connect $remote"
        }
      }
    }

    if (!$SkipProductionDeploy) {
      Invoke-Step "Deploying production" {
        Invoke-CommandChecked npx @('--yes', $vercelPackage, 'deploy', '--prod', '--yes')
      }
    }
  }

  Invoke-Step "Done" {
    $remote = (& git remote get-url origin).Trim()
    Write-Host "GitHub: $remote"
    if (!$SkipVercel) {
      Write-Host "Vercel project: $VercelProjectName"
    }
  }
}
finally {
  Pop-Location
}
