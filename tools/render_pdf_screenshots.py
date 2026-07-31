from __future__ import annotations

import subprocess
import shutil
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "portfolio_screenshots" / "pdf_pages"
TMP = Path(r"C:\Users\Public\Documents\ESTsoft\CreatorTemp\portfolio_pdf_render")
PDFTOPPM = Path(
    r"C:\Users\scinn\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)


def render_pdf(pdf: Path, max_pages: int = 4) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    ascii_stem = "pdf_" + hashlib.sha1(str(pdf).encode("utf-8")).hexdigest()[:10]
    temp_pdf = TMP / f"{ascii_stem}.pdf"
    shutil.copyfile(pdf, temp_pdf)
    prefix = TMP / ascii_stem
    subprocess.run(
        [
            str(PDFTOPPM),
            "-png",
            "-r",
            "140",
            "-f",
            "1",
            "-l",
            str(max_pages),
            str(temp_pdf),
            str(prefix),
        ],
        cwd=str(ROOT),
        check=True,
    )
    rendered = []
    for temp_page in sorted(TMP.glob(f"{ascii_stem}-*.png")):
        destination = OUT / temp_page.name
        shutil.copyfile(temp_page, destination)
        rendered.append(destination)
    return rendered


def make_sheet(paths: list[Path]) -> Path | None:
    if not paths:
        return None

    thumb_w, thumb_h = 480, 270
    label_h = 46
    gap = 18
    cols = 2
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new(
        "RGB",
        (cols * thumb_w + (cols + 1) * gap, rows * (thumb_h + label_h) + (rows + 1) * gap),
        "#f5f5f5",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for idx, path in enumerate(paths):
        row, col = divmod(idx, cols)
        x = gap + col * (thumb_w + gap)
        y = gap + row * (thumb_h + label_h + gap)
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            bg = Image.new("RGB", (thumb_w, thumb_h), "white")
            bg.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
            sheet.paste(bg, (x, y))
        draw.text((x, y + thumb_h + 8), f"{idx + 1}. {path.name}", fill="#111111", font=font)

    output = OUT.parent / "pdf_contact_sheet.png"
    sheet.save(output)
    return output


if __name__ == "__main__":
    all_pages: list[Path] = []
    for pdf in sorted(ROOT.glob("*.pdf")):
        all_pages.extend(render_pdf(pdf))
    sheet = make_sheet(all_pages[:8])
    print(f"rendered_pages={len(all_pages)}")
    if sheet:
        print(f"contact_sheet={sheet}")
    for page in all_pages:
        print(page)
