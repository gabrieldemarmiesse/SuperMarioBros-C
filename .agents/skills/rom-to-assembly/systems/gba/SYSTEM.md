# Game Boy Advance

Status: workflow guidance; not end-to-end tested by this skill.

## Identify and map

Use [GBATEK](https://problemkaputt.de/gbatek.htm) (also available through
[mGBA's documentation mirror](https://mgba-emu.github.io/gbatek/)) for cartridge
layout, CPU, BIOS interface, and hardware mapping. Validate the cartridge header
against the actual image; preserve original padding and checksum bytes.

Establish cartridge mapping, mirrors, and ROM-to-RAM copies. Record both the ROM
storage offset and runtime execution address for copied routines. Do not map
BIOS addresses to cartridge bytes or treat all ROM content as executable code.

## Recover

Select ARM7TDMI-compatible decoding and distinguish ARM and Thumb state using
entry-state and control-flow evidence. Track state-changing transfers, alignment,
literal pools, indirect calls, jump tables, and exception paths. A plausible
instruction decode alone does not establish the correct mode.

Identify compressed assets or code before analyzing decompressed content.
Keep the original compressed input and map decoded content to its source.
Recompression is not required to explain decompressed code. Do not count opaque compressed code as
reviewed assembly. Document DMA, interrupts, BIOS calls, and memory wait-state
effects where the behavior depends on them.

## Readable output and checking

Explain ARM/Thumb state and literal pools where relevant. Keep storage offsets
and runtime addresses in a separate analysis map, not source comments. Use genuine instructions and mark
unresolved targets. Omit per-address assertions, linker scaffolding, and
build-only padding. Runtime cases should exercise mode transitions and recovered
RAM-executed routines where relevant; a rebuilt cartridge is not required.

Only if the user requests reassembly, choose an ARM7TDMI/Thumb assembler and
place architecture, load addresses, and layout controls in a separate build
layer. Review pseudo-instruction expansion, literal pools, and inserted veneers
for that optional rebuild. Follow the shared optional verification procedure.

Compiled origins do not change this skill's output: deliver assembly and
independently derived comments, without importing existing C decompilations.

## Gameplay investigation

Read [the shared gameplay workflow](../../references/gameplay-analysis.md).

Consider mGBA for GBA investigations. Consult its
[scripting API](https://mgba.io/docs/scripting.html) for the installed release.
Verify input control, callbacks, state handling, frame capture, and debugger
access individually. Use the emulator's actual callback model rather than
copying another emulator's frame-advance loop. Include ARM/Thumb state and
ROM-versus-RAM execution context in traces. Follow the shared capability probe
and experiment workflow.
