# Portable GitHub + Vercel Deploy Kit

Use this kit when you finish a local app and want the same repeatable path:

1. Initialize Git if needed.
2. Create a GitHub repository.
3. Push `main`.
4. Create/link a Vercel project.
5. Deploy production once.
6. Try to connect the GitHub repo to Vercel for automatic future deploys.

It also writes safe defaults into `.gitignore` and `.vercelignore` so local config, env files, dependencies, deploy-kit files, and dashboard backup JSON files do not get committed or served by Vercel.

The simplest workflow is Vercel Git integration: pushes to `main` deploy production, and other branches create previews. If Vercel cannot access a private repository yet, authorize the repository in Vercel's GitHub integration, then rerun the script or run `npx vercel@51.7.0 git connect <repo-url>`.

## Requirements

- Git
- GitHub CLI, already logged in with `gh auth login`
- Node.js/npm
- Vercel CLI login, handled by `npx vercel@51.7.0 whoami` or `npx vercel@51.7.0 login`

## One-Command Setup

From any app folder:

```powershell
C:\Users\Jorge DeGuzeman\Desktop\code-projects\Project_dashboard_1\deploy-kit\deploy-git-vercel.ps1 -RepoName my-new-app
```

Useful options:

```powershell
# Public GitHub repo
.\deploy-kit\deploy-git-vercel.ps1 -RepoName my-new-app -Visibility public

# Deploy with a different Vercel project name
.\deploy-kit\deploy-git-vercel.ps1 -RepoName my-new-app -VercelProjectName my-vercel-project

# Add a GitHub Actions workflow template to the target repo
.\deploy-kit\deploy-git-vercel.ps1 -RepoName my-new-app -InstallGithubActionsWorkflow

# Only set up GitHub, skip Vercel
.\deploy-kit\deploy-git-vercel.ps1 -RepoName my-new-app -SkipVercel
```

## Two Deployment Modes

**Native Vercel Git integration**

Best default. Vercel watches GitHub directly. Once connected, no GitHub Actions secrets are required.

**GitHub Actions prebuilt deploy**

Use this when you want tests or approval gates before deploy. Add these GitHub repository secrets:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

The workflow template lives at:

`deploy-kit/templates/vercel-prebuilt.yml`

## Notes

- The script writes `.gitignore` and `.vercelignore` defaults for `.vercel`, `.env`, `node_modules`, `deploy-kit`, local design/reference folders, and recovered dashboard backup JSON files.
- If Vercel cannot connect a private GitHub repo, that is usually GitHub App authorization. Visit Vercel's Git integration page and grant repo access.
- For static HTML apps, no build command is needed. Vercel serves the project root.
- For Next.js, Vite, or other framework apps, Vercel auto-detects the framework from the repo.
