#!/usr/bin/env python3
"""Export/import human label review CSV for processed JSONL (Epic 105 / VLA-44)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.data.label_review import (  # noqa: E402
    LabelReviewError,
    export_jsonl_to_review_csv,
    import_review_csv_to_jsonl,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Round-trip label review CSV for processed training JSONL.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export_parser = sub.add_parser("export", help="Write review CSV from JSONL.")
    export_parser.add_argument("--jsonl", required=True, help="Input processed train/val JSONL.")
    export_parser.add_argument("--output", required=True, help="Output review CSV path.")

    import_parser = sub.add_parser("import", help="Merge reviewed CSV back into JSONL.")
    import_parser.add_argument("--jsonl", required=True, help="Original processed JSONL.")
    import_parser.add_argument("--csv", required=True, help="Reviewed CSV path.")
    import_parser.add_argument("--output", required=True, help="Output JSONL path.")

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "export":
            count = export_jsonl_to_review_csv(args.jsonl, args.output)
            print(f"Exported {count} rows → {args.output}")
            return 0

        stats = import_review_csv_to_jsonl(
            jsonl_path=args.jsonl,
            csv_path=args.csv,
            output_path=args.output,
        )
        print(
            f"Wrote {stats.output_rows} rows → {args.output} "
            f"(approved={stats.approved}, corrected={stats.corrected}, "
            f"rejected={stats.rejected}, pending={stats.pending_skipped}, "
            f"unchanged={stats.unchanged})"
        )
        return 0
    except (LabelReviewError, FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
