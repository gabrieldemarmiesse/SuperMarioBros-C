# Adding a system profile

Read when the target is absent from the system index, or the user requests
extending the skill. During a game reconstruction, record provisional platform
research in the game project. Update the installed skill only when that update
is part of the user's request.

Create `systems/<system-id>/SYSTEM.md` when adding reusable guidance. Put
platform-specific parsers, helpers, and references in that same folder as needed;
do not create placeholder folders for unsupported platforms. Link the profile
from `systems/index.md` and state its validation status.

A profile must establish these decisions, or explicitly defer them to researched
target details before analysis:

1. **Identification:** hardware variants, CPU(s), container signatures and byte
   order, headers, size validation, and ambiguity handling.
2. **Mapping:** file-to-ROM-to-runtime address translation, mirrors, bank state,
   overlays, decompression, coprocessors, and execution from RAM.
3. **Entry points:** boot/load process, vectors, instruction modes, and what
   evidence permits seeding code discovery.
4. **Recovery hazards:** CPU state affecting instruction decoding, indirect
   control flow, embedded tables, hardware effects, and timing.
5. **Readable output:** assembly dialect, a separate bank/address analysis map,
   module organization, and how unresolved regions are presented without noise.
6. **Verification:** decoding against original bytes, target resolution,
   meaningful runtime evidence, and coverage denominator. Reassembly is optional;
   describe assembler/layout details only as a separately requested workflow.
7. **Gameplay control:** emulator candidates and authoritative API references;
   how to probe input/release, bounded stepping, capture, state/replay, and
   tracing/watchpoints. Distinguish playback support from debugger support and
   route to the shared gameplay workflow instead of duplicating it.

Use hardware specifications and generic tooling documentation, not game-specific
reverse-engineering projects. Record source links next to the relevant decisions.
Check current tool compatibility before installation; do not assume candidates
are already installed or that their defaults preserve encoding.

For disc images or multi-chip dumps, describe every supplied file, its hash,
ordering/interleaving, and storage-to-runtime mapping. Record normalization and
unpacking steps so addresses can be traced back to input files. Do not require
recreating a disc image or compressed container to explain its executable code.

Exercise parsers on valid and malformed inputs and mapping boundaries. Check
decoding with small CPU fixtures and verify meaningful target/control-flow
samples. An untried profile is guidance, not tested platform support. Preserve
the shared independence rules and optional-only reassembly policy.
