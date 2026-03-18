param(
    [string]$HostAlias = "agility-ai"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$status = git status --porcelain
if ($status) {
    throw "Working tree is dirty. Commit or stash changes before deploying to the Pi."
}

npm run build

ssh $HostAlias "mkdir -p /home/amcgrean/agility-ai/dist && rm -rf /home/amcgrean/agility-ai/dist/*"
scp -r dist\* "${HostAlias}:/home/amcgrean/agility-ai/dist/"
ssh $HostAlias "/home/amcgrean/agility-ai-local/bin/deploy-agility-ai.sh"
