# Installation

NexusIQ uses MCP over STDIO for execution. There is no REST/OpenAPI execution
gateway. The default installation is the provider-keyless core mode.

## Core mode: default quickstart

```bash
git clone https://github.com/Adaptive-Liquidity/Nexus-IQ-temp.git
cd Nexus-IQ-temp
./install.sh --start
./doctor.sh
```

No OpenAI, Anthropic, Gemini, or Ollama configuration is required. On a fresh
install, `install.sh` creates `.env` from `.env.example`, where:

```dotenv
NEXUS_AEON_ENABLED=false
```

The installer generates `NEXUS_AGENTD_AUTH_TOKEN`, vendors only the pinned
Nexus source, builds only the Nexus image, creates the proof/timeline/module
directories, and bakes `data/modules/sample_tool.wasm`. It does not clone or
build AEON-IQ and does not pull the PostgreSQL image.

Core mode provides:

- Nexus WASM execution and sandboxing;
- Proof Capsule generation;
- on-demand `nexus-mcp` through an authenticated `nexus-agentd`;
- no memory write, recall, or AEON timeline service.

Use `./generate-mcp-config.sh` after installation to create MCP client
configuration.

## Memory mode: explicit opt-in

Memory mode adds PostgreSQL, the AEON proxy, and the AEON worker. It is never
enabled because a provider key happens to be present.

1. Start with `.env.example` or the appropriate `.env.<provider>.example`.
2. Set `NEXUS_AEON_ENABLED=true`.
3. Configure a supported provider and its required credential or Ollama URL.
4. Run:

```bash
./install.sh
./start.sh
./doctor.sh
./verify-live-stack.sh
```

Validation runs before vendoring, building, pulling, or starting. An explicit
memory request fails closed if PostgreSQL/AEON secrets, management-key
cross-wiring, HMAC material, or provider configuration is missing.

Provider presets:

| Preset | Embedding dimension | Schema change? |
|---|---:|---|
| `.env.openai.example` | 1536 | No |
| `.env.anthropic.example` | 1536 (OpenAI-compatible embedding configuration) | No |
| `.env.gemini.example` | 768 | Yes; read the preset warning |
| `.env.ollama.example` | Model-dependent | Yes; read the preset warning |

Gemini and Ollama operators must follow the schema warning in the preset before
initializing PostgreSQL. This kit does not alter the pinned product sources or
their migrations automatically.

## Local source checkouts

Core mode needs only Nexus:

```bash
NEXUSIQ_VENDOR_NEXUS=/path/to/Nexus ./install.sh --build-local
```

Memory mode accepts both source checkouts:

```bash
NEXUSIQ_VENDOR_NEXUS=/path/to/Nexus \
NEXUSIQ_VENDOR_AEON=/path/to/AEON-IQ \
./install.sh --build-local
```

The source refs in `install.sh` and `VERSION_MATRIX.md` remain the reproducible
defaults when local checkouts are not supplied.

## Prebuilt images

Set `NEXUSIQ_USE_PREBUILT=true` and a release tag:

```bash
NEXUSIQ_USE_PREBUILT=true NEXUSIQ_IMAGE_TAG=<release-tag> ./install.sh
```

Core mode pulls only the Nexus image. Memory mode pulls Nexus, AEON, and
PostgreSQL. If release images are unavailable, use the source-build default;
do not substitute a provider placeholder.

## Compatibility behavior

For an existing custom `.env` that does not contain `NEXUS_AEON_ENABLED`, the
lifecycle scripts enable memory for backward compatibility and print a warning
requesting an explicit value. Empty or malformed values are configuration
errors. Only case-insensitive `true` and `false` are accepted.

## Security material

- `NEXUS_AGENTD_AUTH_TOKEN` is always required and generated when blank.
- `POSTGRES_PASSWORD`, `MANAGEMENT_API_KEY`, `NEXUS_AEON_MANAGEMENT_KEY`,
  `NEXUS_AEON_HMAC_KEY`, and `AEON_EVIDENCE_SIGNING_KEY` are generated only
  for memory mode.
- When present, `ALLOW_UNAUTH_MANAGEMENT` must be exactly `false` in either
  mode; empty, ambiguous, or truthy values fail closed.
- `.env` is parsed as data and is never sourced or executed.
