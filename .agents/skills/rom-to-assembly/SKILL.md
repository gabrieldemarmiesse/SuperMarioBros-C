---
name: rom-to-assembly
description: Produce readable, organized, commented assembly directly from a game ROM, with independently derived symbols and evidence-backed explanations. Use for ROM reverse engineering and documenting game behavior or bugs, rather than C decompilation or building an existing third-party disassembly.
---

# ROM to Assembly

Produce readable assembly that explains the supplied ROM. The default deliverable
is for understanding behavior and bugs; reassembly and byte-identical output are
not required. Derive game knowledge independently by default. A byte dump alone
is not an explained disassembly.

Prioritize meaningful labels, coherent routines, and explanatory comments. Do not
emit per-instruction/per-address assertions such as
`.assert * = $90D6, error, "address moved"`. Do not add address comments to the
readable assembly. Keep original addresses in a separate analysis map. Add labels at
entry points, branch targets, and referenced data rather than at every instruction.
Do not add linker configurations, padding, build scripts, or fixed-placement
directives solely to make the reading-oriented output rebuild. Only perform
reassembly work when the user explicitly requests it.

## Evidence and independence

Use the user's ROM, observations from execution, and CPU/platform/mapper
specifications. Generic assemblers, disassemblers, emulators, and analysis tools
are appropriate. Do not search for or import existing game disassemblies,
decompilations, symbol packs, RAM maps, walkthroughs of game internals, or game
source unless the user explicitly changes this constraint. Hardware register
names from platform specifications are fine.

Inspect the provenance of existing project files before reusing them. Quarantine
prior game-derived names and annotations from analysis inputs. Preserve those
files; create a separate output directory when needed. Generic tools may contain
game-specific address tables or imported symbols: audit before reuse. Do not
claim strict clean-room independence if prior work has already been consulted;
state that limitation and support new findings with ROM evidence.

## Establish the target

Identify the supplied file, platform, CPU, container format, memory mapping,
mapper/banking, and ROM revision by hash. Do not identify a revision from its
filename alone. Ask for a ROM path or platform only when it cannot be established
from available files. Do not obtain a game ROM from the internet.

Select exactly one system profile from [systems/index.md](systems/index.md)
after identifying the target. Load only that system's `SYSTEM.md` and any
references it explicitly requires. Profiles provide platform-specific decisions;
the shared recovery and independence rules here still apply. Do not infer support
from an extension or apply NES parsing to another system.

Keep reusable platform guidance and platform-only helpers under
`systems/<system-id>/`. Keep generic comparison tools under `scripts/`. To support
an unlisted system, use [references/adding-system.md](references/adding-system.md);
do not silently modify the installed skill while reconstructing a game.

For a new multi-system workspace, place reconstructions under
`reconstructions/<system-id>/<rom-id>/`, where the ROM identifier includes a hash
prefix. Keep each game's source, extracted assets, manifest, and analysis
together there. Record the full input hash in its manifest. Use the
user's existing layout if specified; do not relocate existing work automatically.
Separate revisions and avoid merging unrelated games' symbols.

Record original size and SHA-256, mapper/region information when known, tool
versions, and analysis commands in a manifest. Keep the input immutable.
Use file offsets plus bank identity and CPU addresses; an address alone is often
ambiguous. Record container boundaries and unexplained regions without filling
the reading-oriented assembly with unrelated raw bytes.

## Play to investigate behavior

Actively play the supplied ROM in a controllable emulator when available, using
short observation/action cycles to investigate the code. Read
[references/gameplay-analysis.md](references/gameplay-analysis.md) before setting
up the session. Use the system profile's emulator guidance and verify actual
control, capture, and debugger capabilities before relying on them.

Progress from visible behavior to candidate memory state, then to the instructions
that read or write it. Alternate gameplay experiments and static analysis; do
not wait for a complete disassembly before trying the game. Record replayable
inputs and evidence for meaningful findings. Playing a scene does not establish
what every routine does. If control or tracing is unavailable, state the precise
limitation and continue the analysis that is possible.

## Recover incrementally

1. Establish a correct memory map and decoder for the target. Keep undecoded
   spans indexed by bank, offset, and length. Show raw bytes only when useful to
   understanding the surrounding code or data; do not disguise a byte dump as
   recovered instructions.
2. Seed analysis from valid reset/interrupt vectors and observed execution.
   Follow control flow, identify branch/call targets, and add cross-references.
   A linear sweep through every byte does not establish code/data boundaries.
3. Track indirect jumps, computed returns, dispatch tables, bank changes,
   RAM-executed code, overlapping instruction streams, and shared entry points.
   Preserve ambiguous regions and explain them rather than inventing functions.
4. Use deterministic emulator traces to resolve uncertainty where possible.
   Record relevant inputs, initial state, frames, bank state, and registers.
   If tracing tools are unavailable, continue static recovery and state the
   limitation; never fabricate execution evidence.
5. Check instruction decoding against ROM bytes, resolve branch destinations,
   and review data boundaries and cross-references. Trace important behavioral
   claims when possible. These checks support the interpretation; assembling a
   replacement ROM is not a prerequisite.

Start with address-based names such as `bank02_9A30`. Introduce semantic names
only after identifying behavior. Separate certainty about executed instructions
from certainty about what the routine means. Track confirmed, inferred, and
unknown findings with bank/address ranges and supporting observations or trace
references. CPU instructions are facts; a name such as “player velocity” may
still be an inference.

## Organize and explain

Split by physical bank first when bank semantics require it, then by established
responsibilities (startup, input, movement, collisions, entities, graphics,
audio, level data). Use meaningful modules as evidence accumulates; do not
create empty subsystems or assign names based on a game's genre. Separate data
and code where justified. Keep original bank/address mappings in a separate
analysis file so organization does not obscure ROM provenance. Comments should
explain behavior, inputs, outputs, and reasoning rather than repeat addresses.

For each reviewed routine or shared entry, document what matters:

- Purpose and evidence/confidence; keep bank/address metadata in the analysis map.
- Inputs in RAM/registers and outputs, including status flags.
- Registers, scratch RAM, stack, and bank state modified or preserved.
- Entry assumptions, shared tails, fall-through paths, and calling conventions.
- Hardware side effects and timing constraints when applicable.
- Arithmetic width, wraparound, signedness, carry/borrow, and edge conditions.

Explain why a branch or bit operation matters rather than paraphrasing every
instruction. Use short C-like pseudocode only when it clarifies behavior; it is
not build input and must preserve the relevant machine semantics. Avoid claims
about original author intent or original variable names.

When investigating a bug, preserve and explain the original behavior first.
Record a reproducible case and the causal instruction path. Keep optional fixes
separate from the explanation of original behavior. Label proposed fixes and
pseudocode as such; do not silently change recovered instructions.

## Deliver and report honestly

Include assembly modules, symbols with provenance/confidence, an address map,
a manifest, and a concise reading/debugging guide. Extract assets only when
useful to the requested analysis. Keep machine-generated analysis separate from
reviewed sources and make regeneration explicit so it cannot overwrite comments.

Report recovered instructions, identified data, unknown regions, reviewed
routines, and unresolved control-flow or mapper assumptions. Use non-overlapping
coverage counts with a clear denominator when reporting byte coverage; track
dual-use bytes separately. State runtime scenarios actually exercised, link
replays and experiment records, and identify code not reached during gameplay.

Correct decoding does not imply that all behavior is understood. If work remains,
leave a reproducible checkpoint and prioritized unresolved regions. Do not block
completion of a requested reading/annotation task on absent reassembly tooling,
ROM hash equality, or exact binary layout.

## Optional reassembly

Only when the user requests a rebuild, create a separate build layer with the
necessary assembler/linker configuration, original assets, and layout controls.
Keep generated layout guards out of the readable modules; prefer section/bank
checks in that build layer over per-instruction assertions.

Build from the recovered source rather than copying the original ROM. For an
explicitly requested byte-identical rebuild, compare the complete files using
`python3 <skill-dir>/scripts/verify_rom.py original rebuilt`. The helper returns
nonzero on differences; it is optional tooling, not the default success criterion.
Verify a fresh build and a controlled source edit in an isolated copy when
establishing a new build pipeline. Report rebuild results separately from
semantic confidence; a matching hash does not prove an explanation is correct.
