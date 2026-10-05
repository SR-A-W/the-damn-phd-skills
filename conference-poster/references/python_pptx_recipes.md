# python-pptx 增量编辑配方(在人类手改的 pptx 上操作)

定位元素:按 `shape.name`(dump 一次清单)或 `shape.text_frame.text` 关键字;表格 `shape.has_table`。

- **改字号**:遍历 `paragraphs → runs`,只改 `run.font.size` 在目标区间的 run(避开 44 pt 标题、20 pt 图注)。
- **拆 run 上色**(如 /think 蓝、/no_think 绿):`re.split` 命中 run 的文本,`copy.deepcopy(run._r)` 插到原 run 之后,逐段设颜色;表格单元格同样处理。
- **重写一段 bullets**:删除第 2+ 段、清空第 1 段 runs,重建 label(bold)+ body 两个 run;项目符号写 XML:`pPr.marL/indent` + `<a:buChar char="•"/>`(先移除 buNone/buChar/buAutoNum)。
- **文字阴影**:在 `a:rPr` 下插 `<a:effectLst><a:outerShdw blurRad dist dir algn="tl"><a:srgbClr val="000000"><a:alpha val="30000"/></a:srgbClr></a:outerShdw></a:effectLst>`;**必须放在 `a:latin/a:ea/a:cs/a:sym` 之前**(schema 顺序),否则校验失败。
- **表格纵向居中**:`cell.vertical_anchor = MSO_ANCHOR.MIDDLE`;合并表头 `cell(0,j).merge(cell(0,j+1))`。
- **替换/新增图片**:`add_picture(path_or_BytesIO, left, top, width, height)`;复制已有图:`shape.image.blob` → BytesIO。
- **按高度/宽度等比缩放**:先算 `ratio = width/height`,再设另一维。
- **删除元素**:`el = shape._element; el.getparent().remove(el)`。
- **面板边框/底色**:`shape.line.color.rgb / line.width`;`fill.solid()`;图面板 `fill WHITE`。
- 读取人类改动:先 dump(name / 位置 / 字号 / 文本首 70 字),再决定定位键;人类可能把一个框拆成多个(如三个 callout),脚本要容忍。

渲染预览:`python scripts/preview_poster.py deck.pptx out.png`(50 px/in;画形状填充+边框、图片(alpha 合成)、文本换行、表格;文本溢出画红框;**不画项目符号与阴影**,这两项靠 XML 自检)。
