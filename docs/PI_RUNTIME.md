# Facktry Pi Runtime

> Orientation summary. `PI_FOUNDATION.md` governs operator-host implementation; `ADR.md` governs harness behavior.

## Pi integration boundary

Facktry must not copy Pi's source code. It must use Pi as a pinned npm dependency and provide a thin operator application around its SDK.

## Architecture

```text
facktry run                 # Python entrypoint
  └─ facktry-run            # Node/TypeScript launcher
      └─ createFacktrySession()
          └─ @earendil-works/pi-coding-agent
              ├─ agent loop
              ├─ streaming
              ├─ TUI / print / RPC modes
              ├─ compaction
              └─ session management
```

Facktry owns only:

- the launcher;
- a **closed `ResourceLoader`**;
- the Facktry system prompt;
- Facktry tools, skills, and the curated recipe catalog;
- the operator session location;
- the Python `agent_api` bridge;
- the isolated research subagent.

Pi already provides `createAgentSession`, `createAgentSessionRuntime`, `InteractiveMode`, `runPrintMode`, `SessionManager`, `ModelRuntime`, and extension APIs.

## Isolation

Do **not** use Pi's default ambient discovery unchanged. It can load:

- `~/.pi/agent/extensions`;
- project `.pi/extensions`;
- global/project skills and prompts.

Facktry must construct a closed loader that exposes only Facktry resources:

```text
Facktry prompt
Facktry tools
Facktry skills
Facktry recipes and recipe notes
Facktry research agent
No ambient user extensions
No project extensions by default
```

Normal `pi` remains completely stock. Facktry must not install anything into `~/.pi/agent/`.

## Package shape

```text
facktry-pi/
  package.json              # depends on pinned Pi version
  src/
    bin/facktry-run.ts
    session/createFacktrySession.ts
    loader/FacktryResourceLoader.ts
    extensions/index.ts
    tools/
  prompts/SYSTEM.md
  agents/research.md
  skills/                  # mirror of canonical docs/skills/
  recipes/                 # recipe catalog/index
  tests/
```

Facktry must pin a compatible Pi dependency and Node engine range rather than depend on the globally installed copy.

## Runtime flow

1. Resolve the `.facktry/` workspace.
2. Create a Pi `ModelRuntime` for model/auth configuration.
3. Create a closed resource loader.
4. Register only the operator tool allowlist.
5. Store Pi sessions under:

   ```text
   .facktry/operator-sessions/
   ```

6. Run either:
   - `InteractiveMode` for `facktry run`;
   - `runPrintMode` for headless execution;
   - RPC if another process needs to drive the operator.

Later, Facktry tools call Python `agent_api`. They do **not** duplicate `govern`, `admit`, or training logic in TypeScript.

Research is a second isolated Pi session—preferably nested with its own session manager and tool allowlist, or alternatively a child `pi --mode json` process. Only its bounded summary returns to the parent.

## References

- [`PI_FOUNDATION.md`](PI_FOUNDATION.md)
- Pi SDK: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/sdk.md`
- Pi extensions: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md`
- Pi package guidance: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/packages.md`
- Full-control SDK example: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/sdk/12-full-control.ts`
- Custom prompt example: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/sdk/03-custom-prompt.ts`
- Tool configuration example: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/sdk/05-tools.ts`
- Subagent example: `/home/admin/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/extensions/subagent/`

Facktry is an operator application/image built on a pinned Pi dependency, not a Pi fork.
