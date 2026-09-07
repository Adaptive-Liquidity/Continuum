# NexusIQ Troubleshooting

Run `./doctor.sh` first. It resolves the configured mode, checks only the
required live service set, and prints explicit PASS, FAIL, WARN, or INFO lines.

## Unexpected runtime mode

Only case-insensitive `true` and `false` are accepted:

```dotenv
NEXUS_AEON_ENABLED=false
```

If the key is absent in an older custom `.env`, memory is enabled for backward
compatibility and every lifecycle command prints a warning. Add an explicit
value. Empty values and aliases such as `yes`, `1`, or `off` are errors.

A provider key does not enable memory automatically.

## Docker not running

Start Docker Desktop or the Docker Engine, then verify `docker info` and
`docker compose version` before re-running the installer.

## Port 8080 already in use

This matters only in memory mode because core mode does not publish AEON. Set a
free `AEON_PORT` in `.env`, then run `./stop.sh && ./start.sh`.

## Missing provider configuration

Core mode does not require a provider. If `NEXUS_AEON_ENABLED=true`,
`./scripts/validate-env.sh` fails before build/start and names the missing key
or Ollama URL. Configure the selected provider, then re-run:

```bash
./install.sh
./start.sh
```

The lifecycle never falls back to core mode after memory was explicitly
requested.

## AEON build is slow or AEON was not vendored

Core mode intentionally does not create `vendor/aeon-iq` and does not build an
AEON image. That is expected, not a failure.

In memory mode the first AEON/Nexus source build may take several minutes. If a
source checkout cannot be cloned, provide it explicitly:

```bash
NEXUSIQ_VENDOR_NEXUS=/path/to/Nexus \
NEXUSIQ_VENDOR_AEON=/path/to/AEON-IQ \
./install.sh
```

## MCP client cannot find connect-mcp.sh

**Symptom:** The MCP client shows an error like "command not found" or fails
to launch the server.

**Fix:** The `command` in the MCP config must be an **absolute path**. Run:

```bash
./generate-mcp-config.sh
```

This bakes the absolute path into the generated config. If you moved the kit
directory after generating the config, re-run the script and repaste the
updated JSON.

If your client still fails, manually set the full path:

```json
{
  "mcpServers": {
    "nexusiq": {
      "command": "/home/you/nexusiq/connect-mcp.sh",
      "args": [],
      "env": {
        "NEXUSIQ_SELFHOST_DIR": "/home/you/nexusiq"
      }
    }
  }
}
```

---

## agentd socket missing

**Symptom:** `./doctor.sh` reports `FAIL nexus-agentd not live (no daemon ping,
socket file absent)`.

**Fix:** Check whether `nexus-agentd` is running and healthy:

```bash
docker compose ps nexus-agentd
./logs.sh nexus-agentd
```

Common causes:
- The selected service set did not pass startup validation or health checks. Re-run `./start.sh`; it starts memory services before agentd only when memory is enabled.
- The image build failed or was not run. Re-run `./install.sh`.

---

## How to read logs

```bash
./logs.sh aeon            # follow AEON-IQ logs
./logs.sh nexus-agentd    # follow the Nexus daemon logs
./logs.sh nexus-mcp       # logs from the last MCP session
./logs.sh postgres        # Postgres logs
./logs.sh                 # follow all services
```

Increase verbosity by setting `RUST_LOG=debug` in `.env` and restarting the
affected service.

---

## How to reset

**Soft reset** — stop the stack, wipe all volumes, restart fresh. This deletes
all stored memories, timeline events, and Postgres data:

```bash
./reset.sh
```

**Manual reset** — stop, remove volumes, re-run install:

```bash
./stop.sh
docker compose down -v
./install.sh
./start.sh
```

**Rotate secrets only** — blank out the secret lines in `.env` (leave keys
like `OPENAI_API_KEY` intact), then re-run:

```bash
./scripts/generate-secrets.sh
./start.sh
```

---

## nexus-mcp handshake fails in doctor

**Symptom:** `FAIL nexus-mcp handshake failed (no tools listed over
connect-mcp.sh)`.

**Check in order:**
1. Is `nexus-agentd` healthy? (`docker compose ps nexus-agentd`)
2. Does the `agentd_run` volume exist and contain the socket?
   (`docker compose exec nexus-agentd test -S /run/nexus/nexus-agentd.sock`)
3. Is the `nexus-mcp` image built? (`docker compose --profile tools build nexus-mcp`)
4. Check logs: `./logs.sh nexus-agentd`

---

## ALLOW_UNAUTH_MANAGEMENT is not false

**Symptom:** validation reports that `ALLOW_UNAUTH_MANAGEMENT` must be exactly
`false`. Empty, ambiguous, and truthy values are rejected so management
authentication cannot be disabled accidentally.

**Fix:** Set it to `false` in `.env`:

```
ALLOW_UNAUTH_MANAGEMENT=false
```

Then apply the selected service set with `./start.sh`. Never leave this enabled
in any real deployment.
