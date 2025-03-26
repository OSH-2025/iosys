## Development

### Docs Site

1. Install Node.js and PNPM

```powershell
# Run in Windows PowerShell:

# Download and install fnm:
winget install Schniz.fnm
# Download and install Node.js:
fnm install 22
# Verify the Node.js version:
node -v # Should print "v22.14.0".
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
