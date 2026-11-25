"""Builds docs/*.html and docs/*.pdf from the Markdown manuals.

Requires: markdown, pymupdf.   Usage: python tools/build_manuals.py
"""
import os

import markdown
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

CSS = """
body { font-family: sans-serif; font-size: 10pt; line-height: 1.4; color: #111; }
h1 { font-size: 20pt; color: #1d4ed8; margin-bottom: 4pt; }
h2 { font-size: 14pt; color: #1d4ed8; margin-top: 14pt; border-bottom: 1px solid #cbd5e1; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
th, td { border: 1px solid #cbd5e1; padding: 3pt 5pt; font-size: 8.5pt; vertical-align: top; }
th { background: #e2e8f0; }
code { font-family: monospace; font-size: 8.5pt; background: #f1f5f9; }
img { width: 100%; }
"""

HTML_CSS = CSS + "body { max-width: 900px; margin: 30px auto; padding: 0 20px; }"


def build(name):
    md_path = os.path.join(DOCS, name + ".md")
    with open(md_path, encoding="utf-8") as f:
        body = markdown.markdown(f.read(), extensions=["tables"])
    html = f"<html><head><meta charset='utf-8'><title>{name}</title><style>{HTML_CSS}</style></head><body>{body}</body></html>"
    with open(os.path.join(DOCS, name + ".html"), "w", encoding="utf-8") as f:
        f.write(html)

    pdf_path = os.path.join(DOCS, name + ".pdf")
    story = pymupdf.Story(html=f"<body>{body}</body>", user_css=CSS, archive=pymupdf.Archive(DOCS))
    writer = pymupdf.DocumentWriter(pdf_path)
    mediabox = pymupdf.paper_rect("a4")
    where = mediabox + (50, 50, -50, -50)
    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    print("built", pdf_path)


if __name__ == "__main__":
    for n in ("Manual_FCP_Live_Analyzer_pt-BR", "Manual_FCP_Live_Analyzer_EN"):
        build(n)
