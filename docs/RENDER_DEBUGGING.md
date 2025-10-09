# Render Debugging Playbook

This guide describes how to reproduce the Render build environment locally so you can iterate on fixes quickly.

## 1. Bootstrap the Python environment

Use the helper script to create a virtual environment that mirrors the dependencies Render expects:

```bash
./scripts/setup-dev-env.sh
```

Set `INSTALL_BACKEND_OPTIONALS=true` if you need the full production dependency stack (it includes large machine learning wheels and may take several minutes to download):

```bash
INSTALL_BACKEND_OPTIONALS=true ./scripts/setup-dev-env.sh
```

## 2. Rebuild frontend assets

Render runs `npm run build` so that FastAPI can serve the compiled static files. You can emulate the same workflow locally:

```bash
pushd frontend
npm ci
npm run build
popd
```

The build artifacts are automatically copied into `backend/frontend_dist/` by `render-build.sh`. Running the script locally ensures the same directory layout that Render expects.

## 3. Execute the Render build script

To verify shell provisioning and dependency installation, run the Render build script directly:

```bash
./render-build.sh
```

The script is idempotent and can be executed multiple times. It installs the required system packages, configures a virtual environment under `/opt/render/project/.venv`, installs Python dependencies, and builds the frontend bundle.

## 4. Run the automated test suite

Once the environment is prepared, execute the tests to confirm the services are healthy:

```bash
source .venv/bin/activate
pytest -q
```

The top-level `requirements.txt` now includes the scientific libraries (`numpy`, `pandas`, and `networkx`) that the backend imports during startup so the tests pass consistently.

## 5. Common troubleshooting tips

- **Missing optional ML dependencies** – Some services (for example causal inference modules) rely on heavy optional packages. Enable the `INSTALL_BACKEND_OPTIONALS` flag when bootstrapping the environment to install everything.
- **Frontend asset mismatch** – Always run `npm run build` after editing the frontend. The backend serves files from `backend/frontend_dist/` and will warn if the directory is missing.
- **Credential configuration** – The `/health` endpoint reports the status of Google Drive credentials and stubbed drive integrations to help verify secrets are configured correctly on Render.

Following these steps provides a reproducible Render-like environment for debugging issues before pushing changes.
