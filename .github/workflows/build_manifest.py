"""
Build a flat JSON index of every bucket in the backup.

Reads YAML front-matter from each .md file under <buckets_dir> and emits a
single JSON document with one entry per bucket. The output is sorted by
bucket id so day-over-day diffs are minimal — only fields that actually
change (e.g. last_active, activation_count, importance) show up.

Usage:
    python build_manifest.py <buckets_dir> <output_json>
"""

import json
import os
import sys
from datetime import datetime, timezone

import frontmatter


MANIFEST_FIELDS = (
    "name", "type", "domain", "importance",
    "valence", "arousal", "activation_count",
    "created", "last_active",
    "resolved", "digested", "pinned", "protected",
    "tags",
)


def build(buckets_dir: str) -> dict:
    entries = []
    skipped = []
    for root, _dirs, files in os.walk(buckets_dir):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            path = os.path.join(root, fname)
            try:
                post = frontmatter.load(path)
            except Exception as e:
                skipped.append({"file": os.path.relpath(path, buckets_dir), "error": str(e)})
                continue
            meta = post.metadata or {}
            entry = {"id": meta.get("id") or fname[:-3]}
            for field in MANIFEST_FIELDS:
                if field in meta:
                    entry[field] = meta[field]
            entry["rel_path"] = os.path.relpath(path, buckets_dir)
            entries.append(entry)

    entries.sort(key=lambda e: e["id"])

    by_type = {}
    for e in entries:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bucket_count": len(entries),
        "by_type": by_type,
        "skipped": skipped,
        "buckets": entries,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    buckets_dir, out_path = sys.argv[1], sys.argv[2]
    if not os.path.isdir(buckets_dir):
        print(f"buckets dir not found: {buckets_dir}", file=sys.stderr)
        return 1
    manifest = build(buckets_dir)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=False, default=str)
        f.write("\n")
    print(f"Wrote {manifest['bucket_count']} buckets → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
