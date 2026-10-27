import hashlib

import pymupdf  # reads PDF files
from PIL import Image, ImageStat

MAX_SIZE = 1500
RESIZED_PATH = "receipts/_resized.jpg"
PDF_DPI = 200          # how sharp PDF pages are rendered (dots per inch)
MAX_PDF_PAGES = 5      # long receipts can span pages; more than this is probably not a receipt


def pdf_to_image(pdf_path):
    """Render every page of a PDF and stack them vertically into one tall image."""
    doc = pymupdf.open(pdf_path)
    try:
        pages = []
        for page in list(doc)[:MAX_PDF_PAGES]:
            pixmap = page.get_pixmap(dpi=PDF_DPI)
            pages.append(Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples))
    finally:
        doc.close()

    width = max(page.width for page in pages)
    height = sum(page.height for page in pages)
    combined = Image.new("RGB", (width, height), "white")
    top = 0
    for page in pages:
        combined.paste(page, (0, top))
        top += page.height
    return combined


def load_image(path):
    """Open an image file or a PDF, always returning an RGB image."""
    if str(path).lower().endswith(".pdf"):
        return pdf_to_image(path)
    return Image.open(path).convert("RGB")


def prepare_image(image_path):
    """Shrink the image, save a copy for the AI, and measure its contrast."""
    image = load_image(image_path)
    image.thumbnail((MAX_SIZE, MAX_SIZE))
    image.save(RESIZED_PATH)
    contrast = ImageStat.Stat(image.convert("L")).stddev[0]
    return RESIZED_PATH, contrast


def file_hash(image_path):
    """Fingerprint of the file: identical files give identical hashes."""
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()