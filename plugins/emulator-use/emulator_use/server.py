"""Run with python -m emulator_use.server (MCP stdio)."""
from contextlib import asynccontextmanager
import atexit
import json
import signal
import threading

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import TextContent, ImageContent

from .backend import Session

sessions: dict[str, Session] = {}
lock = threading.RLock()


def cleanup():
    with lock:
        for session in sessions.values():
            session.close()
        sessions.clear()


@asynccontextmanager
async def lifespan(server):
    try:
        yield {}
    finally:
        cleanup()


atexit.register(cleanup)
mcp = FastMCP('emulator-use', lifespan=lifespan,
    instructions='Play local NES ROMs through FCEUX. Sessions are paused between calls. '
    'Use step then screenshot to observe, checkpoints for paired experiments, and '
    'RAM/write-watch tools for evidence. Watch PCs are CPU addresses, not physical banks. '
    'Close sessions when finished. Never claim to have seen a screen without inspecting the returned image.')


def get_session(session_id: str) -> Session:
    with lock:
        if session_id not in sessions:
            raise ValueError('Unknown session ID')
        return sessions[session_id]


@mcp.tool()
def start_session(rom_path: str, output_dir: str | None = None) -> dict:
    """Open a local NES cartridge in isolated FCEUX, paused. GUI display and FCEUX required.

    Creates a uniquely named session folder, copies the ROM, and records the hash.
    User saves/settings are isolated. Supports up to four simultaneous sessions.
    output_dir is an optional parent for the session's logs, screenshots and checkpoints.
    """
    with lock:
        if len(sessions) >= 4:
            raise ValueError('Close an existing session before opening another (limit 4)')
        session = Session(rom_path, output_dir)
        sessions[session.id] = session
        return session.metadata


@mcp.tool()
def load_movie(session_id: str, movie_path: str) -> dict:
    """Load a local power-on text FM2 movie into a fresh session for native read-only replay.

    Must be called before stepping or creating checkpoints. Checks the FM2 ROM
    checksum against FCEUX's loaded cartridge identity; copies the movie into the
    session directory. Then use step without buttons to replay bounded segments,
    screenshot/read_ram/watch_writes to inspect them, and checkpoints to revisit.
    At the movie end step advances zero frames; manual input is rejected.
    Supports NES standard gamepad ports and reset/power commands. Other FM2 forms
    (binary, Four Score, FDS, embedded save states) are explicitly rejected.
    """
    return get_session(session_id).load_movie(movie_path)


@mcp.tool()
def get_status(session_id: str) -> dict:
    """Get frame number, paused status and CPU registers without advancing the game."""
    return get_session(session_id).status()


@mcp.tool()
def set_speed(session_id: str, mode: str = 'normal') -> dict:
    """Set normal or unthrottled playback without advancing or unpausing.

    Unthrottled runs as fast as the backend allows while rendering every frame.
    Frame limits, movie inputs, screenshots and write watches retain their normal
    semantics. Speed is session-level and persists across checkpoint restores.
    """
    return get_session(session_id).set_speed(mode)


@mcp.tool()
def step(session_id: str, frames: int, buttons: list[str] | None = None) -> dict:
    """Advance exactly 1-600 frames with controller-1 buttons; release and pause afterward.

    Buttons: A, B, start, select, up, down, left, right. Empty means neutral input.
    Use short intervals near events and call screenshot to inspect the result.
    During movie replay omit buttons; advancement stops at the movie end.
    """
    return get_session(session_id).step(frames, buttons or [])


@mcp.tool()
def screenshot(session_id: str) -> list[TextContent | ImageContent]:
    """Return the current 256x240 NES framebuffer as a PNG image, with frame and artifact path.

    Does not advance the game. A just-loaded checkpoint may display the prior
    framebuffer until rendering occurs; step matching neutral frames before comparisons.
    """
    result = get_session(session_id).screenshot()
    data = result.pop('png')
    return [TextContent(type='text', text=json.dumps(result)), Image(data=data, format='png').to_image_content()]


@mcp.tool()
def read_ram(session_id: str, address: int = 0, length: int = 2048) -> dict:
    """Read NES internal RAM only (0..2047), with SHA-256, without advancing.

    Addresses are decimal integers. MMIO and mapper space are deliberately excluded
    to avoid side-effecting reads. Compare control and action runs from one checkpoint.
    """
    return get_session(session_id).ram(address, length)


@mcp.tool()
def save_checkpoint(session_id: str, name: str) -> dict:
    """Save a new named checkpoint. Does not overwrite existing names or user save slots.

    Names: 1-48 letters/digits/underscore/hyphen. Restore only in the same session.
    """
    return get_session(session_id).checkpoint(name)


@mcp.tool()
def load_checkpoint(session_id: str, name: str) -> dict:
    """Restore this session's checkpoint and logical frame counter; release buttons and pause."""
    return get_session(session_id).checkpoint(name, load=True)


@mcp.tool()
def watch_writes(session_id: str, address: int, frames: int,
                 buttons: list[str] | None = None, max_events: int = 128) -> dict:
    """Advance 1-120 frames while watching writes to one internal RAM byte (0..2047).

    Returns bounded write-hook events with CPU registers, value and logical frame.
    max_events is 1-512. Total count and truncation are reported. The hook is removed
    at completion. PC is callback CPU context, not a guaranteed instruction-start
    address; resolve it against code and mapper state before attribution.
    """
    return get_session(session_id).watch(address, frames, buttons or [], max_events)


@mcp.tool()
def close_session(session_id: str) -> dict:
    """Stop only the emulator process owned by this session; preserve experiment artifacts."""
    with lock:
        session = sessions.pop(session_id, None)
        if session is None:
            return {'closed': True, 'already_closed': True}
        return session.close()


def stop_on_signal(signum, frame):
    # MCP clients may terminate stdio servers before their async lifespan exits.
    # Release owned emulator processes before accepting process termination.
    cleanup()
    raise SystemExit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGINT, stop_on_signal)
    mcp.run(transport='stdio')
