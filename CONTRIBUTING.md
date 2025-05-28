# Development Guide

## Backend

1. Install uv

```powershell
# Run in Windows PowerShell:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Configure `.env` file

- Copy `.env.example` to `.env` and modify it as needed.

3. Start the backend server

```powershell
uv run ./main.py
```

## Frontend

1. Install Node.js and PNPM

```powershell
# Run in Windows PowerShell:

# Download and install fnm:
winget install Schniz.fnm
# Download and install Node.js:
fnm install 22
# Verify the Node.js version:
node -v # Should print "v22.x.x".
# Download and install pnpm:
corepack enable pnpm
```

2. Install dependencies

```powershell
cd <project_root>/ui
pnpm install
```

3. Start dev server

```powershell
cd <project_root>/ui
pnpm dev
```

## Docs Site

1. Install Node.js and PNPM

> Skip this step if you have already installed Node.js and PNPM for the frontend.

```powershell
# Run in Windows PowerShell:

# Download and install fnm:
winget install Schniz.fnm
# Download and install Node.js:
fnm install 22
# Verify the Node.js version:
node -v # Should print "v22.x.x".
# Download and install pnpm:
corepack enable pnpm
```

2. Install dependencies

```powershell
cd <project_root>/docs
pnpm install
```

3. Start dev server

```powershell
cd <project_root>/docs
pnpm dev
```
