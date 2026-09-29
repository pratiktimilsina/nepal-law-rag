import os, json
os.environ["TESSDATA_PREFIX"] = r"C:\projects\nepal-law-rag\tessdata"

import pymupdf
import pytesseract
from PIL import Image
from tqdm import tqdm

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
SRC = "data/raw/constitution_ne.pdf"
OUT = "data/processed/ne_pages.jsonl"

done = set()
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        for line in f:
            done.add(json.loads(line)["page"])

doc = pymupdf.open(SRC)
with open(OUT, "a", encoding="utf-8") as out:
    for i in tqdm(range(len(doc))):
        if i in done:
            continue
        page = doc[i]
        r = page.rect
        clip = pymupdf.Rect(r.x0, r.y0 + 50, r.x1, r.y1 - 50)
        pix = page.get_pixmap(dpi=300, clip=clip)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr = pytesseract.image_to_string(img, lang="nep", config="--psm 6")
        layer = page.get_text(clip=clip)
        out.write(json.dumps({"page": i, "ocr": ocr, "layer": layer}, ensure_ascii=False) + "\n")
        out.flush()
print("done")
