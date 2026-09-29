---
name: emulator-use
description: Play and inspect a local game ROM through emulator MCP tools, using screenshots, bounded controller input, checkpoints, RAM comparisons, and write-watch experiments. Use for gameplay exploration, bug reproduction, and gathering evidence for reverse engineering. Currently supports NES cartridges through local FCEUX.
---

# Emulator Use

Use the plugin's MCP tools to operate the game, not just describe how a person
could play it. Current backend: NES cartridges in FCEUX with a GUI display.
Game Boy, GBA, SNES, and other systems are not implemented by this plugin.

## Open and observe

1. Identify the user's local ROM. Use `start_session` with its absolute path and,
   when working in a project, `output_dir` pointing to the project's gameplay
   analysis folder. The tool creates a unique child directory and copies the ROM.
2. Retain the returned session ID, ROM hash, capability/limitation list, and
   artifact directory. The emulator is paused at startup. An initially blank
   image may require advancing through boot.
3. Use `step` with neutral input, then `screenshot`. Inspect the returned image
   before choosing an action. Screenshots are actual framebuffer images, not
   textual descriptions. Do not claim to have seen an image you have not viewed.
4. Play in short cycles: choose buttons, step a bounded interval, inspect the
   next image, and adapt. Near a suspected event, use shorter intervals.

`step` accepts 1-600 frames and controller-1 buttons `A`, `B`, `start`, `select`,
`up`, `down`, `left`, `right`. Omitted/empty buttons means neutral input. Each
call releases buttons and pauses afterward; pressing a button in one call does
not hold it through the next. Opposite directions are rejected. Discover actions
from visible responses; do not assume a title's controls or scripted menu timing.

For long runs, call `set_speed(session_id, "unthrottled")` to advance faster while
rendering every frame. Actual speed depends on the host; this is not a fixed
multiplier. Frame bounds, input timing, and pausing still apply. Use `"normal"`
to return to real-time pacing. Speed changes advance no frames and persist across
checkpoint restores; `get_status` includes the selected speed.

## Replay an FM2 movie

For a recorded path through the game, start a fresh session and call `load_movie`
with the local `.fm2` path before stepping or creating checkpoints. The tool
checks the movie's ROM checksum against FCEUX's cartridge identity and copies the
file into the session. Do not silently bypass a checksum mismatch or rewrite the
header to make an incompatible recording appear valid.

FCEUX performs native, read-only playback. Use `step` without buttons to advance
bounded segments; the movie supplies both controller ports and reset/power
commands. Inspect screenshots, read RAM, and use `watch_writes` without buttons
at interesting points. Save/load checkpoints to revisit the same movie segment.
`get_status` reports movie position, length, and remaining frames. A step crossing
the end is shortened; further steps advance zero frames. Manual input is rejected
in replay sessions. Open another session for interactive play.

This version accepts power-on text FM2 version 3 with standard gamepad/empty ports.
Binary movies, embedded savestate starts, Four Score, FDS, and special controllers
are rejected explicitly. Record the movie hash and emulator/version/settings with
the experiment. A ROM checksum match alone does not guarantee synchronization
across emulator versions. The C++ port's FM2 input support also omits NES CPU
power-on/lag timing; replay there is not automatically frame-identical to FCEUX.

## Investigate a behavior

Save a checkpoint before an event. Use unique checkpoint names: the tools do not
overwrite existing checkpoints. The full input/action log is in `events.jsonl`.
Checkpoints can only be loaded in their originating live session, even though
state artifacts are retained on disk. Save from-reset input sequences when a
later reproduction matters.

Run a control and action experiment from the same checkpoint with equal frame
counts. Compare screenshots and `read_ram` results. RAM reads are restricted to
NES internal RAM (decimal addresses 0-2047); no MMIO, mapper reads, or writes are
exposed. A changed byte is only a candidate, not proof of its role.

Use `watch_writes` on a candidate RAM byte to gather its writers while advancing
1-120 frames. It accepts the same button list and a 1-512 event limit; the result
reports total writes and whether the returned sample was truncated. Hooks are
removed after each call. Register PCs are hook-time CPU context, not guaranteed
instruction-start addresses; the tool does not resolve physical mapper banks.
Correlate against actual instruction bytes and bank state before naming code.
Do not present these write events as a full CPU execution trace or debugger
breakpoint facility; those tools are not implemented.

Repeat a significant action from the same checkpoint to check reproducibility.
Validate the proposed explanation with a contrasting case. Checkpoint loading
restores CPU/game state but may leave a stale framebuffer until the next rendered
frame; advance the same neutral interval in both runs before visual comparison.
Keep input-event frame numbers separate from wall-clock time. The logical frame
counter counts completed frames from bridge startup and rewinds on checkpoint
load; the log's request IDs establish ordering across rewinds.

Record the question, checkpoint, inputs, observed outcome, candidate state,
write-watch evidence, confidence, and alternative explanations. Link selected
screenshots and logs. Gameplay evidence complements static code inspection;
it cannot identify every routine automatically. For assembly work, keep numeric
addresses in separate analysis files and comments focused on behavior. Do not
import existing game-specific source, symbols, or RAM maps unless requested.

## Session lifecycle and limits

Close sessions with `close_session` when finished. The server owns only the
processes it launches and stops them on shutdown; artifacts remain. There is a
four-session limit. If a command times out or the bridge errors, the owned
emulator is stopped rather than left running inputs. Open a new session after
such a failure; use its log to diagnose the issue.

The backend needs FCEUX on PATH or `FCEUX_PATH` set to its executable, plus a
working graphical desktop. Treat missing emulator/display capability as a real
limitation, not as permission to fabricate gameplay. If tools are not available
in the current thread, say so; do not substitute guessed results. No arbitrary
Lua execution, ROM patching, or user save modification is exposed.
