#!/usr/bin/env python
"""Redact sparrow_config.keys (last column) in pg_dump INSERT output.

Usage: redact_sparrow_keys.py INPUT.sql OUTPUT.sql
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

REDACTED_LITERAL = "'\"<<REDACTED>>\"'"
SPARROW_INSERT = re.compile(r"INSERT INTO public\.sparrow_config VALUES ")


def parse_values_list(s: str, open_paren: int) -> tuple[list[tuple[int, int]], int]:
    """Walk forward from `(` at open_paren, return spans of each top-level value
    and the index of the matching `)`. Handles SQL string `''` escapes.
    """
    assert s[open_paren] == "("
    i = open_paren + 1
    val_start = i
    ranges: list[tuple[int, int]] = []
    while True:
        c = s[i]
        if c == "'":
            i += 1
            while True:
                if s[i] == "'":
                    if i + 1 < len(s) and s[i + 1] == "'":
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    i += 1
        elif c == ",":
            ranges.append((val_start, i))
            i += 1
            while s[i] == " ":
                i += 1
            val_start = i
        elif c == ")":
            ranges.append((val_start, i))
            return ranges, i
        else:
            i += 1


def redact(src: str) -> str:
    out: list[str] = []
    pos = 0
    for m in SPARROW_INSERT.finditer(src):
        open_paren = src.index("(", m.end())
        ranges, _ = parse_values_list(src, open_paren)
        last_start, last_end = ranges[-1]
        out.append(src[pos:last_start])
        out.append(REDACTED_LITERAL)
        pos = last_end
    out.append(src[pos:])
    return "".join(out)


def main() -> None:
    src_path = Path(sys.argv[1])
    dst_path = Path(sys.argv[2])
    dst_path.write_text(redact(src_path.read_text()))


if __name__ == "__main__":
    main()
