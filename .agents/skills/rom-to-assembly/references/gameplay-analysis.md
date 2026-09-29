# Gameplay-driven code understanding

Use active play as an experiment, not just a demonstration that the ROM boots.
The goal is to connect a visible event to machine state and a specific code path.
Keep addresses in analysis artifacts, never add address comments or assertions
to the readable assembly. No reassembly is needed for this workflow.

## Establish real emulator control

Choose a local emulator from the system profile and inspect the installed
version's documentation/API. Prefer frame-based scripting or a debugger bridge
for reproducibility. Use available GUI control only when it actually supports the
emulator; do not assume browser tools can control desktop applications.

Probe capabilities in an isolated session with the supplied ROM:

- Load/reset the correct ROM and identify emulator/core version and hardware mode.
- Press and release buttons, run a bounded number of frames, and pause.
- Capture the rendered frame and inspect it with an available image-viewing tool.
- Save and restore state, or replay inputs deterministically from reset.
- Read RAM and, when available, collect registers, bank/mode state, execution
  traces, write watchpoints, and breakpoints.

Record which capabilities actually work. A running process, available API name,
or successful screenshot call alone is not proof of interactive control. Confirm
that an input produces an observed change and that release stops being held.
If screenshots are unavailable, report that the run was trace-based rather than
claiming visual observation. If debugging is unavailable, gameplay can describe
behavior but cannot by itself attribute that behavior to a routine.

Keep battery saves, save states, configuration, and experiment output in the
project session directory. Do not overwrite the user's existing saves. Use
bounded scripts with a frame/time limit and a clear stop condition; ensure
buttons are released and trace hooks removed on completion or failure.

## Observe, act, inspect, repeat

Begin with a short baseline from reset: identify title/menu and enter gameplay
using observed feedback. Discover controls by small input experiments rather
than assuming a particular button means jump or attack. Capture before/after
frames, choose the next action based on what happened, and shorten the step size
near an event of interest. Long blind button sequences produce weak evidence.

Explore behaviors relevant to the task, such as movement, jumping, attacking,
collisions, damage, death, pickups, menus, scrolling, and scene transitions.
Treat these as candidate experiments, not mandatory features every game has.
Save useful checkpoints so that reaching a scene does not need to be repeated.
A full playthrough is not required unless the user requests one.

For each hypothesis:

1. State the question, such as “which state controls horizontal movement?”
2. Start two runs from the same checkpoint: a no-input/control run and a run
   changing one input or condition. Keep frame counts and initial state aligned.
3. Inspect visible differences and compare RAM/register/trace changes. Exclude
   unrelated timers and animation updates before naming candidate variables.
4. Place focused write watchpoints on candidate RAM and trace the writers and
   their callers. Use the physical bank and CPU mode, not just the program counter.
5. Inspect the resulting instruction paths statically. Distinguish input reading,
   state updates, physics, collision correction, and rendering when evidence allows.
6. Repeat with a contrasting case (opposite direction, button release, grounded
   versus airborne, collision versus free movement) to test the explanation.
7. Update names and comments only to the specificity supported by the results.

For example, a byte changing while the player moves may be a screen coordinate,
world coordinate, fractional position, camera offset, or animation counter.
Correlation alone does not justify calling it velocity. A routine running every
frame during a jump is not necessarily the jump routine. Link the event to the
actual data flow and validate a contrasting case.

## Replay and instrumentation

Record ROM hash, emulator version, region/hardware settings, start state or reset
sequence, and frame-numbered input transitions with explicit releases. Define
whether frame numbers refer to input application or frame completion. Save states
are emulator/version-dependent; retain the input sequence from reset when possible.
Replay a key experiment and check that the significant state/event recurs before
calling it reproducible. Log nondeterminism or desynchronization instead of hiding it.

Trace only relevant time windows or address ranges, with size limits, so output
remains usable. Debugger memory inspection must not accidentally perform extra
side-effecting hardware reads; use debugger peek facilities where supported.
Record the phase of sampling relative to input, CPU execution, and rendering.

Ordinary play and observation are the baseline. If a controlled RAM/register
intervention is useful, branch from a copied checkpoint, log the exact change,
and compare with an unmodified control. Do not treat cheated or patched execution
as ordinary game behavior. Keep the source ROM unchanged.

## Evidence artifacts and handoff

Store sessions under the game's `analysis/playthroughs/<session-id>/`. Keep only
artifacts useful for reproduction or the findings: session metadata, inputs,
checkpoint identifiers, selected frames, bounded traces, and experiment notes.
Use installed-emulator formats rather than inventing a supposedly universal
savestate format. Record scripts and launch commands needed to repeat a session.

Each experiment note should include:

- Question and starting checkpoint.
- Input sequence/control case and relevant frame window.
- Visible outcome and measured state changes.
- Candidate routine/symbol and evidence linking it to the event.
- Conclusion, confidence, alternative explanations, and untested cases.
- Links to replay, frames, trace excerpts, and separate address mapping.

Promote supported findings into readable assembly comments focused on behavior.
Keep raw logs and numeric address metadata out of those comments. Summarize what
was played and understood, what remains unvisited, and any missing tool capability.
Never claim that the skill itself provides a working emulator integration until
that integration has been executed successfully in the current environment.
