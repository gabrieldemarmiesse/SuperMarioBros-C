# NES-specific reconstruction

Use this reference only for an NES cartridge ROM. Consult authoritative CPU,
iNES/NES 2.0, and mapper documentation for the actual target. FDS images require
a different container and loading model.

## Mapping before analysis

- Validate the NES signature and distinguish iNES from NES 2.0 before calculating
  PRG/CHR sizes. NES 2.0 has extended size encodings; do not assume byte counts
  always use the simple iNES multiplier.
- Account for the 16-byte header, optional 512-byte trainer, PRG, CHR, and any
  extra sections/trailing bytes. CHR size zero can mean CHR RAM. Preserve original
  header bytes in the input; do not normalize them during analysis.
- Decode the mapper and, where available, submapper. Understand power-on mapping,
  fixed/switchable windows, bank granularity, and mapper writes. Do not assume all
  NES ROMs map a flat PRG image at $8000.
- For mapper 0 specifically, 16 KiB PRG is mirrored at $8000 and $C000; 32 KiB PRG
  occupies $8000-$FFFF. Apply this only after establishing mapper 0.
- Resolve vectors at $FFFA-$FFFF through the actual cartridge mapping. Record
  possible bank states when power-on bank selection is uncertain.
- Distinguish ROM offsets, CPU addresses, PPU addresses, and physical banks. Label
  ROM references with a bank identity; identical CPU addresses can mean different
  instructions as banks switch.

## Instruction and behavioral hazards

The NES CPU uses a 6502-derived instruction set with platform-specific behavior.
Use a compatible decoder and emulator. Decimal arithmetic is disabled on the NES
CPU; do not blindly apply a generic 6502 model. Unofficial opcodes must be decoded
and modeled according to the target CPU, or retained as bytes with uncertainty.

Account for zero-page wrapping, the indirect-JMP page-boundary behavior,
relative-branch ranges, interrupt stack behavior, and carry-dependent arithmetic.
Code can pass results through flags and registers without a conventional return
value. Shared tails and branches into the middle of another routine are legal.
Inline tables after calls and stack-manipulating dispatchers defeat naive
function discovery. A trace proves observed paths only, not all possible paths.

PPU/APU/controller/mapper reads and writes are effects, not ordinary variables.
Repeated writes can be significant. Preserve access order, read side effects,
interrupt interactions, DMA stalls, and timing-sensitive loops. Do not merge or
simplify instructions just because a high-level expression seems equivalent.

## Readable output and checking

Keep real instruction modes, branch targets, and bank identity clear. Do not
simplify instructions just to make the listing prettier. Keep addresses in a separate mapping file; omit address comments and
per-address `.assert` guards from readable assembly. Unknown PRG spans can be recorded in an analysis index instead of large
byte dumps in the readable modules. Reassembly is not required.

If the user explicitly requests reassembly, choose an assembler with explicit
encoding controls. In that optional build layer, account for zero-page versus
absolute encoding, branch ranges, bank layout, and unofficial opcodes.

A boot/title-screen check does not validate gameplay, bank transitions, or
interrupt timing. Choose runtime cases that exercise the region being explained
and retain inputs/state needed to repeat them.

## Gameplay investigation

Read [the shared gameplay workflow](../../references/gameplay-analysis.md).

Consider FCEUX for scripted NES investigations. Its
[Lua documentation](https://fceux.com/web/help/LuaFunctionsList.html) covers
controller input, frame advancement, state handling, and memory access. Check
the installed build's supported functions and debugger access before generating
a script; do not assume every frontend exposes the same integration. Use the
shared capability probe, bounded input runs, and recorded experiments.

When the local `emulator-use` plugin tools are available, use them for the shared
gameplay workflow: start a session, alternate bounded steps and screenshots,
compare checkpointed RAM states, and collect focused write-watch events. Its
current backend reports CPU PCs without physical mapper-bank resolution; do not
treat those events as bank-resolved instruction traces.
