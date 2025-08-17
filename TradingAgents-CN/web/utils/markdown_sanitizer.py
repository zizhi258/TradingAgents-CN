#!/usr/bin/env python3
"""
Markdown sanitizer for Streamlit rendering.

Goals:
- Prevent KaTeX/MathJax warnings by avoiding unintended math mode.
- Escape currency-like "$" and unmatched "$" outside code fences.
- Keep fenced code blocks intact (including ```math).
"""

from __future__ import annotations

import os
import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_UNESCAPED_DOLLAR_RE = re.compile(r"(?<!\\)\$")


def _escape_all_unescaped_dollars(line: str) -> str:
    return _UNESCAPED_DOLLAR_RE.sub(r"\\$", line)


def _enabled() -> bool:
    v = os.getenv("MARKDOWN_SANITIZER_ENABLED", "true").strip().lower()
    return v in {"1", "true", "yes", "on"}


def sanitize_markdown_for_streamlit(md: str) -> str:
    r"""Sanitize Markdown to avoid KaTeX strict warnings.

    Rules (applied outside fenced code):
    - Escape "$" before digits (currency): $123 -> \$123
    - If a line has CJK characters and also contains unescaped "$", escape all "$" in that line.
    - If a line has an odd count of unescaped "$", escape all to avoid unmatched math delimiters.
    - Keep fenced code blocks (``` ... ```) intact.
    """

    if not _enabled():
        return md

    in_code_block = False
    fence_re = re.compile(r"^\s*```")

    out_lines: list[str] = []
    for line in md.splitlines():
        if fence_re.match(line):
            in_code_block = not in_code_block
            out_lines.append(line)
            continue

        if not in_code_block:
            s = line
            # 1) Escape currency-like patterns: $<digit>
            s = re.sub(r"(?<!\\)\$(?=\d)", r"\\$", s)
            # 2) Escape $ preceding common placeholders like $X.XX / $x.xx
            s = re.sub(r"(?<!\\)\$(?=[A-Za-z](?:\.|\d))", r"\\$", s)

            # 3) If CJK present and unescaped $, escape all unescaped $
            if _CJK_RE.search(s) and _UNESCAPED_DOLLAR_RE.search(s):
                s = _escape_all_unescaped_dollars(s)
            else:
                # 4) If odd number of unescaped $, escape them all
                cnt = len(_UNESCAPED_DOLLAR_RE.findall(s))
                if cnt % 2 == 1:
                    s = _escape_all_unescaped_dollars(s)

            out_lines.append(s)
        else:
            out_lines.append(line)

    return "\n".join(out_lines)
