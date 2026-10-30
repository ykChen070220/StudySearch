"""从自编文本生成示例 PDF，无需下载字体或教材。"""
import json
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parent

def build():
    lessons = json.loads((ROOT / "samples/lessons.json").read_text(encoding="utf-8"))
    doc = pymupdf.open()
    for number, lesson in enumerate(lessons, 1):
        page = doc.new_page(width=595, height=842)
        page.draw_rect(pymupdf.Rect(0, 0, 595, 12), color=None, fill=(0.15, 0.35, 0.85))
        page.insert_text((48, 55), "StudySearch / DEMO NOTES", fontsize=12, color=(0.2, 0.3, 0.5))
        page.insert_text((48, 115), lesson["title"], fontname="china-s", fontsize=23)
        result = page.insert_textbox(pymupdf.Rect(48, 165, 547, 660), lesson["text"],
                                    fontname="china-s", fontsize=14, lineheight=1.9)
        if result < 0:
            raise RuntimeError("正文溢出")
        page.insert_text((48, 735), "自编演示资料，仅用于项目功能和检索实验，不替代正式教材。", fontname="china-s", fontsize=10)
        page.insert_text((48, 775), f"StudySearch | {number:02d} / {len(lessons)}", fontsize=10)
    doc.save(ROOT / "samples/study_notes.pdf")
    doc.close()

if __name__ == "__main__":
    build()
