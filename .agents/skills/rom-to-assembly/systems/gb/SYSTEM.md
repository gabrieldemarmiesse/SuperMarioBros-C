# Game Boy / Game Boy Color

Status: workflow guidance; not end-to-end tested by this skill.

## Identify and map

Consult [Pan Docs](https://gbdev.io/pandocs/) for cartridge headers, CPU,
interrupts, and the actual memory bank controller. Resolve DMG/CGB compatibility
and the hardware mode used by the run; file extensions alone are insufficient.
Validate declared sizes against the actual file and retain original checksums.

The cartridge ROM windows are normally $0000-$3FFF and $4000-$7FFF. Resolve both
through the actual controller state; do not assume the lower window always maps
physical bank zero. Track RAM/VRAM banking where relevant. See the
[memory map](https://gbdev.io/pandocs/Memory_Map.html).

## Recover

Use an SM83-compatible decoder, not a generic Z80 decoder. Establish the boot ROM
handoff, cartridge entry, interrupt targets, and used restart targets from the
hardware documentation and bytes. Vector-area bytes can also serve as data.
Track controller writes and label ROM references with physical bank identity.
Review interrupt state, HALT/STOP behavior, DMA, and hardware model differences
against documentation before interpreting affected routines.

## Readable output and checking

Organize by bank and inferred responsibility. Keep original bank/CPU addresses in
a separate analysis map. Omit address comments, per-address assertions, and
build-only padding. Check decoded instructions and targets against the ROM and controller
state. Runtime checks should include relevant bank transitions and hardware
modes, not only boot. A rebuilt cartridge is not required.

Only if the user requests reassembly, evaluate
[RGBDS](https://rgbds.gbdev.io/docs/) and put bank/section constraints in a separate
build layer. Preserve original header bytes rather than silently fixing them.
Use the shared optional reassembly procedure for any requested exact comparison.

## Gameplay investigation

Read [the shared gameplay workflow](../../references/gameplay-analysis.md).

Consider mGBA for Game Boy/Game Boy Color investigations. Consult its
[scripting API](https://mgba.io/docs/scripting.html) for the installed release
and verify support for input, frame callbacks, state handling, and capture.
Confirm the selected hardware mode and bank context. Debugger/watchpoint access
must be checked separately from basic playback. Follow the shared capability
probe and experiment workflow.
