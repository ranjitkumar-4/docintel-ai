#!/usr/bin/env python3
"""Generate and index the canonical demo corpus without duplicating records."""

import argparse
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.document_manager import document_manager


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove existing canonical demo records before reseeding; keep user documents.",
    )
    args = parser.parse_args()

    print("DocIntel AI — Seeding canonical demo corpus")
    if args.reset:
        print("Safe reset enabled: only known demo records will be replaced.")

    results = document_manager.seed_demo_corpus(reset=args.reset)
    for doc in results:
        message = doc.error_message or "Indexed successfully"
        print(
            f"{doc.upload_status:7} {doc.filename}: "
            f"{doc.chunks_count} chunk(s); {message}"
        )

    all_docs = document_manager.get_all_documents()
    demo_names = {doc.filename for doc in results}
    counts = {
        name: sum(1 for doc in all_docs if doc.filename == name)
        for name in demo_names
    }
    if any(count != 1 for count in counts.values()):
        print(f"ERROR: demo registry is not unique: {counts}", file=sys.stderr)
        return 1

    print(
        f"Registry verified: {len(demo_names)} unique canonical demo documents "
        f"({len(all_docs)} total registered documents)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
