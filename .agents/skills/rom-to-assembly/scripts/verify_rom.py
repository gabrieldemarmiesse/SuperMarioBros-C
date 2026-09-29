#!/usr/bin/env python3
"""Compare full ROM images without modifying either file; exit 0 iff equal."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(original, rebuilt):
    shared = min(len(original), len(rebuilt))
    differences = sum(a != b for a, b in zip(original, rebuilt))
    differences += abs(len(original) - len(rebuilt))
    samples = []
    for offset in range(max(len(original), len(rebuilt))):
        before = original[offset] if offset < len(original) else None
        after = rebuilt[offset] if offset < len(rebuilt) else None
        if before != after:
            samples.append({"file_offset": offset, "original": before, "rebuilt": after})
            if len(samples) == 16:
                break
    return {
        "equal": original == rebuilt,
        "original_size": len(original),
        "rebuilt_size": len(rebuilt),
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "rebuilt_sha256": hashlib.sha256(rebuilt).hexdigest(),
        "compared_shared_bytes": shared,
        "different_or_missing_bytes": differences,
        "first_differences": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("rebuilt", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.original.read_bytes(), args.rebuilt.read_bytes())
    except OSError as error:
        parser.exit(2, f"Cannot read ROM: {error}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
