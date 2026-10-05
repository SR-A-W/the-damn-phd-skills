---
name: conference-poster
description: 为任意学术会议论文制作海报的多阶段、可中断续作的工作流:自动获取会议海报要求与模板 → 用生图定版式(唯一必须人类参与的环节)→ python-pptx 代码生成 pptx → 按黄金标准自检返工到位后才交人审 → 人手改后以增量脚本继续。适用于 "帮我做 XX 会议的 poster"、"继续做海报"、"海报改一下 XX"。
---

# Conference Poster — 学术海报制作工作流

这不是一次性 skill。全程通常 1–2 小时、跨多轮对话甚至跨 session,因此**状态写在磁盘**:
`<paper_dir>/poster/POSTER_STATE.md`。每次调用先读它,从记录的阶段续作;没有就从 Stage 0 开始。

## 调用形态
```
/conference-poster <会议名+年份> [论文仓路径]     # 新建或续作(自动判断)
/conference-poster                             # 续作:读 POSTER_STATE.md
/conference-poster stage <0|1|2|3>             # 强制跳到某阶段
```

## 设计原则(先读)
1. **人类只在两个闸门出现**:闸门 A = 版式定稿(需要人去外部生图),闸门 B = 成品审阅。其余一切迭代——字号、溢出、留白、对齐、配色、图注/正文体——由你按 `references/golden_checklist.md` **自己检查、自己返工**,直到全部打勾才允许交人。人类说"字太小"属于你的失败,不是流程的一部分。
2. **代码是唯一事实源**:pptx 由 python-pptx 脚本生成;人类手改 pptx 之后,改为在他的文件上跑**增量编辑脚本**(永不覆盖人类改动)。
3. **本机常无渲染器**(HPC 无 LibreOffice):用 `scripts/preview_poster.py` 从 pptx 渲染近似预览(替代字体更宽,预览能放下则真机必能放下;含溢出红框);有 LibreOffice 时改用 pptx skill 的 soffice→pdf→png 路径。
4. **每轮"看渲染图再下结论"**,不盯源码脑补;发现问题改脚本重跑,而不是手补。

---

## Stage 0 — 会议要求与模板(全自动,不要让人类上传模板)
1. WebSearch/WebFetch 会议官网:FAQ / Call for Papers / 主页公告 / 往届 poster 指南。要拿到:**尺寸与方向**(主会 vs workshop 常不同)、**是否要求会议 logo 及位置**、**官方或印刷商模板下载链接**(Dropbox/PDF/pptx)、打印/物流说明、海报场次(日期、时间、房间;注意日程页**按观看者时区显示**的坑,必须换算成会议当地时间)。
2. 下载模板到 `poster/`;若模板尺寸与公布尺寸不同(例:公布 72×36 in、模板 56×28.8 in),解释原因(PowerPoint 单边 56 in 上限 → 等比印出)并记录缩放比,后续字号按缩放比折算。
3. 读模板(python-pptx):画布尺寸、占位符、母版品牌元素。
4. 写入 `POSTER_STATE.md`:要求摘要、模板路径、尺寸/缩放、场次、下一阶段。

## Stage 1 — 版式定稿(闸门 A:人类用外部工具生图)
目标:一张**人类认可的效果图**作为后续构建的目标版式。
1. 读论文(abstract、方法图、主表主图、消融、泛化),列出候选区块。
2. 按 `references/imagegen_prompts.md` 的模板写**生图 prompt**(英文,含尺寸比例、三栏/两排结构、各区块内容、配色、"calm academic, no oversized numbers" 等约束),交人去 ChatGPT 生图。**附上论文架构图和人类手绘的结构草图**能显著提高保真度——主动提议。
3. 人类回传效果图 + 批注 → 你修 prompt(不是修海报)。典型要点:架构图用论文原图且保持原宽高比;提升数字不要销售海报式大字;版式按人类草图。
4. 人类说"就用这版" → 保存为 `poster/poster_target_layout_v1.png`,写进 STATE,进入 Stage 2。
5. (可选同轨)项目 logo:同样用生图 prompt 迭代;要点见 `references/imagegen_prompts.md` 的 logo 节(符号必须能表达机制、构图对称、去掉文字标签、输出透明 PNG)。

## Stage 2 — 正式构建(全自动,自检到位才交人)
1. **资产**:论文图从 Overleaf/LaTeX 仓的 PDF 用 `pdftoppm -r 300` 栅格化;需要局部时用 PIL 按比例裁切并**肉眼核对裁切线**(x 轴标签是否被切、下一行是否露头);二维码 `qrcode` 生成;logo 全部转透明 PNG(avif → pillow-avif-plugin,svg → cairosvg),可能需要白底转透明 + 裁边。
2. **构建脚本**:以 `scripts/example_builder_ple_v5.py` 为骨架(LAYOUT 字典 + panel/text/caption/callout/table 助手 + 固定字号表)。写**单一文件**,所有尺寸来自 LAYOUT。
3. **自检循环**(核心):
   ```
   build → preview_poster.py → 读预览图 → 对照 golden_checklist 逐条判 → 改脚本 → 重复
   ```
   直到清单全部通过且 `validate.py`(pptx skill 自带)PASS。**不允许**带着已知问题交人。常见需要 2–4 轮。
4. 交人(闸门 B):发 pptx + 预览图,**明说预览字体为替代字体、logo 透明在 PPT 中正常**;列出需要人提供的东西(缺的 logo、场次、二维码目标)。
5. commit + push(用户授权前提下;**commit 信息严禁 Claude 署名尾注**)。

## Stage 3 — 人类手改之后的增量迭代
1. `git pull`,以人类的 pptx 为基准;**不再从构建脚本重生成**。
2. 每条批注 → 一个增量脚本 `build/edit_vN.py`(参考 `scripts/example_incremental_edit.py`):按 shape name/文本定位元素,只改被点名的属性;其余一字不动。常用操作见 `references/python_pptx_recipes.md`(改字号、拆 run 上色、项目符号、文字阴影、表格纵向居中、替换图片、移动/缩放)。
3. 每版仍走自检循环 + 校验 + 预览,再交付;版本号递增,commit + push。
4. 场次/时区、会议 logo 要求等事实项变化时,回到 Stage 0 的信息源核对,不凭记忆。

---

## 黄金标准(摘要;全文见 references/golden_checklist.md)
- 字号(以 56 in 画布为准,印刷放大 ≥1.25×):标题 60–66 / 作者 28 / section 标题 44 / 正文 26–32 / 图注 20 / 表格 20–24。**正文体与图注体必须两套样式**(图注:小一号、灰、斜体、"Figure N." 前缀)。
- 版面:所有面板有明显边框;放图面板白底;文字面板浅底;正文结论放带底色的 callout 框;留白不超过面板 15%;整体先满后匀。
- 图:论文原图保持原宽高比;只裁行不裁轴;图内字号对海报偏小时考虑重出或放大。
- Logo:按**视觉重量**而非等高配平;同机构 logo 同侧成组;项目 logo 不放左上角(会被读成公司标)。
- 语义色:控制词/模式名全文统一上色;section 内加粗用黑,不用主题色。
- 结构:section 编号;结论 bullet 先结论后数据;禁止 "[Put contents here]" 类占位进入交付。
- 校验:预览无溢出红框、`validate.py` PASS、二维码可解码、文件名/commit 无 AI 署名痕迹。

## 事故档案(执行时自查)
- 预览脚本把 RGBA 透明画成黑块 → 已修(alpha 合成到白底);别误报 logo 黑底。
- 字号跳大必溢出:每次调大字号都要重跑预览;装不下就缩图/缩文,不许溢出交付。
- 裁切图露出下一行 y 轴/切掉 x 轴标签:裁切线要看带状截图确认。
- 增量脚本拆 run 时丢字(label 被切成多个 run):重写整段 run 而不是局部清空。
- 日程页时区陷阱(EDT 显示 ≠ 当地 PDT):场次一律以官网"会议当地时区"为准。
- 二维码只校验 SVG 不校验版面:最终以打印版实际解码为准(名片同理)。
