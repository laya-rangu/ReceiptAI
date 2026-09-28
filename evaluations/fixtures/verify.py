"""Validate committed fixture facts independently of the renderer and application.

No imports from build.py or backend/app. No API calls, database writes or extraction.
"""

import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(directory=None):
    root = (directory or HERE / "v1").resolve()
    manifest = read_json(root / "manifest.json")
    scenarios = read_json(HERE / "scenarios.json")
    facts = read_json(root / "expected/receipts.json")
    records = facts["records"]
    labels = read_json(root / "expected/extraction.json")
    documents = manifest["documents"]
    by_id = {doc["id"]: doc for doc in documents}
    require(len(by_id) == len(documents), "Duplicate document ID")
    require(
        manifest["synthetic"] is True and facts["synthetic"] is True,
        "Synthetic flags required",
    )
    require(manifest["reference_date"] == "2026-09-28", "Wrong reference date")
    require(
        Counter(doc["cohort"] for doc in documents)
        == {"clear": 60, "challenging": 20, "adversarial": 20, "supplemental": 5},
        "Unexpected cohort counts",
    )
    require(
        len({doc["layout_id"] for doc in documents if doc["cohort"] == "clear"}) == 12,
        "Expected 12 clear layouts",
    )
    require(
        len(labels) == len(documents) and set(labels) == set(by_id),
        "Missing extraction labels",
    )

    for source in ("definitions", "scenarios"):
        actual = hashlib.sha256((HERE / f"{source}.json").read_bytes()).hexdigest()
        require(
            actual == manifest[f"{source}_sha256"],
            f"Changed {source}: rebuild intentionally",
        )

    paths = set()
    for relative, expected_hash in manifest["artifact_hashes"].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root), f"Unsafe fixture path: {relative}")
        require(path.is_file(), f"Missing artifact: {relative}")
        require(
            hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash,
            f"Hash mismatch: {relative}",
        )
        paths.add(relative)
    actual_paths = {
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    }
    require(actual_paths == paths | {"manifest.json"}, "Missing/unlisted artifact")

    groups, hashes, issuers = defaultdict(set), defaultdict(set), defaultdict(set)
    checked_bytes = 0
    for doc in documents:
        path = root / doc["path"]
        require(doc["path"] in paths, f"Untracked document: {doc['id']}")
        data = path.read_bytes()
        checked_bytes += len(data)
        require(len(data) == doc["size_bytes"], f"Size mismatch: {doc['id']}")
        require(
            hashlib.sha256(data).hexdigest() == doc["sha256"],
            f"Document hash mismatch: {doc['id']}",
        )
        require(
            doc["source_record_id"] in records, f"Missing source facts: {doc['id']}"
        )
        require(
            doc["split"] in {"development", "held_out"}, f"Invalid split: {doc['id']}"
        )
        groups[doc["leakage_group"]].add(doc["split"])
        hashes[doc["sha256"]].add(doc["split"])
        issuers[records[doc["source_record_id"]]["merchant_name"]].add(doc["split"])
        label = labels[doc["id"]]
        require(
            label["expected_outcome"] == doc["expected"]["extraction"],
            f"Outcome mismatch: {doc['id']}",
        )
        if doc["expected"]["upload"] == "reject":
            require(
                label["fields"] is None,
                f"Rejected bytes have predicted fields: {doc['id']}",
            )
            continue
        require(
            doc["expected"]["requires_human_confirmation"],
            f"Unreviewed finalization: {doc['id']}",
        )
        require(label["fields"] is not None, f"Missing visible labels: {doc['id']}")
        for field in doc["expected"]["unknown_fields"]:
            value = label["fields"]
            for part in field.split("."):
                value = value[int(part)] if isinstance(value, list) else value[part]
            require(
                value is None,
                f"Hidden field leaked into scored labels: {doc['id']} {field}",
            )
        if doc["content_type"] == "application/pdf":
            reader = PdfReader(io.BytesIO(data), strict=True)
            require(not reader.is_encrypted, f"Accepted PDF is encrypted: {doc['id']}")
            require(
                1 <= len(reader.pages) <= 5, f"Accepted PDF page count: {doc['id']}"
            )
            # Verify an actual receipt raster exists, not just a valid blank PDF.
            require(
                len(reader.pages[0].images) == 1,
                f"PDF lacks receipt image: {doc['id']}",
            )
            image = reader.pages[0].images[0].image
            require(
                image.width > 100 and image.height > 100,
                f"Empty receipt PDF: {doc['id']}",
            )
        else:
            with Image.open(io.BytesIO(data)) as image:
                require(
                    image.format in {"JPEG", "PNG"},
                    f"Accepted image format: {doc['id']}",
                )
                require(
                    image.width * image.height <= 20_000_000,
                    f"Oversized accepted image: {doc['id']}",
                )
                image.verify()
    for name, mapping in [("layout", groups), ("bytes", hashes), ("issuer", issuers)]:
        require(
            all(len(splits) == 1 for splits in mapping.values()),
            f"Cross-split leakage by {name}",
        )

    for doc in documents:
        if doc["cohort"] != "clear":
            continue
        record = records[doc["source_record_id"]]
        require(record["currency"] == "USD", f"Unsupported clear currency: {doc['id']}")
        require(
            date.fromisoformat(record["purchased_at"]) <= date(2026, 9, 28),
            f"Future clear date: {doc['id']}",
        )
        require(record["items"], f"No items: {doc['id']}")
        require(
            all(Decimal(item["quantity"]) > 0 for item in record["items"]),
            f"Invalid quantity: {doc['id']}",
        )
        require(
            all(type(item["line_total_cents"]) is int for item in record["items"]),
            f"Fractional cents: {doc['id']}",
        )
        require(
            sum(item["line_total_cents"] for item in record["items"])
            == record["subtotal_cents"],
            f"Subtotal mismatch: {doc['id']}",
        )
        expected = (
            record["subtotal_cents"] - record["discount_cents"] + record["fees_cents"]
        )
        expected += 0 if record["tax_included"] else record["tax_cents"]
        require(
            expected == record["total_cents"], f"Incorrect clear total: {doc['id']}"
        )

    # Independently authored scenario results are never calculated by the renderer.
    for case in scenarios["financial_cases"]:
        record = records[case["record_id"]]
        if case["expected_errors"]:
            require(
                record["total_cents"] != case["expected_total_cents"],
                "BAD1 accidentally repaired",
            )
        else:
            require(
                record["total_cents"] == case["expected_total_cents"],
                f"Golden total mismatch: {case['record_id']}",
            )
    primary = scenarios["primary"]
    saved_a = [
        records[row["record_id"]]
        for row in primary["records"]
        if row["owner"] == "A" and row["status"] == "READY"
    ]
    require(
        sum(row["total_cents"] for row in saved_a)
        == primary["expected"]["a_all_time_cents"]
        == 3234,
        "All-time golden total",
    )
    require(
        sum(
            row["total_cents"] for row in saved_a if row["purchased_at"] >= "2026-09-01"
        )
        == primary["expected"]["a_this_month_cents"]
        == 2434,
        "This-month golden total",
    )
    require(
        records["Q1"]["subtotal_cents"] == 1275 and records["Q1"]["tax_cents"] == 102,
        "Q1 golden tax",
    )
    price = scenarios["price_comparison"]
    old, new = [records[key]["items"][0] for key in price["record_ids"]]
    delta = Decimal(new["line_total_cents"]) / Decimal(new["quantity"]) - Decimal(
        old["line_total_cents"]
    ) / Decimal(old["quantity"])
    require(delta == price["expected_change_cents"] == 50, "Unit-price golden result")
    boundaries = scenarios["date_boundaries"]
    for period in ["this_month", "last_month", "last_30_days"]:
        case = boundaries[period]
        matching = [
            row
            for row in boundaries["records"]
            if case["start"] <= row["date"] <= case["end"]
        ]
        require(
            [row["id"] for row in matching] == case["ids"],
            f"Date-boundary IDs: {period}",
        )
        require(
            sum(row["total_cents"] for row in matching) == case["total_cents"],
            f"Date-boundary total: {period}",
        )
    require(
        by_id["DUP1_EXACT"]["sha256"] == by_id["P1"]["sha256"],
        "Exact duplicate bytes differ",
    )
    require(
        by_id["DUP1_PHOTO"]["sha256"] != by_id["Q1"]["sha256"],
        "Photo counterpart must differ in bytes",
    )
    require(
        by_id["DUP1_PHOTO"]["source_record_id"] == "Q1", "Cross-source facts differ"
    )
    return {
        "benchmark_documents": 100,
        "supplemental_documents": 5,
        "layouts": 12,
        "cohorts": dict(Counter(doc["cohort"] for doc in documents)),
        "splits": dict(Counter(doc["split"] for doc in documents)),
        "document_bytes": checked_bytes,
        "status": "PASS",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
