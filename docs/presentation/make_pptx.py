"""Make deck.pptx from layout.json, so that the slides can be changed in PowerPoint, Google Slides or Canva.

Each text is a text box with the fonts of the HTML slides. Each box is a shape and each image is a picture.
The line breaks are the same as in the HTML slides, because the text boxes do not wrap the text.

To make the file, do these steps in this folder:
  1. Run "node build.js". It writes layout.json.
  2. Run "uv run --no-project --with python-pptx python make_pptx.py".
"""

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
EMU = 6350  # one CSS pixel: the slide is 1920 px and 13.333 inches wide
PT = 0.5  # one CSS pixel in points
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}


def emu(v: float) -> Emu:
    return Emu(round(v * EMU))


def rgb(c: dict) -> RGBColor:
    return RGBColor(round(c["r"]), round(c["g"]), round(c["b"]))


def set_alpha(color_parent, a: float) -> None:
    if a < 1:
        clr = color_parent.find(qn("a:srgbClr"))
        etree.SubElement(clr, qn("a:alpha")).set("val", str(round(a * 100000)))


def add_rect(slide, it: dict) -> None:
    w, h, r = it["w"], it["h"], it.get("r", 0)
    if w <= 0 or h <= 0:
        return
    if r >= min(w, h) / 2 - 0.5 and abs(w - h) < 1:
        kind = MSO_SHAPE.OVAL
    elif r > 0.5:
        kind = MSO_SHAPE.ROUNDED_RECTANGLE
    else:
        kind = MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(kind, emu(it["x"]), emu(it["y"]), emu(w), emu(h))
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = min(r / min(w, h), 0.5)
    sh.shadow.inherit = False
    if it.get("fill"):
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(it["fill"])
        set_alpha(sh.fill._xPr.find(qn("a:solidFill")), it["fill"]["a"])
    else:
        sh.fill.background()
    line = it.get("line")
    if line:
        sh.line.width = emu(line["w"])
        sh.line.color.rgb = rgb(line["c"])
    else:
        sh.line.fill.background()
    sh.rotation = it.get("rot", 0)
    # A shape without text must not show the default text style of the theme.
    sh.text_frame.text = ""


def add_image(slide, it: dict) -> None:
    path = unquote(urlparse(it["src"]).path)
    pic = slide.shapes.add_picture(path, emu(it["x"]), emu(it["y"]), emu(it["w"]), emu(it["h"]))
    c = it["crop"]
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = c["l"], c["t"], c["r"], c["b"]
    if it["oval"]:
        pic.auto_shape_type = MSO_SHAPE.OVAL
    pic.rotation = it.get("rot", 0)


def add_text(slide, it: dict) -> None:
    tb = slide.shapes.add_textbox(emu(it["x"]), emu(it["y"]), emu(it["w"]), emu(it["h"]))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = ALIGN[it["align"]]
    p.line_spacing = Pt(it["lh"] * PT)
    p.space_before = p.space_after = Pt(0)
    for run in it["runs"]:
        if run.get("br"):
            p.add_line_break()
            continue
        st = run["st"]
        r = p.add_run()
        r.text = run["t"]
        f = r.font
        f.name = st["font"]
        f.size = Pt(st["size"] * PT)
        f.bold = st["weight"] >= 600
        f.italic = st["italic"]
        if st["color"]:
            f.color.rgb = rgb(st["color"])
        if st["ls"]:
            r._r.get_or_add_rPr().set("spc", str(round(st["ls"] * PT * 100)))
        if st["href"] and st["href"].startswith("http"):
            r.hyperlink.address = st["href"]
    tb.rotation = it.get("rot", 0)


def main() -> None:
    layout = json.loads((HERE / "layout.json").read_text(encoding="utf-8"))
    prs = Presentation()
    prs.slide_width, prs.slide_height = emu(1920), emu(1080)
    for items in layout:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        for it in items:
            {"rect": add_rect, "img": add_image, "text": add_text}[it["type"]](slide, it)
    prs.save(HERE / "deck.pptx")
    print(f"deck.pptx: {len(layout)} slides")


if __name__ == "__main__":
    main()
