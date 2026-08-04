from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "portfolio_screenshots"
DATA_URI_RE = re.compile(r"data:image/(?P<kind>png|jpeg);base64,(?P<data>[A-Za-z0-9+/=\s]+)")


def as_text(value: object) -> str:
    if isinstance(value, list):
        return "".join(str(part) for part in value)
    return "" if value is None else str(value)


def decode_image_payload(payload: object) -> bytes:
    data = as_text(payload)
    return base64.b64decode("".join(data.split()))


def safe_name(text: str) -> str:
    keep = []
    for ch in text:
        keep.append(ch if ch.isalnum() or ch in "._-[]" else "_")
    return "".join(keep).strip("_") or "notebook"


def extract() -> list[dict[str, object]]:
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []

    for notebook in sorted(ROOT.glob("*.ipynb")):
        with notebook.open("r", encoding="utf-8") as handle:
            nb = json.load(handle)

        for cell_index, cell in enumerate(nb.get("cells", []), start=1):
            source = as_text(cell.get("source", "")).strip().splitlines()
            title = next((line.strip("# ").strip() for line in source if line.strip()), "")

            for output_index, output in enumerate(cell.get("outputs", []), start=1):
                data = output.get("data", {})
                images: list[tuple[str, bytes]] = []

                if "image/png" in data:
                    images.append(("png", decode_image_payload(data["image/png"])))
                if "image/jpeg" in data:
                    images.append(("jpg", decode_image_payload(data["image/jpeg"])))

                html = as_text(data.get("text/html", ""))
                for match in DATA_URI_RE.finditer(html):
                    ext = "jpg" if match.group("kind") == "jpeg" else "png"
                    images.append((ext, decode_image_payload(match.group("data"))))

                for image_index, (ext, blob) in enumerate(images, start=1):
                    name = (
                        f"{safe_name(notebook.stem)}"
                        f"_cell{cell_index:03d}_out{output_index:02d}_{image_index}.{ext}"
                    )
                    path = OUT / name
                    path.write_bytes(blob)
                    with Image.open(path) as img:
                        width, height = img.size
                    records.append(
                        {
                            "file": str(path),
                            "notebook": notebook.name,
                            "cell": cell_index,
                            "output": output_index,
                            "title": title,
                            "width": width,
                            "height": height,
                            "bytes": len(blob),
                        }
                    )

    summary = OUT / "notebook_output_images.json"
    summary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def make_contact_sheet(records: list[dict[str, object]]) -> Path | None:
    if not records:
        return None

    ranked = sorted(
        records,
        key=lambda item: int(item["width"]) * int(item["height"]),
        reverse=True,
    )[:12]

    thumb_w, thumb_h = 420, 260
    label_h = 72
    gap = 18
    cols = 2
    rows = (len(ranked) + cols - 1) // cols
    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = rows * (thumb_h + label_h) + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#f5f5f5")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for idx, item in enumerate(ranked):
        row, col = divmod(idx, cols)
        x = gap + col * (thumb_w + gap)
        y = gap + row * (thumb_h + label_h + gap)
        with Image.open(str(item["file"])) as img:
            img = img.convert("RGB")
            img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            bg = Image.new("RGB", (thumb_w, thumb_h), "white")
            bg.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
            sheet.paste(bg, (x, y))

        label = f"{idx + 1}. {Path(str(item['file'])).name}"
        detail = f"{item['notebook']} | cell {item['cell']} | {item['width']}x{item['height']}"
        draw.text((x, y + thumb_h + 8), label[:68], fill="#111111", font=font)
        draw.text((x, y + thumb_h + 30), detail[:68], fill="#555555", font=font)

    output = OUT / "contact_sheet.png"
    sheet.save(output)
    return output


if __name__ == "__main__":
    found = extract()
    sheet = make_contact_sheet(found)
    print(f"extracted={len(found)}")
    if sheet:
        print(f"contact_sheet={sheet}")
    for record in sorted(found, key=lambda item: int(item["width"]) * int(item["height"]), reverse=True)[:20]:
        print(
            f"{Path(str(record['file'])).name}\t"
            f"{record['width']}x{record['height']}\t"
            f"{record['notebook']}\tcell {record['cell']}\t{record['title']}"
        )
