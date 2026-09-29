# Emulator Use

A local MCP server and companion skill for playing NES ROMs through FCEUX.
The emulator stays paused between requests. The server uses the official Python
MCP SDK over stdio and a small FCEUX Lua bridge over atomic session-local files.
There is no listening network port or arbitrary-code tool.

## Requirements and launch

- macOS or Linux with a GUI desktop and a Lua-enabled FCEUX build.
- Python 3.11+, `uv`, and the dependencies pinned in `uv.lock`.
- A locally supplied NES cartridge ROM. No ROMs are included.

```sh
uv run --locked --no-dev python -m emulator_use.server
```

Set `FCEUX_PATH` if FCEUX is not on PATH. The plugin resolves its source through
`${PLUGIN_ROOT}` and stores its virtual environment under `${PLUGIN_DATA}/venv`.
It finds `uv` on PATH and does not contain machine-specific launch paths. A new
Codex thread is needed after installation. See the repository's
[setup guide](../../docs/rom-analysis-tools.md) for skill and MCP setup.

## Tools

| Tool | Behavior |
| --- | --- |
| `start_session` | Open a copied ROM with isolated emulator config/saves |
| `load_movie` | Load a matching power-on text FM2 path for native read-only replay |
| `get_status` | Read paused state, logical frame, and CPU registers |
| `step` | Run 1-600 frames with explicit buttons, release, and pause |
| `screenshot` | Return a 256x240 PNG image and save it as an artifact |
| `read_ram` | Read internal RAM only; no side-effecting MMIO reads |
| `save_checkpoint` | Create a named checkpoint without overwriting |
| `load_checkpoint` | Restore a checkpoint within the same live session |
| `watch_writes` | Collect bounded write-hook events while running inputs |
| `close_session` | Stop the owned process and retain artifacts |

Sessions default to `~/.local/share/emulator-use/sessions/<id>/`. The optional
`output_dir` changes their parent directory. Each has a copied ROM, source hash,
emulator identification, logs, screenshots, and checkpoint files. The logical
frame counter rewinds on load; request IDs remain monotonic. Use an identical
neutral step after loading checkpoints when comparing rendered images because
the framebuffer may be stale immediately after load.

For movie replay, call `load_movie(session_id, movie_path)` immediately after
opening a session, then `step` without buttons. The movie is copied locally and
its cartridge checksum must match. Playback stops at EOF and can be revisited
through checkpoints. Supports power-on text FM2 version 3 with standard gamepads;
other FM2 variants are explicitly rejected. The movie probe checks identical
RAM/framebuffer output across checkpoint rewinds and fresh emulator sessions.
See the [FM2 specification](https://fceux.com/web/help/fm2.html) for the format.

Only the NES backend is implemented. It does not resolve physical mapper banks,
provide full instruction traces, or accept arbitrary Lua/ROM/RAM writes. A write
hook's PC is CPU callback context and needs static validation. Readable assembly
and code explanations remain a separate analysis task.

## Validation

```sh
uv run --locked --group dev pytest -q
uv run --locked python -m tests.live_probe /absolute/path/to/game.nes
uv run --locked python -m tests.mcp_probe /absolute/path/to/game.nes
uv run --locked python -m tests.movie_probe /absolute/path/to/game.nes
```

The opt-in live probes currently use a Super Mario Bros. title/start sequence;
use a compatible local ROM. They test the bridge and actual MCP stdio transport,
not game-code interpretation. They create isolated sessions and close their
owned emulator processes. The emulator backend itself has no game-specific
addresses, symbols, or gameplay code.

Generic API sources: [FCEUX Lua](https://fceux.com/web/help/LuaFunctionsList.html),
[FCEUX Lua implementation](https://github.com/TASEmulators/fceux/blob/master/src/lua-engine.cpp),
[FCEUX config isolation](https://github.com/TASEmulators/fceux/blob/master/src/drivers/Qt/config.cpp),
[Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).
