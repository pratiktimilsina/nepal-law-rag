import os
os.environ["TESSDATA_PREFIX"] = r"C:\projects\nepal-law-rag\tessdata"

import pymupdf
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

doc = pymupdf.open("data/raw/constitution_ne.pdf")
out = open("data/ocr_test.txt", "w", encoding="utf-8")
for psm in [3, 4, 6]:
    for i in [2, 61]:
        page = doc[i]
        r = page.rect
        clip = pymupdf.Rect(r.x0, r.y0 + 50, r.x1, r.y1 - 50)  # crop header/footer
        pix = page.get_pixmap(dpi=300, clip=clip)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="nep", config=f"--psm {psm}")
        out.write(f"===== psm {psm} | page {i} =====\n{text}\n")
out.close()
print("done")
