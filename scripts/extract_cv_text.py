#!/usr/bin/env python3

import argparse
import pathlib
import shutil
import subprocess
import sys


def run_command(args: list[str]) -> str:
    completed = subprocess.run(args, check=True, capture_output=True, text=True)
    return completed.stdout


def extract_text(source: pathlib.Path) -> str:
    suffix = source.suffix.lower()

    if suffix in {".txt", ".md"}:
        return source.read_text(encoding="utf-8")

    if suffix == ".docx":
        return run_command(["textutil", "-convert", "txt", "-stdout", str(source)])

    if suffix == ".pdf":
        pdftotext = shutil.which("pdftotext")
        if not pdftotext:
            raise RuntimeError("PDF extraction requires `pdftotext` to be installed.")
        return run_command([pdftotext, str(source), "-"])

    raise RuntimeError(f"Unsupported file type: {suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract plain text from a CV.")
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    args = parser.parse_args()

    source = pathlib.Path(args.input_path).expanduser().resolve()
    output = pathlib.Path(args.output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    text = extract_text(source)
    output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
