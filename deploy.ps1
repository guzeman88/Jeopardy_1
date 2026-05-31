param(
  [string]$Message = "update"
)

Set-Location $PSScriptRoot

git add -A
$changes = (& git status --porcelain)
if (!$changes) {
  Write-Host "Nothing to commit." -ForegroundColor Yellow
  exit 0
}
git commit -m $Message
git push
Write-Host ""
Write-Host "Pushed. Vercel will auto-deploy from GitHub." -ForegroundColor Green
Write-Host "Track progress: https://vercel.com/guzeman88-yahoocoms-projects/jeopardy-1" -ForegroundColor Cyan
