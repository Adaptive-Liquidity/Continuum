# Releasing NexusIQ

This playbook is a maintainer-only process and is **not to be run automatically** by repository users.

## 1) Repos to release

- `adaptiveliquidity/nexusiq` (this repo)
- `adaptiveliquidity/Nexus`
- `adaptiveliquidity/AEON-IQ`

## 2) Prepare release candidates

- Choose one version for the Kit release: `KIT_TAG` (example `v0.1.0`).
- Confirm required source states:
  - Nexus pin used by installer: `NEXUSIQ_NEXUS_REF`
  - AEON-IQ vendored checkout for this release
  - Compose defaults:
    - `NEXUS_IMAGE=nexusiq-nexus:local`
    - `AEON_IQ_IMAGE=nexusiq-aeon:local`
    - `NEXUS_BUILD_CONTEXT=./vendor/nexus`
    - `AEON_BUILD_CONTEXT=./vendor/aeon-iq`

## 3) Cut GitHub Releases (three repos)

Repeat for each repo branch you are ready to release (`nexusiq`/`Nexus`/`AEON-IQ`):

1. `git checkout main && git pull --ff-only`
2. Ensure final docs are committed.
3. `git tag -a <TAG> -m "release: <TAG>"`
4. `git push origin <TAG>`
5. Publish release with notes and assets:

```bash
gh release create <TAG> --repo <OWNER>/<REPO> \
  --title "<REPO> <TAG>" \
  --target main \
  --notes-file RELEASE_NOTES.md
```

For the Kit release, include:

- `VERSION_MATRIX.md` and the final `RELEASING.md`
- checksums file
- composed stack manifest (see below)

## 4) Build and publish Docker images to GHCR

All images are scoped under:

- `ghcr.io/adaptiveliquidity/nexusiq-nexus`
- `ghcr.io/adaptiveliquidity/aeon-iq`
- (compose stack is published as a versioned compose manifest in this repo; no dedicated stack Dockerfile exists today)

### Prerequisites

```bash
echo "${GITHUB_TOKEN}" | docker login ghcr.io -u "${GITHUB_ACTOR}" --password-stdin
docker buildx create --use --name nexusiq-builder || docker buildx use nexusiq-builder
```

### 4.1 Build/publish Nexus image (`nexus` repo binaries + MCP)

Uses the repo-local `docker/Dockerfile.nexus` and the vendored Nexus checkout.

```bash
# Ensure install.sh has copied docker/Dockerfile.nexus to vendor/nexus/Dockerfile.nexusiq
./install.sh

NEXUS_TAG=ghcr.io/adaptiveliquidity/nexusiq-nexus:${KIT_TAG#v}

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --file docker/Dockerfile.nexus \
  --tag "$NEXUS_TAG" \
  --tag ghcr.io/adaptiveliquidity/nexusiq-nexus:latest \
  --push \
  --build-arg NEXUS_VERSION="${KIT_TAG#v}" \
  ./vendor/nexus
```

### 4.2 Build/publish AEON-IQ image

From this repo, AEON is used through the vendored `./vendor/aeon-iq` checkout.

```bash
AEON_IMAGE_TAG=ghcr.io/adaptiveliquidity/aeon-iq:${AEON_TAG}

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --file ./vendor/aeon-iq/Dockerfile \
  --tag "$AEON_IMAGE_TAG" \
  --tag ghcr.io/adaptiveliquidity/aeon-iq:latest \
  --push \
  ./vendor/aeon-iq
```

### 4.3 Publish compose stack images and release artifact

`docker-compose.yml` defines stack services:

- `postgres`
- `aeon`
- `nexus-agentd`
- `nexus-mcp`

Push only the kit-owned images (`nexus-agentd`, `nexus-mcp` share one image; `aeon` is separate):

```bash
export NEXUS_IMAGE="$NEXUS_TAG"
export AEON_IQ_IMAGE="$AEON_IMAGE_TAG"

docker compose -f docker-compose.yml --env-file .env.example build nexus-agentd nexus-mcp aeon
docker compose -f docker-compose.yml --env-file .env.example push nexus-agentd nexus-mcp aeon
```

Generate a release-pinned compose file (the deployable stack reference):

```bash
mkdir -p release
docker compose -f docker-compose.yml --env-file .env.example config \
  > "release/nexusiq-stack-${KIT_TAG#v}.yml"
```

## 5) Generate SHA256 checksums

Create checksums for any release assets you publish:

```bash
sha256sum \
  "release/nexusiq-stack-${KIT_TAG#v}.yml" \
  VERSION_MATRIX.md \
  RELEASING.md \
  > "release/SHA256SUMS-${KIT_TAG#v}.txt"
```

Capture image digests for traceability (record these lines in release notes/checksum bundle):

```bash
for img in "$NEXUS_TAG" "$AEON_IMAGE_TAG" ; do
  docker inspect --format '{{index .RepoDigests 0}}' "$img"
done > "release/image-digests-${KIT_TAG#v}.txt"
```

Append or attach digest + checksum artifacts to the GitHub Releases for discoverability.

## 6) Update VERSION_MATRIX.md after each Kit release

After release tags are final and container artifacts are published:

- Add a new row at the top of `VERSION_MATRIX.md`.
- Set `NexusIQ kit version` to `KIT_TAG`.
- Set `Nexus version` and `AEON-IQ version` to the exact SHAs used for that release.
- Update notes with the published GHCR tags:
  - `ghcr.io/adaptiveliquidity/nexusiq-nexus:<tag>`
  - `ghcr.io/adaptiveliquidity/aeon-iq:<tag>`
- Commit and push the matrix update only if additional source/compatibility state changed after release.

## 7) Signature support (future)

Sigstore/cosign signing of Git tags and GHCR images is a planned follow-up and is not included in this pass.
