"""Approximate PIL render of a python-pptx deck (no LibreOffice on this host).
Draws autoshape fills, pictures, text boxes (wrapped) and tables at 50 px/inch."""
import sys, io
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
PPI = 50
FONT_REG = "/usr/share/fonts/dejavu/DejaVuSans.ttf"; FONT_BOLD = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
def font(pt, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, max(6, int(pt / 72 * PPI * 0.92)))

prs = Presentation(SRC); s = prs.slides[0]
Wp, Hp = int(Emu(prs.slide_width).inches * PPI), int(Emu(prs.slide_height).inches * PPI)
im = Image.new("RGB", (Wp, Hp), "white"); d = ImageDraw.Draw(im)
px = lambda e: int(Emu(e).inches * PPI)
def rgb(c):
    try: return "#" + str(c.rgb)
    except Exception: return None

def draw_text_frame(tf, x, y, w, h):
    cy = y + 4
    for p in tf.paragraphs:
        runs = [(r.text, r.font) for r in p.runs]
        if not runs: cy += 10; continue
        size = next((r.font.size.pt for _, r in [(0, type("o", (), {"font": f})) for _, f in runs] if r.font.size), 14)
        # simple word wrap over concatenated runs (per-run style approximated by first run bold/color)
        words = []
        for t, f in runs:
            col = rgb(f.color) if f.color and f.color.type is not None else "#444444"
            for wd in t.split(" "): words.append((wd, f.bold, col, f.size.pt if f.size else size))
        line, lw = [], 0; maxw = w - 14
        def flush(line, cy):
            cx = x + 7
            if p.alignment == 2:   # center
                tot = sum(d.textlength(wd + " ", font=font(sz, b)) for wd, b, c, sz in line); cx = x + (w - tot) / 2
            for wd, b, c, sz in line:
                f = font(sz, b); d.text((cx, cy), wd, fill=c or "#444444", font=f); cx += d.textlength(wd + " ", font=f)
            return cy + int(max(sz for _, _, _, sz in line) / 72 * PPI * 1.15)
        for wd, b, c, sz in words:
            ww = d.textlength(wd + " ", font=font(sz, b))
            if lw + ww > maxw and line: cy = flush(line, cy); line, lw = [], 0
            line.append((wd, b, c, sz)); lw += ww
        if line: cy = flush(line, cy)
        cy += 3
    if cy > y + h + 6: d.rectangle([x, y, x + w, y + h], outline="red", width=3)  # overflow marker

for sh in s.shapes:
    x, y, w, h = px(sh.left), px(sh.top), max(1, px(sh.width)), max(1, px(sh.height))
    if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
        pim = Image.open(io.BytesIO(sh.image.blob)).convert("RGBA").resize((max(1, w), max(1, h)))
        bg = Image.new("RGBA", pim.size, (255, 255, 255, 255)); bg.alpha_composite(pim); im.paste(bg.convert("RGB"), (x, y))
    elif sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
        fill = rgb(sh.fill.fore_color) if sh.fill.type == 1 else None
        outline = None
        try:
            if sh.line.fill.type == 1: outline = "#" + str(sh.line.color.rgb)
        except Exception: pass
        if fill or outline: d.rounded_rectangle([x, y, x + w, y + h], radius=int(min(w, h) * 0.03), fill=fill, outline=outline, width=3 if outline else 0)
        if sh.has_text_frame and sh.text_frame.text.strip(): draw_text_frame(sh.text_frame, x, y, w, h)
    elif sh.shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
        draw_text_frame(sh.text_frame, x, y, w, h)
    elif sh.has_table:
        t = sh.table; cx = x
        colw = [px(c.width) for c in t.columns]; rowh = h // len(t.rows)
        for i, row in enumerate(t.rows):
            cx = x
            for j, cell in enumerate(row.cells):
                fill = "#1F3A5F" if i == 0 else ("#EAEEF4" if i % 2 == 0 else "white")
                d.rectangle([cx, y + i * rowh, cx + colw[j], y + (i + 1) * rowh], fill=fill, outline="#CCCCCC")
                r = cell.text_frame.paragraphs[0].runs
                if r:
                    f = font(r[0].font.size.pt if r[0].font.size else 14, bool(r[0].font.bold))
                    col = "white" if i == 0 else "#333333"
                    tw = d.textlength(r[0].text, font=f)
                    tx = cx + (colw[j] - tw) / 2 if j else cx + 6
                    d.text((tx, y + i * rowh + rowh * 0.25), r[0].text, fill=col, font=f)
                cx += colw[j]
im.save(OUT); print("preview", OUT, im.size)
