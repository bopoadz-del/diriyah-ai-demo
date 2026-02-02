# Render Debugging Playbook

This guide describes how to reproduce the Render build environment locally so you can iterate on fixes quickly.

## 1. Bootstrap the Python environment

Use the helper script to create a virtual environment that mirrors the dependencies Render expects:

```bash
./scripts/setup-dev-env.sh
```

Set `INSTALL_BACKEND_OPTIONALS=true` if you need the optional machine learning and translation stacks (it includes large ML wheels and may take several minutes to download):

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

The top-level `requirements.txt` aggregates the backend runtime and development requirements to keep CI and local runs consistent.

## 5. Common troubleshooting tips

- **Enable verbose logging** – Set `LOG_LEVEL=DEBUG`, `PYTHONUNBUFFERED=1`, and `PYTHONFAULTHANDLER=1` in Render to stream logs immediately and surface tracebacks.
- **Missing optional ML/translation dependencies** – Some services rely on large optional packages. Enable the `INSTALL_BACKEND_OPTIONALS` flag when bootstrapping the environment to install them.
- **Frontend asset mismatch** – Always run `npm run build` after editing the frontend. The backend serves files from `backend/frontend_dist/` and will warn if the directory is missing.
- **Credential configuration** – The `/health` endpoint reports the status of Google Drive credentials and stubbed drive integrations to help verify secrets are configured correctly on Render.
- **Render shell missing git** – If the Render shell shows `git` is unavailable, use **Clear build cache & deploy** so the updated `render-build.sh` provisions git in the next build.

Following these steps provides a reproducible Render-like environment for debugging issues before pushing changes.
