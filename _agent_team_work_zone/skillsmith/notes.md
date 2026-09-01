# SkillSmith 工作笔记

(工作中积累的重要知识会记录在这里)

## 维护对象（4 个 skill，项目根目录）

- `check-hallucinated-citations/` — 参考文献幻觉核查。含 SKILL.md + scripts/（make_workflow.py, stage0.py）+ reference/pitfalls.md。7 个核查维度：1–6 抓"文献不存在类"，7 抓"文献真实但不支持论点"。git status 显示 pitfalls.md 和 make_workflow.py 有未提交改动（入职时已存在，非我所改）。
- `graceful-self-citation/` — 优雅自引织入。只有 SKILL.md。增量模式（GSC-LEDGER 台账），Scholar 人物模式 / 单篇模式。
- `paper-severe-issue-audit/` — 八类严重问题终审。只有 SKILL.md。regex 撒网 + 人工分诊。
- `preprint-release/` — arXiv 上传包整理。只有 SKILL.md。8 步流程，副本隔离 + pdftotext diff=0 验收。

## 反馈台账

(格式：日期 | 来源 | 涉及 skill | 问题摘要 | 处理结论/改动)

- 2026-08-31 | `downstream_feedback/20260831`（EMNLP 2026 camera-ready 实战，含 tar 包 3 份报告 + 3 份 patch）| preprint-release | 缺陷 1–10（.bbl 时序、diff 基线跨模式失效、删图无验收、cleaner 双目录、error 锚点、--keep_bib 缺失、故意变更无通道、词级 diff、文件名平台兼容、环境预检）| 应用下游附带的 `preprint-release_cumulative.patch`（审查后全盘采纳），另补「作用域总纲」一段
- 2026-08-31 | 同上 | check-hallucinated-citations | 缺陷 1–8（陈旧 .bst 反转判据、维度 2 基准未钉死、dim7 只搜自己术语、多键 citep 移除后不复查、计数口径、缺渲染保真维度、PDF 链接层盲区、完整性/DOI）| 手工改 SKILL.md：新增**维度 9 渲染保真**（8 维→9 维）、维度 2 基准钉死为 arXiv /abs 当前标题、Stage 0 加 .bst 版本核实、§4 加 .bbl 权威计数口径、§5 加检索词扩展纪律、§6 验收清单加 pdfplumber 链接矩形检查、§7 加多键移除复查、加可选完整性检查 + 作用域总纲。维度 9 目前是文档级指引，**未**改 stage0.py（脚本有他人未提交改动，且自动化属后续工作）
- 2026-08-31 | 同上 | graceful-self-citation | 缺陷 1–9 + 1 正面案例（WebFetch 编造逐字引用、漏搜附录、标题误导、归属统计口径、高引前 3 篇、venue 未出版留痕、姓名官方源冲突、作者表漂移、标题版本漂移；JW-SVD 零幻觉纪律生效正例）| 手工改 SKILL.md：Phase 0 加先例附录检查、Phase 2 加"必读摘要"+"高引前 3 篇深核"、Phase 5 大幅扩充（逐字取证、作者表重拉、标题以 /abs 当前为准、venue 留痕、官方源姓名冲突以作者本人为准、归属统计口径），正面案例记入"停下要材料"条目，加作用域总纲

## 三份报告共同的结构性教训（已分别写进三个 skill 的总纲）

> 检查跑了、也通过了，但检查的作用域比被检查对象的作用域窄。
> 一个「通过」的保证上限是它的作用域——每报告一项通过，同时说明这项检查看不见什么。

## 遗留 / 后续可做

- 维度 9（渲染保真）可自动化进 `check-hallucinated-citations/scripts/`（比对 .bib 字段 vs .bbl 渲染）——本轮只做了文档级，因 scripts 有入职前未提交改动、且属新功能开发
- `paper-severe-issue-audit` 本轮无反馈，未动
- 下游反馈包留在 `downstream_feedback/20260831/`，解包副本在 scratchpad（session 结束即弃）
