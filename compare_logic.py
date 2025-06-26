import os
import cv2
import numpy as np
import pypdfium2
from PIL import Image
from datetime import datetime

# 色指定（日本語 → RGB）
COLOR_OPTIONS = {
    "赤":       (255,   0,   0),
    "オレンジ": (255, 127,   0),
    "マゼンダ": (255,   0, 255),
    "ピンク":   (255, 130, 160),
    "青":       (  0,   0, 255),
    "緑":       ( 20, 175,  60),
    "水色":     (  0, 190, 255),
    "黄緑":     (173, 255,  47),
    "黒":       (  0,   0,   0),
    "白":       (255, 255, 255),
    "グレー":   (150, 150, 150),
}

def pdf_to_images(pdf_path: str, dpi: int) -> list[np.ndarray]:
    pdf = pypdfium2.PdfDocument(pdf_path)
    return [np.array(page.render(scale=dpi/72).to_pil()) for page in pdf]

def resize_to_match(img1: np.ndarray, img2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = img1.shape[:2]
    img2r = cv2.resize(img2, (w, h), interpolation=cv2.INTER_AREA)
    return img1, img2r

def preprocess_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

def color_coded_diff(
    img_new: np.ndarray,
    img_old: np.ndarray,
    threshold: int,
    new_color: str,
    old_color: str
) -> np.ndarray:
    g_new = preprocess_gray(img_new)
    g_old = preprocess_gray(img_old)
    diff_add    = cv2.subtract(g_new, g_old)
    diff_remove = cv2.subtract(g_old, g_new)
    common      = cv2.bitwise_and(g_new, g_old)
    _, t_add    = cv2.threshold(diff_add,    threshold, 255, cv2.THRESH_BINARY)
    _, t_remove = cv2.threshold(diff_remove, threshold, 255, cv2.THRESH_BINARY)
    _, t_common = cv2.threshold(common,      threshold, 255, cv2.THRESH_BINARY)

    h, w = g_new.shape
    out = np.zeros((h, w, 3), dtype=np.uint8)
    out[t_common > 0] = (255, 255, 255)
    out[t_add    > 0] = COLOR_OPTIONS.get(new_color, (255, 0, 0))
    out[t_remove > 0] = COLOR_OPTIONS.get(old_color, (0, 0, 255))
    return out

def generate_unique(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{base}_{i}{ext}"):
        i += 1
    return f"{base}_{i}{ext}"

def compare_pdfs_with_color_coding(
    pdf1: str,
    pdf2: str,
    out_folder: str,
    dpi: int = 300,
    threshold: int = 120,
    new_color: str = "赤",
    old_color: str = "青",
    append_suffix: bool = False
) -> str:
    os.makedirs(out_folder, exist_ok=True)
    imgs1 = pdf_to_images(pdf1, dpi)
    imgs2 = pdf_to_images(pdf2, dpi)
    pages = min(len(imgs1), len(imgs2))
    results = []
    for i in range(pages):
        im_new, im_old = imgs1[i], imgs2[i]
        if im_new.shape[:2] != im_old.shape[:2]:
            im_new, im_old = resize_to_match(im_new, im_old)
        diff = color_coded_diff(im_new, im_old, threshold, new_color, old_color)
        results.append(Image.fromarray(diff))
    if not results:
        raise RuntimeError("比較対象のページがありません。")
    today = datetime.now().strftime("%y%m%d")
    filename = f"{today}_変更比較図.pdf"
    out_path = generate_unique(os.path.join(out_folder, filename))
    results[0].save(out_path, save_all=True, append_images=results[1:])
    return out_path