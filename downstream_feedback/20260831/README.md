# 上游 skill 反馈包

本目录汇总对四个第三方 skill 的使用反馈。全部来自一次真实任务：
将一篇已录用论文（EMNLP 2026 Main）从 ARR 投稿版做成 camera-ready。

**所有缺陷均为实测撞上，不是设想。** 每条都注明触发条件、实际后果与修正思路；
证据强度分 🔴 实测 / 🟡 推断两级。

## 目录

| skill | 文件 | 缺陷数 | 状态 |
|---|---|---|---|
| `preprint-release` | `preprint-release_UPSTREAM_REPORT_round1.md`（缺陷 1–5）<br>`preprint-release_UPSTREAM_REPORT_round2.md`（缺陷 6–10） | 10 | 含 3 份可直接应用的 patch |
| `check-hallucinated-citations` | `check-hallucinated-citations_UPSTREAM_REPORT.md` | 8 | 含 1 个建议新增的维度 |
| `graceful-self-citation` | `graceful-self-citation_UPSTREAM_REPORT.md` | 9 | 含 1 个正面案例 |
| `paper-severe-issue-audit` | — | — | 本次未使用，无反馈 |

## patch 说明

`preprint-release` 的三份 patch 针对其 `SKILL.md`：
- `preprint-release_round1.patch` —— 仅第一轮（缺陷 1–5）
- `preprint-release_round2.patch` —— 仅第二轮（缺陷 6–10）
- `preprint-release_cumulative.patch` —— 两轮合并，**建议用这份**

另外三个 skill 只给了报告，没有 patch —— 因为其中几条建议涉及新增检查维度或
改变判据基准，属于设计决策，不宜由使用方直接改写。

## 三个 skill 共同暴露的一个结构性问题

三份报告是各自独立写的，但回看时发现缺陷高度同构：

> **检查跑了、也通过了，但检查的作用域比被检查对象的作用域窄。**

具体表现：
- `preprint-release`：diff 基线跨模式不可比，导致核心验收**静默失效**——
  它一直在"通过"，只是比的是错的东西
- `check-hallucinated-citations`：维度 2 的比对基准是「bib 声称的版本」而非当前版本；
  验收清单覆盖源码与文本层，不覆盖 PDF 的链接层
- `graceful-self-citation`：作者归属统计以 Scholar Profile 收录为口径，
  而非以每篇文章的真实作者表为口径，系统性低估某类合作者

**建议三个 skill 都在开头加一条总纲：**
每报告一项通过，同时说明这项检查看不见什么。一个"通过"所提供的保证，
上限是它的作用域——而使用者往往把它读成"这方面没问题"。

本轮最有力的佐证：**三个真实缺陷全部由论文作者肉眼在 PDF 上发现**
（书目里的 `and 1 others`、整张表格变成可点击链接、缩写被样式压成小写），
而当时已经跑过 202 个 agent 的全量核查、外加一次 197 个 agent 的独立第三方核查。

## 另一件值得上游知道的事

`check-hallucinated-citations` 报告里的缺陷 3（判定「该文献不讲 X」时只搜自己的术语），
**被一个完全独立的第三方核查在同一条上重现**。两边都读了原文、都没搜同义词。
这说明它不是个别 agent 的疏忽，而是方法本身缺了一步。
