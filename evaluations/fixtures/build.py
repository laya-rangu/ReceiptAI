"""Offline, deterministic synthetic receipt renderer. Never imports application code.

Definitions contain authored prices/totals. Rendering does not calculate expected totals.
Use `python -m evaluations.fixtures.build --check` from the repository root.
"""

import argparse
import copy
import hashlib
import importlib.metadata
import io
import json
import struct
import textwrap
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pypdf import PdfWriter

HERE = Path(__file__).resolve().parent
VERSION_DIR = HERE / "v1"
REQUIRED_VERSIONS = {"Pillow": "12.3.0", "pypdf": "6.19.0"}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def money(cents):
    return f"{'-' if cents < 0 else ''}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def load_definitions():
    return json.loads((HERE / "definitions.json").read_text(encoding="utf-8"))


def records_from_definitions(definitions):
    """Expand explicit source facts, without deriving totals from line items."""
    records, metadata = {}, {}
    for layout_index, layout in enumerate(definitions["layouts"]):
        for slot, basket in enumerate(definitions["standard_baskets"], start=1):
            key = f"{layout['id']}-{slot}"
            override = definitions["overrides"].get(key, {})
            record_id = override.get("id", key.upper())
            raw_a, name_a, raw_b, name_b = layout["products"]
            lines = override.get(
                "items",
                [
                    [raw_a, name_a, basket["quantities"][0], basket["line_cents"][0]],
                    [raw_b, name_b, basket["quantities"][1], basket["line_cents"][1]],
                ],
            )
            record = {
                "merchant_name": layout["merchant"],
                "purchased_at": override.get("date", f"2026-09-{slot + 10:02d}"),
                "currency": "USD",
                "items": [
                    {
                        "raw_name": raw,
                        "normalized_name": name,
                        "quantity": quantity,
                        "line_total_cents": amount,
                        "category": layout["category"],
                    }
                    for raw, name, quantity, amount in lines
                ],
                **{
                    field: override.get(field, basket[field])
                    for field in [
                        "subtotal_cents",
                        "discount_cents",
                        "tax_cents",
                        "fees_cents",
                        "total_cents",
                    ]
                },
                "tax_included": override.get("tax_included", False),
                "category": layout["category"],
                "notes": "Synthetic test receipt. Not a real purchase.",
            }
            records[record_id] = record
            metadata[record_id] = {
                "layout": layout,
                "slot": slot,
                "owner": override.get("owner", "B" if layout_index >= 10 else "A"),
                "source_type": override.get("source_type", "PHOTO"),
            }
    records["BAD1"] = {**copy.deepcopy(records["P1"]), "total_cents": 2000}
    return records, metadata


def render_receipt(record, layout, receipt_id, footer_note=None):
    width = layout["width"]
    picture = Image.new("RGB", (width, 1900), "white")
    draw = ImageDraw.Draw(picture)
    body_font = ImageFont.load_default(size=23)
    small_font = ImageFont.load_default(size=17)
    title_font = ImageFont.load_default(size=33)
    total_font = ImageFont.load_default(size=30)
    margin, y = 32, 20
    regions = {}
    style = layout["style"]

    def text(value, font=body_font, align="left", color="black"):
        nonlocal y
        x = (
            margin
            if align == "left"
            else width / 2
            if align == "center"
            else width - margin
        )
        anchor = "lt" if align == "left" else "mt" if align == "center" else "rt"
        bounds = draw.textbbox((x, y), value, font=font, anchor=anchor)
        draw.text((x, y), value, font=font, anchor=anchor, fill=color)
        y += font.size + 13
        return bounds

    def rule(dotted=False):
        nonlocal y
        if dotted:
            for x in range(margin, width - margin, 14):
                draw.line(
                    (x, y, min(x + 7, width - margin), y), fill="#777777", width=1
                )
        else:
            draw.line((margin, y, width - margin, y), fill="#555555", width=1)
        y += 18

    text("SYNTHETIC TEST RECEIPT", small_font, "center")
    text("NOT A PURCHASE - NO PAYMENT", small_font, "center")
    y += 8
    align = (
        "center"
        if style in {"thermal", "ticket", "dotted"}
        else "right"
        if style == "right_header"
        else "left"
    )
    if style in {"boxed", "invoice", "wide"}:
        draw.rectangle(
            (margin - 10, y - 10, width - margin + 10, y + 48), fill="#eeeeee"
        )
    text(record["merchant_name"], title_font, align)
    if style in {"invoice", "right_header", "wide"}:
        text(f"DOCUMENT {receipt_id}", small_font, align)
    regions["date"] = text(f"Purchase date: {record['purchased_at']}", body_font, align)
    text(f"Currency: {record['currency']}", small_font, align)
    rule(style in {"thermal", "dotted"})
    if style in {"quantity_first", "weighed"}:
        text("QTY          DESCRIPTION                 LINE AMOUNT", small_font)
    elif style in {"invoice", "wide", "ruled"}:
        text("DESCRIPTION                             QTY      LINE AMOUNT", small_font)
    elif style == "ticket":
        text("YOUR ORDER", small_font, "center")
    else:
        text("ITEMS (amounts are line totals)", small_font)
    for index, item in enumerate(record["items"]):
        raw = item["raw_name"]
        prefix = f"{index + 1:02d}. " if style == "numbered" else ""
        if style in {"quantity_first", "weighed"}:
            prefix = f"{item['quantity']} x  "
        name = prefix + raw
        wrap_width = 31 if width >= 760 else 24
        first_name_bounds = None
        for line in textwrap.wrap(name, width=wrap_width, break_long_words=True):
            bounds = text(line)
            first_name_bounds = first_name_bounds or bounds
        if index == 0:
            regions["first_item_name"] = first_name_bounds
        if style in {"quantity_first", "weighed"}:
            # Quantity already printed beside the item name.
            text(money(item["line_total_cents"]), body_font, "right")
        elif style in {"invoice", "wide", "ruled"}:
            draw.text(
                (width - 200, y), f"{item['quantity']} x", font=small_font, fill="black"
            )
            text(money(item["line_total_cents"]), body_font, "right")
        else:
            draw.text(
                (margin + 12, y),
                f"Qty {item['quantity']}",
                font=small_font,
                fill="#444444",
            )
            text(money(item["line_total_cents"]), body_font, "right")
        if style in {"ruled", "boxed", "numbered"}:
            rule(style == "numbered")
        elif style == "stacked":
            y += 12
    rule(style in {"thermal", "ticket", "dotted"})
    regions["totals_start"] = y
    for label, key in [
        ("Subtotal", "subtotal_cents"),
        ("Discount", "discount_cents"),
        ("Tax (included)" if record["tax_included"] else "Tax", "tax_cents"),
        ("Fees", "fees_cents"),
    ]:
        draw.text((margin, y), label, font=body_font, fill="black")
        value = ("-" if key == "discount_cents" and record[key] else "") + money(
            record[key]
        )
        text(value, body_font, "right")
    rule()
    draw.text((margin, y), f"TOTAL {record['currency']}", font=total_font, fill="black")
    regions["total"] = text(money(record["total_cents"]), total_font, "right")
    if footer_note:
        y += 18
        for line in textwrap.wrap(
            footer_note, width=max(30, (width - 2 * margin) // 10)
        ):
            text(line, small_font)
    y += 20
    rule(True)
    text(f"Fixture {receipt_id} - synthetic data only", small_font, "center")
    if y + 25 > picture.height:
        raise ValueError(f"Receipt exceeds canvas: {receipt_id}")
    return picture.crop((0, 0, width, y + 25)), regions


def image_bytes(image, kind="png"):
    buffer = io.BytesIO()
    if kind == "jpg":
        image.save(buffer, format="JPEG", quality=92, subsampling=0, optimize=False)
    elif kind == "gif":
        image.save(buffer, format="GIF")
    else:
        image.save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def image_pdf(image, pages=1, action=False):
    """Minimal deterministic image-only PDF, with accurate byte offsets.

    The optional rejection fixture contains only an internal page-navigation action.
    There is no JavaScript, shell command, attachment, URL, or network operation.
    """
    width, height = image.size
    compressed = zlib.compress(image.convert("RGB").tobytes(), level=9)
    page_ids = [5 + i * 2 for i in range(pages)]
    catalog = b"<< /Type /Catalog /Pages 2 0 R"
    if action:
        catalog += b" /OpenAction [5 0 R /Fit]"
    objects = [
        catalog + b" >>",
        (
            f"<< /Type /Pages /Count {pages} /Kids ["
            + " ".join(f"{p} 0 R" for p in page_ids)
            + "] >>"
        ).encode(),
        (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(compressed)} >>\nstream\n"
        ).encode()
        + compressed
        + b"\nendstream",
        b"<< /Producer (ReceiptAI synthetic fixture renderer v1) >>",
    ]
    for page_id in page_ids:
        content = f"q {width} 0 0 {height} 0 0 cm /ReceiptImage Do Q\n".encode()
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
                f"/Resources << /XObject << /ReceiptImage 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
            ).encode()
        )
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"endstream"
        )
    document = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R /Info 4 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(document)


def encrypted_pdf(data):
    # Deliberately obsolete encryption, solely to exercise rejection; never used for storage.
    writer = PdfWriter(clone_from=io.BytesIO(data))
    writer.encrypt("synthetic-fixture-only", algorithm="RC4-40")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def corrupt_or_change(image, regions, transform):
    altered = image.copy()
    unknown = []
    if transform == "rotated":
        altered = altered.rotate(
            8, resample=Image.Resampling.BICUBIC, expand=True, fillcolor="white"
        )
    elif transform == "blurred":
        altered = altered.filter(ImageFilter.GaussianBlur(2.5))
    elif transform == "cropped_totals":
        altered = altered.crop((0, 0, altered.width, regions["totals_start"] - 8))
        unknown = [
            "subtotal_cents",
            "discount_cents",
            "tax_cents",
            "fees_cents",
            "total_cents",
            "tax_included",
        ]
    elif transform in {"missing_date", "missing_item_name"}:
        bounds = regions["date" if transform == "missing_date" else "first_item_name"]
        left, top, right, bottom = bounds
        ImageDraw.Draw(altered).rectangle(
            (left - 3, top - 3, right + 3, bottom + 3), fill="white"
        )
        unknown = (
            ["purchased_at"]
            if transform == "missing_date"
            else ["items.0.raw_name", "items.0.normalized_name"]
        )
    else:
        raise ValueError(transform)
    return altered, unknown


def build_artifacts():
    for package, expected in REQUIRED_VERSIONS.items():
        actual = importlib.metadata.version(package)
        if actual != expected:
            raise RuntimeError(
                f"Install evaluations/fixtures/requirements.txt: {package} is {actual}, expected {expected}"
            )
    definitions = load_definitions()
    records, metadata = records_from_definitions(definitions)
    artifacts, documents, images, regions = {}, [], {}, {}

    def add_document(
        document_id,
        record_id,
        data,
        extension,
        cohort,
        transform="original",
        upload="accept",
        extraction="needs_review",
        unknown=None,
        name=None,
        instructions=False,
    ):
        meta = metadata[record_id]
        path = name or f"{cohort}/{document_id}.{extension}"
        if path in artifacts:
            raise ValueError(f"Repeated output path: {path}")
        artifacts[path] = data
        mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "pdf": "application/pdf",
        }[extension]
        documents.append(
            {
                "id": document_id,
                "path": path,
                "cohort": cohort,
                "source_record_id": record_id,
                "layout_id": meta["layout"]["id"],
                "leakage_group": meta["layout"]["id"],
                "split": meta["layout"]["split"],
                "transform": transform,
                "content_type": mime,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "expected": {
                    "upload": upload,
                    "extraction": extraction,
                    "unknown_fields": unknown or [],
                    "ignore_document_instructions": instructions,
                    "requires_human_confirmation": upload == "accept",
                },
            }
        )

    for record_id, meta in metadata.items():
        images[record_id], regions[record_id] = render_receipt(
            records[record_id], meta["layout"], record_id
        )
        extension = (
            "jpg" if meta["slot"] == 2 else "pdf" if meta["slot"] == 3 else "png"
        )
        data = (
            image_pdf(images[record_id])
            if extension == "pdf"
            else image_bytes(images[record_id], extension)
        )
        add_document(record_id, record_id, data, extension, "clear")

    development = [
        key
        for key, meta in metadata.items()
        if meta["layout"]["split"] == "development"
    ][:10]
    held_out = [
        key for key, meta in metadata.items() if meta["layout"]["split"] == "held_out"
    ][:10]
    transforms = [
        "rotated",
        "blurred",
        "cropped_totals",
        "missing_date",
        "missing_item_name",
    ]
    for index, record_id in enumerate(development + held_out):
        transform = transforms[index % len(transforms)]
        altered, unknown = corrupt_or_change(
            images[record_id], regions[record_id], transform
        )
        add_document(
            f"CH{index + 1:02d}",
            record_id,
            image_bytes(altered),
            "png",
            "challenging",
            transform,
            unknown=unknown,
        )

    for index, instruction in enumerate(definitions["adversarial_instructions"]):
        parent = development[index] if index < 4 else held_out[index - 4]
        altered, _ = render_receipt(
            records[parent],
            metadata[parent]["layout"],
            f"ADV{index + 1:02d}",
            footer_note=instruction,
        )
        add_document(
            f"ADV{index + 1:02d}",
            parent,
            image_bytes(altered),
            "png",
            "adversarial",
            "instruction_text",
            instructions=True,
        )

    unsupported = [
        ("ADV09", "UNSUPPORTED_EUR", "P1", {"currency": "EUR"}, "unsupported_currency"),
        (
            "ADV10",
            "UNSUPPORTED_CAD",
            held_out[0],
            {"currency": "CAD"},
            "unsupported_currency",
        ),
        (
            "ADV11",
            "UNSUPPORTED_REFUND",
            "P1",
            {"subtotal_cents": -1057, "total_cents": -1057},
            "unsupported_refund",
        ),
        ("ADV12", "BAD1", "P1", {"total_cents": 2000}, "total_mismatch"),
    ]
    for document_id, record_id, parent, changes, transform in unsupported:
        record = {**copy.deepcopy(records[parent]), **changes}
        if transform == "unsupported_refund":
            for item in record["items"]:
                item["line_total_cents"] = -item["line_total_cents"]
        records[record_id], metadata[record_id] = record, metadata[parent]
        rendered, _ = render_receipt(record, metadata[parent]["layout"], document_id)
        add_document(
            document_id,
            record_id,
            image_bytes(rendered),
            "png",
            "adversarial",
            transform,
            extraction="needs_correction"
            if transform == "total_mismatch"
            else "unsupported",
        )

    pdf = image_pdf(images["P1"])
    invalid = [
        ("ADV13", image_bytes(images["P1"], "gif"), "gif", "unsupported_image_type"),
        (
            "ADV14",
            b"SYNTHETIC TEST INPUT: plain text pretending to be PNG.\n",
            "png",
            "forged_mime",
        ),
        ("ADV15", b"", "png", "empty_file"),
        (
            "ADV16",
            b"%PDF-1.7\nSYNTHETIC TEST INPUT: missing PDF objects.\n",
            "pdf",
            "malformed_pdf",
        ),
        ("ADV17", encrypted_pdf(pdf), "pdf", "encrypted_pdf"),
        ("ADV18", image_pdf(images["P1"], action=True), "pdf", "internal_pdf_action"),
        ("ADV19", image_pdf(images["P1"], pages=6), "pdf", "six_page_pdf"),
        ("ADV20", image_bytes(images["P1"])[:64], "png", "truncated_image"),
    ]
    for document_id, data, extension, reason in invalid:
        add_document(
            document_id,
            "P1",
            data,
            extension,
            "adversarial",
            reason,
            upload="reject",
            extraction="not_applicable",
        )

    add_document(
        "DUP1_EXACT",
        "P1",
        artifacts["clear/P1.png"],
        "png",
        "supplemental",
        "exact_copy",
        name="supplemental/DUP1_exact.png",
    )
    duplicate, _ = render_receipt(
        records["Q1"],
        metadata["Q1"]["layout"],
        "DUP1_PHOTO",
        footer_note="Synthetic paper counterpart of the Q1 digital sale.",
    )
    add_document(
        "DUP1_PHOTO",
        "Q1",
        image_bytes(duplicate),
        "png",
        "supplemental",
        "cross_source_duplicate",
        name="supplemental/DUP1_photo.png",
    )
    add_document(
        "P1_JPG",
        "P1",
        image_bytes(images["P1"], "jpg"),
        "jpg",
        "supplemental",
        "format_variant",
    )
    add_document("P1_PDF", "P1", pdf, "pdf", "supplemental", "format_variant")
    add_document(
        "P1_PDF5",
        "P1",
        image_pdf(images["P1"], pages=5),
        "pdf",
        "supplemental",
        "five_page_pdf",
    )

    # A preview of the PDF pixel content, so reviewers need not open adversarial PDFs.
    artifacts["previews/P1.png"] = image_bytes(images["P1"])
    artifacts["previews/layouts.png"] = image_bytes(contact_sheet(images, metadata))
    expected = {
        "dataset_version": definitions["dataset_version"],
        "synthetic": True,
        "reference_date": definitions["reference_date"],
        "records": records,
        "record_metadata": {
            key: {
                "owner": meta["owner"],
                "source_type": meta["source_type"],
                "layout_id": meta["layout"]["id"],
            }
            for key, meta in metadata.items()
        },
    }
    artifacts["expected/receipts.json"] = json_bytes(expected)
    extraction_labels = {}
    for document in documents:
        fields = copy.deepcopy(records[document["source_record_id"]])
        fields.pop("notes")
        for field in document["expected"]["unknown_fields"]:
            parts = field.split(".")
            current = fields
            for part in parts[:-1]:
                current = (
                    current[int(part)] if isinstance(current, list) else current[part]
                )
            current[parts[-1]] = None
        extraction_labels[document["id"]] = {
            "expected_outcome": document["expected"]["extraction"],
            "fields": fields if document["expected"]["upload"] == "accept" else None,
            "required_uncertainties": document["expected"]["unknown_fields"],
            "ignore_document_instructions": document["expected"][
                "ignore_document_instructions"
            ],
        }
    artifacts["expected/extraction.json"] = json_bytes(extraction_labels)
    manifest = {
        "dataset_version": definitions["dataset_version"],
        "synthetic": True,
        "reference_date": definitions["reference_date"],
        "purpose": "Deterministic synthetic bootstrap data; no extraction or retrieval scores measured.",
        "renderer_versions": REQUIRED_VERSIONS,
        "definitions_sha256": hashlib.sha256(
            (HERE / "definitions.json").read_bytes()
        ).hexdigest(),
        "scenarios_sha256": hashlib.sha256(
            (HERE / "scenarios.json").read_bytes()
        ).hexdigest(),
        "documents": documents,
        "artifact_hashes": {
            path: hashlib.sha256(data).hexdigest()
            for path, data in sorted(artifacts.items())
        },
    }
    artifacts["manifest.json"] = json_bytes(manifest)
    return artifacts


def contact_sheet(images, metadata):
    selected = [
        key for key, meta in metadata.items() if meta["slot"] == 1 and key in images
    ]
    sheet = Image.new("RGB", (1440, 1800), "#e8e8e8")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for index, key in enumerate(selected):
        thumbnail = images[key].copy()
        thumbnail.thumbnail((315, 520))
        x, y = (index % 4) * 360 + 22, (index // 4) * 600 + 15
        draw.text(
            (x, y), f"{metadata[key]['layout']['id']} / {key}", font=font, fill="black"
        )
        sheet.paste(thumbnail, (x, y + 35))
    return sheet


def materialize_boundaries(output):
    output.mkdir(parents=True, exist_ok=True)
    base = image_bytes(Image.new("RGB", (200, 200), "white"))
    # A valid ancillary PNG chunk before IEND gives an exact byte length without
    # a huge decoded image. Binary zero padding is not compressed receipt content.
    for target, name in [
        (10_485_760, "SIZE_AT_LIMIT.png"),
        (10_485_761, "SIZE_OVER_LIMIT.png"),
    ]:
        padding = b"\0" * (target - len(base) - 12)
        kind = b"raNd"
        chunk = (
            struct.pack(">I", len(padding))
            + kind
            + padding
            + struct.pack(">I", zlib.crc32(kind + padding) & 0xFFFFFFFF)
        )
        (output / name).write_bytes(base[:-12] + chunk + base[-12:])
    large = Image.new("RGB", (5001, 4000), "white")
    ImageDraw.Draw(large).text(
        (30, 30),
        "SYNTHETIC OVERSIZED IMAGE",
        fill="black",
        font=ImageFont.load_default(size=40),
    )
    (output / "PIXELS_OVER_LIMIT.png").write_bytes(image_bytes(large))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare generated bytes with committed files; never write",
    )
    parser.add_argument(
        "--boundaries",
        action="store_true",
        help="Write large size/pixel cases under ignored .runtime/fixture-boundaries",
    )
    args = parser.parse_args()
    if args.check and args.boundaries:
        parser.error("Choose --check or --boundaries")
    if args.boundaries:
        print(
            f"Wrote boundary fixtures to {materialize_boundaries(HERE.parents[1] / '.runtime' / 'fixture-boundaries')}"
        )
        return
    artifacts = build_artifacts()
    if args.check:
        differences = [
            name
            for name, data in artifacts.items()
            if not (VERSION_DIR / name).is_file()
            or (VERSION_DIR / name).read_bytes() != data
        ]
        extra = sorted(
            {
                p.relative_to(VERSION_DIR).as_posix()
                for p in VERSION_DIR.rglob("*")
                if p.is_file()
            }
            - artifacts.keys()
        )
        if differences or extra:
            raise SystemExit(
                f"Fixture mismatch. Changed/missing: {differences}; unexpected: {extra}"
            )
        print(f"PASS: all {len(artifacts)} artifacts reproduce byte-for-byte.")
        return
    for name, data in artifacts.items():
        destination = VERSION_DIR / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    print(f"Wrote {len(artifacts)} artifacts under {VERSION_DIR}; no files deleted.")


if __name__ == "__main__":
    main()
