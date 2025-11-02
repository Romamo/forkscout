#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import tiktoken

DEFAULT_ENCODING = "cl100k_base"
IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".cache",
    ".tox",
    ".eggs",
    ".qoder",
    ".next",
    ".dart_tools",
    "__generated__",
    "flutter_build",
    "package-lock.json",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".hex", ".sum", ".STEP", ".step", ".log", ".html", ".lock",
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".xz", ".zst", ".svg",
    ".so", ".dylib", ".dll", ".exe", ".bin", ".obj", ".o", ".a",
    ".ttf", ".otf", ".woff", ".woff2",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".wav", ".flac",
    ".class", ".jar",
    ".sqlite", ".sqlite3", ".db", ".db3",
    ".pyc", ".pyo",
    ".dmg", ".iso",
}

def detect_binary(path: Path, sample_bytes: int = 2048) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_bytes)
            if b"\x00" in chunk:
                return True
        return False
    except Exception:
        return True

def num_tokens_from_string(s: str, encoding_name: str) -> int:
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(s))

def iter_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # mutate dirnames in-place to prune traversal
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fname in filenames:
            p = Path(dirpath) / fname
            files.append(p)
    return files

def count_tokens_in_file(path: Path, encoding_name: str) -> Tuple[int, int]:
    """
    Returns a tuple (tokens, bytes_read). Returns (0, 0) when skipped.
    """
    try:
        ext = path.suffix.lower()
        if ext in BINARY_EXTENSIONS:
            return (0, 0)
        if detect_binary(path):
            return (0, 0)
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        tokens = num_tokens_from_string(text, encoding_name)
        return (tokens, len(text.encode("utf-8", errors="ignore")))
    except Exception:
        return (0, 0)

def format_int(n: int) -> str:
    return f"{n:,}"

def main():
    parser = argparse.ArgumentParser(description="Calculate project size in tokens.")
    parser.add_argument(
        "--root",
        type=str,
        default=str(Path(__file__).resolve().parent),
        help="Root directory to scan (default: repository root)",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default=DEFAULT_ENCODING,
        help=f"Tiktoken encoding to use (default: {DEFAULT_ENCODING})",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default="",
        help="Optional path to write per-file token counts as JSON.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Show top-N largest files by tokens.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    encoding_name = args.encoding

    if not root.exists() or not root.is_dir():
        print(f"Root path does not exist or is not a directory: {root}")
        raise SystemExit(2)

    files = iter_files(root)
    total_tokens = 0
    total_bytes = 0
    processed_files: Dict[str, Dict[str, int]] = {}

    for p in files:
        tokens, bytes_read = count_tokens_in_file(p, encoding_name)
        if tokens > 0 or bytes_read > 0:
            rel = str(p.relative_to(root))
            processed_files[rel] = {"tokens": tokens, "bytes": bytes_read}
            total_tokens += tokens
            total_bytes += bytes_read

    # Sort by tokens desc
    top_items: List[Tuple[str, int]] = sorted(
        ((name, info["tokens"]) for name, info in processed_files.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    total_files = len(processed_files)
    print("Project token size summary")
    print("--------------------------")
    print(f"Root: {root}")
    print(f"Encoding: {encoding_name}")
    print(f"Files processed: {format_int(total_files)}")
    print(f"Total bytes (UTF-8): {format_int(total_bytes)}")
    print(f"Total tokens: {format_int(total_tokens)}")
    if total_files:
        print(f"Average tokens/file: {format_int(total_tokens // total_files)}")
    print()
    print(f"Top {min(args.top, len(top_items))} largest files by tokens:")
    for i, (name, tok) in enumerate(top_items[: args.top], start=1):
        print(f"{i:>3}. {name} - {format_int(tok)} tokens")

    if args.json_out:
        out_path = Path(args.json_out)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "root": str(root),
                        "encoding": encoding_name,
                        "total_files": total_files,
                        "total_bytes": total_bytes,
                        "total_tokens": total_tokens,
                        "files": processed_files,
                    },
                    f,
                    indent=2,
                )
            print(f"\nWrote JSON report to: {out_path}")
        except Exception as e:
            print(f"Failed to write JSON report: {e}")

if __name__ == "__main__":
    main()
