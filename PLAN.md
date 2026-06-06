# Plan: Fix slow container startup, multi-arch image, and README accuracy

Status: changes applied to working tree, not yet committed.

## 1. Problem statement

Running the published image takes a long time to start on every boot:

```
podman run -p 8080:8080 -v tools-cache:/data/cache --env-file .env ghcr.io/pubmarks/tools:latest
WARNING: image platform (linux/amd64) does not match the expected platform (linux/arm64)
   Building tools @ file:///app
Downloading ruff (10.8MiB)
 Downloaded ruff
      Built tools @ file:///app
Uninstalled 1 package in 6ms
Installed 7 packages in 31ms
INFO:     Started server process [25]
```

Two distinct problems are visible:

1. The container **re-resolves and re-installs Python packages on every start** (downloads
   `ruff`, rebuilds the local `tools` package, installs 7 packages) — work that should happen at
   build time, not boot time.
2. The image is **amd64-only**, so on Apple Silicon it runs under emulation (the platform
   warning), which slows everything further.

## 2. Root cause analysis

### 2.1 Runtime re-sync (the main cause)

- The old `Containerfile` CMD was `uv run python -m tools.server`.
- `uv run` **syncs the environment before executing**, and by default it includes *all*
  dependency groups — including the `dev` group (`pytest`, `pytest-asyncio`, `ruff`) declared in
  `pyproject.toml`.
- The build step ran `uv sync --no-dev`, deliberately excluding dev tools. So at every container
  start `uv run` notices they are missing and **downloads + installs them again** ("Downloading
  ruff … Installed 7 packages"), and rebuilds the local wheel ("Built tools @ file:///app").
- `uv.lock` was **not copied into the image**, so the build couldn't pin the resolution and uv had
  more reason to re-resolve at runtime.

### 2.2 Single-arch image

- The CI build job (`.github/workflows/ci.yml`) declared `platforms: linux/amd64,linux/arm64` but
  used `redhat-actions/buildah-build` + `redhat-actions/push-to-registry`. That combination does
  not reliably push a true multi-arch **manifest list**; it published an amd64-only image under
  `latest`, which is why the arm64 host got the platform-mismatch warning.

## 3. Changes

### 3.1 `Containerfile` (DONE)

Rewrote so all dependency work happens at build time and the runtime never syncs:

- Copy `uv.lock` alongside `pyproject.toml` for a reproducible, pinned install.
- `uv sync --locked --no-dev` at build time (fails loudly if the lockfile is stale).
- `CMD [".venv/bin/python", "-m", "tools.server"]` — runs straight from the venv, so no
  `uv run` re-sync, no dev deps downloaded on boot, no wheel rebuild.
- Removed the no-op `apt-get install` block (it installed nothing).

Result: container start becomes "import + bind port", with no network/package work.

### 3.2 `.github/workflows/ci.yml` (DONE)

Replaced the build/push steps with the Docker buildx toolchain, which produces a proper
multi-arch manifest list in a single push:

- `docker/metadata-action@v5` for tags (`latest` on the default branch, long SHA, version on
  tags).
- `docker/setup-qemu-action@v3` + `docker/setup-buildx-action@v3` + `docker/login-action@v3`.
- `docker/build-push-action@v6` with `platforms: linux/amd64,linux/arm64`, `file: Containerfile`,
  and GitHub Actions layer caching (`cache-from`/`cache-to: type=gha`).

The `test` job (uv sync, ruff, pytest on `ubuntu-latest`) is unchanged.

### 3.3 `README.md` (DONE)

Verified every claim against the source; all accurate except one, now fixed:

- `AVGPE_BASE_URL` was documented with no default, but `config.py` and `.env.example` both define
  `https://pubmarks.github.io/datasets/stocks/{ticker}`. Updated the Configuration table to show
  the real default and note that `{ticker}` is interpolated.

Confirmed accurate (no change needed): 10 tool names, `/mcp` endpoint + `/healthz` health check,
all argument columns vs. actual signatures, the supported-indicators list, and the rest of the
Configuration table.

### 3.4 `.containerignore` (CHECKED, no change)

Confirmed it does **not** exclude `uv.lock`, so the new `COPY ... uv.lock` works.

## 4. Verification / rollout

Pre-merge:

1. Ensure the lockfile is current: `uv lock` (otherwise `uv sync --locked` will reject the build).
2. Local native build + run:
   - `podman build --platform linux/arm64 -t tools:local -f Containerfile .`
   - `podman run -p 8080:8080 --env-file .env -v tools-cache:/data/cache tools:local`
   - Confirm: no "Downloading … / Built tools / Installed N packages" lines, no platform warning,
     server starts quickly.
3. Smoke test endpoints:
   - `curl -s localhost:8080/healthz` → `{"status":"ok"}`
   - point an MCP client at `http://localhost:8080/mcp` and list tools (expect 10).

Post-merge:

4. CI runs `test` then `build-push` (on `main`/tags). Confirm the GHCR package shows a manifest
   list with both `linux/amd64` and `linux/arm64`.
5. Re-pull on Apple Silicon: `podman pull ghcr.io/pubmarks/tools:latest` — the warning should be
   gone and startup fast.

## 5. Risks / notes

- `uv sync --locked` makes a stale `uv.lock` a hard build failure — intended, but means the lock
  must be committed and kept in sync with `pyproject.toml`.
- The CI `test` job runs only on amd64; the arm64 image is built under QEMU but not test-executed.
  If arm64 test coverage is wanted later, add a matrix/arm runner.
- First CI run after this change repopulates the GHA build cache, so it will be slower than
  subsequent runs.

## 6. Suggested commit/PR

- Branch off `main` (per repo conventions).
- Suggested message: `fix(container): build deps at build time, publish true multi-arch image`.
- Include README fix in the same PR (small, related).
