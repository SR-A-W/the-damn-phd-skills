# 生图 prompt 模板(版式定稿 + 项目 logo)

## 1. 海报效果图(交人去 ChatGPT/其他生图工具)
骨架(按论文填空,英文):
```
A clean, understated academic poster for <CONFERENCE YEAR>, <landscape|portrait>, aspect ratio <W:H>
(<W × H in>), white background, sans-serif type, generous whitespace, calm academic tone —
NOT a marketing poster; no oversized numbers; callouts in body-text size.

Header band: title "<TITLE>"; one line of authors; affiliation logos (<LIST>); small "<CONF>" tag;
QR codes labeled "<arXiv>" and "<Code>" placed <bottom-right|header>.

Row 1 (≈45% height), three panels <narrow|wide|narrow>:
- Left "<Abstract / Motivation>": <2–3 sentences> + <Fig 1 description>.
- Center "<METHOD NAME>": place the attached architecture figure AS-IS at its natural aspect ratio
  (~<r>:1), one-sentence caption: "<...>".
- Right "<Motivation / In a nutshell>": <table or bullets>.

Row 2, three equal panels:
- "Main results": <N> grouped bar charts (<metrics>) for <baselines vs ours>, <color scheme>;
  one bold body-size summary line: "<headline numbers>".
- "Ablations": <two small charts> + <2 findings>.
- "Generalization & Takeaways": <small table> + <3 bullets>; closing sentence in regular weight.

Palette: white, <primary hex>, <secondary hex>, <accent only for highlights>, light gray panels.
Flat vector style, crisp text, no photos, no gradients, no shadows; rendered as a printed poster viewed straight on.
```
要点:
- **附上论文架构图 + 人类手绘结构草图**并写 "follow EXACTLY the attached layout sketch";否则生图会自己画一个竖版架构图。
- 人类反馈循环只修 prompt;每轮只改被批注的点,保留其他已认可的描述。
- 常见否决:架构图占比过大/方向错、提升比例字体像促销、三栏比例失衡、Logo 在左上角。

## 2. 项目 logo(可选)
原则:符号必须能**表达机制**而不只是配色;构图**对称**(两条路径从同一器件对称发出,否则一条像附件);**去掉文字标签**(/think 等);输出透明 PNG + 单色版。
骨架:
```
A minimal flat vector logo mark for "<ABBR> — <Full Name>". Transparent background. <portrait|square>;
mark width = width of the bold "<ABBR>" wordmark beneath it; "<FULL NAME>" in small spaced caps under it.
No other text. <Describe the mechanism as a physical device, e.g. a two-position toggle switch with two
identical output ports; the two outputs leave at mirror angles with identical stroke weight; only their
SHAPE differs: upper = dense serpentine meander (long deliberation), lower = one straight line (direct)>.
Uniform rounded strokes, flat colors (<hex list>), no gradients/shadows/3D/brains/robots/padlocks.
Legible at 2 cm and 20 cm. Deliver full-color and single-color versions as transparent PNG.
```
迭代经验:锁 → 像"被挡住";Y 形岔口 → 一条像附件;电路符号开关 → 第一眼不懂;**带外壳+两个端口+拨杆的拨动开关**最易读。
