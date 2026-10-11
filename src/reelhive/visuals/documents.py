"""PDFs and slide decks as sources: page text for `research`, page images for scenes.

Pages are rendered once into the run folder (`documents/`) and reused on resume. Decks are converted to
PDF with LibreOffice when it is installed; nothing leaves the machine here.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

DECKS = {".pptx", ".ppt", ".odp"}
SUFFIXES = {".pdf", *DECKS}
MAX_PAGES = 30  # per document
SHORT_SIDE = 1280  # every format's minimum in resolver.MINIMUM_SIZE fits inside this


def office() -> str | None:
    mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return shutil.which("soffice") or shutil.which("libreoffice") or (str(mac) if mac.exists() else None)


def to_pdf(source: Path, out_dir: Path) -> Path:
    if source.suffix.lower() == ".pdf":
        return source
    pdf = out_dir / f"{source.stem}.pdf"
    if not pdf.exists():
        binary = office()
        if not binary:
            raise ValueError(f"{source.name}: install LibreOffice to read slide decks, or export the deck as PDF")
        subprocess.run(
            [binary, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(source)],
            check=True,
            capture_output=True,
            timeout=180,
        )
    return pdf


def pages(paths: list[str], out_dir: Path) -> list[dict[str, str]]:
    """One entry per page: `image`/`file`/`caption` like a provided image, plus the page `text`."""
    import pypdfium2 as pdfium

    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for number, name in enumerate(paths, 1):
        source = Path(name)
        if source.suffix.lower() not in SUFFIXES or not source.is_file():
            raise ValueError(f"not a PDF or slide deck: {source}")
        slug = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40] or "document"
        pdf = pdfium.PdfDocument(to_pdf(source, out_dir))
        try:
            for index in range(min(len(pdf), MAX_PAGES)):
                page = pdf[index]
                text = page.get_textpage().get_text_bounded().strip()
                file = out_dir / f"doc{number}-{slug}-p{index + 1:02d}.png"
                if not file.exists():
                    width, height = page.get_size()
                    page.render(scale=SHORT_SIDE / min(width, height)).to_pil().convert("RGB").save(file)
                result.append(
                    {
                        "image": file.name,
                        "file": str(file),
                        "caption": " ".join(text.split())[:200],
                        "text": text,
                        "document": source.name,
                        "page": str(index + 1),
                    }
                )
        finally:
            pdf.close()
    return result
