# ROM analysis skills and emulator tools

These optional tools support two related workflows:

- [rom-to-assembly](../.agents/skills/rom-to-assembly/SKILL.md) produces readable,
  organized assembly from a supplied ROM and independent evidence. It avoids
  existing game-specific disassemblies and imported symbols by default. Comments
  explain behavior, without address comments or layout assertions. Reassembly is
  optional. Separate NES, Game Boy/Color, and GBA profiles describe analysis;
  those profiles do not imply executable emulator support for every system.
- [emulator-use](../plugins/emulator-use/skills/emulator-use/SKILL.md) controls a
  local FCEUX process through ten MCP tools. It supports NES cartridges only,
  with bounded input, PNG screenshots, checkpoints, internal RAM reads, CPU
  registers, and bounded write-watch events.

The repository's existing port and disassembly are not inputs to the independent
workflow. Keep them out of a new ROM analysis's evidence unless you deliberately
choose to use existing game work. Neither tool requires rebuilding this C++ port.

## Use the skills

Codex can discover `rom-to-assembly` under `.agents/skills/` in this repository.
For example:

> Use $rom-to-assembly to explain movement in my ROM at /absolute/path/game.nes.

The `emulator-use` skill is bundled with the plugin. To install it and its MCP
configuration, run from the repository root in a local Codex installation:

```sh
codex plugin marketplace add "$PWD"
codex plugin add emulator-use@smb-rom-tools
```

Start a new thread to load the tools, then ask:

> Use emulator-use to play my ROM at /absolute/path/game.nes and investigate movement.

Requirements are a graphical macOS/Linux environment, `uv` on PATH, Python 3.11+
(which uv can provision), and a Lua-enabled FCEUX build. Set `FCEUX_PATH` before
starting Codex if the emulator is not on PATH. Plugin-root/data placeholders in
`.mcp.json` resolve at installation/runtime; no personal filesystem paths are
committed. The compatibility manifest is in `.codex-plugin/plugin.json`.

For another MCP client, use the same stdio server with a working directory of
`plugins/emulator-use` and command:

```sh
uv run --locked --no-dev python -m emulator_use.server
```

Configure that client's executable and working directory for its own checkout.
The server uses stdio; a GUI display is needed by FCEUX, not by the MCP protocol.

## What an experiment does

1. Open a local ROM in an isolated session and inspect a screenshot after boot.
2. Send a short controller input, advance a bounded number of frames, and inspect
   the next screenshot. The emulator pauses and releases input between calls.
3. Save a checkpoint, then compare control and action runs from that checkpoint.
4. Compare internal RAM and use a bounded write watch to identify candidate code.
5. Check the candidate instructions and record confidence before naming routines.

A write hook reports CPU context, not a bank-resolved instruction trace. A changed
RAM byte is a candidate, not proof of its purpose. Checkpoints restore only within
one live session, and a just-restored framebuffer may need a rendering step.

Session artifacts include a copied ROM, hashes, logs, screenshots, and save states.
They default outside this repository under `~/.local/share/emulator-use/sessions/`.
Use a separate local directory if overriding `output_dir`; do not commit session
artifacts, ROMs, personal paths, or saves. The tools expose no arbitrary Lua,
ROM/RAM patching, or side-effecting MMIO reads.

## Replay a recorded path

Open a fresh session, then pass the local FM2 filename to
`load_movie(session_id, movie_path)`. Use `step` without buttons to replay bounded
segments, and the usual screenshots, RAM reads, checkpoints, and write watches
to inspect the path. FCEUX owns playback timing and controller/reset events.
The movie is read-only and copied into the isolated session. Its ROM checksum
must match the cartridge. Requests stop at the movie end rather than silently
continuing gameplay.

Supported movies are power-on text FM2 version 3 with standard gamepad/empty
ports. Binary recordings, embedded savestate starts, Four Score, FDS, and special
controllers are not implemented. A matching ROM still needs compatible emulator
settings/version to stay synchronized. The C++ port's existing movie support can
consume FM2 inputs too, but does not reproduce NES CPU startup or lag timing.

## Validate changes

The ordinary tests need no FCEUX or game ROM:

```sh
cd plugins/emulator-use
uv run --locked --group dev pytest -q
```

The live probes require FCEUX, a GUI, and a local Super Mario Bros. ROM compatible
with the title/start sequence in the tests. They are deliberately opt-in:

```sh
uv run --locked python -m tests.live_probe /absolute/path/game.nes
uv run --locked python -m tests.mcp_probe /absolute/path/game.nes
uv run --locked python -m tests.movie_probe /absolute/path/game.nes
```

The first probe exercises the bridge and deterministic replay. The second uses
the actual MCP stdio transport and checks image responses, input, RAM, checkpoints,
and invalid-request handling. The backend contains no game-specific addresses or
symbols; the probes' menu sequence is only a test fixture. No ROM is distributed.
