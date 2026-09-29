# System profiles

Identify hardware and container before choosing a profile. These are workflow
profiles, not turnkey disassemblers; none has been end-to-end validated on a ROM
through this skill yet. Report target-specific validation on each actual run.

| System ID | Applies to | Guidance |
| --- | --- | --- |
| `nes` | NES/Famicom cartridge images; excludes FDS | [NES](nes/SYSTEM.md) |
| `gb` | Game Boy and Game Boy Color cartridges | [Game Boy](gb/SYSTEM.md) |
| `gba` | Game Boy Advance cartridges | [GBA](gba/SYSTEM.md) |

Hardware variants sharing a container/toolchain can share a profile if the
variant is explicit in the manifest and analysis. Different containers or CPUs
need their own handling. An arcade game title does not identify an arcade board;
use board-specific profiles rather than a universal `arcade` memory map.

For SNES, Nintendo 64, PlayStation, FDS, or another unlisted target, follow
[the new-system procedure](../references/adding-system.md). Do not claim these
systems are implemented merely because generic byte comparison works on them.
