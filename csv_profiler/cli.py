"""Command-line interface for csv-profiler."""
import argparse
import json
import os
import sys

from .core import profile, read_table, to_markdown


def main(argv=None):
    ap = argparse.ArgumentParser(prog="csv-profiler", description="Profile the columns of a CSV file.")
    ap.add_argument("csvfile")
    ap.add_argument("--delimiter")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-o", "--output")
    args = ap.parse_args(argv)
    with open(args.csvfile, encoding="utf-8-sig", errors="replace", newline="") as fh:
        header, rows = read_table(fh.read(), args.delimiter)
    rep = profile(header, rows)
    out = json.dumps(rep, indent=2, default=str) if args.json else to_markdown(rep, os.path.basename(args.csvfile))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out)
    else:
        sys.stdout.write(out + ("\n" if args.json else ""))
    return 0
