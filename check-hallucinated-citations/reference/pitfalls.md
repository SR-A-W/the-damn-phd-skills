# 踩坑清单 —— 假警报与漏检的来源

> 这份清单是从真实审稿中攒出来的。**误报和漏检同样致命**：误报会让作者改坏正确的东西，
> 漏检会让幻觉引用进 camera-ready。下判断前先扫一遍这里。

---

## A. 会造成**误报**的（说人家错、其实人家对）

### A1. 忠实于官方记录 ≠ 错误
被引条目的字段要和**它所引版本的 canonical 记录**比，不是和"这个人一般怎么写"比。

| 真实案例 | 表象 | 真相 |
|---|---|---|
| DeepSeek-V2 作者 `Chengqi Dengr` | 像把 Deng 拼成 Dengr | **arXiv 官方元数据本身就是 "Chengqi Dengr"**（DeepSeek 投稿时的笔误），引用是忠实的 |
| `geva2022ffn` 作者 `Kevin Wang` | PDF 署名是 Kevin Ro Wang | **ACL Anthology 官方元数据就是 "Kevin Wang"** |
| DeepSeekMath `YK Li` / `Y Wu` | 像缩写偷懒 | arXiv 记录本身就只印首字母 |

**判据**：报错前必须能说出"canonical 记录写的是 X，bib 写的是 Y"。说不出就不是错。

### A2. 同一个人的**不同名字写法** ≠ 拼写错误（最隐蔽的一类）
真实案例：某条引用写 `Yang, Wang`，而所引论文的 TMLR 官方记录是 `Van Yang`。
一度被判为"作者名错"——**其实是同一个人的两种写法**，而且这人正是**引用方论文的共同第一作者**，
在同一份书目的另外 5 条里也一律写作 "Wang Yang"。

**动手前必查两件事**：
1. 这个名字是不是**引用方作者自己或其合作者**？（比对本文作者块 `\author{...}`）
2. 同一份书目里这个人**其它条目**怎么写的？

若是同一人的写法差异 → **不是错误**，是取舍；强行统一成被引记录的写法反而会让同一人在同一份
书目里出现两种名字。**交给作者本人决定，别当 bug 报。**

### A3. et al. / `and others` 未必多余
`Mixtral`/`Qwen3`/`Gemma`/`GPT-OSS`/`DeepSeek-R1`/`o1`/`Kimi` 这类论文**作者真的有几十上百位**，
`and others` 用得完全正确。**先查真实作者数，再决定 et al. 是否多余。**

### A4. OpenAlex 对 TMLR 有系统性索引缺失
真实案例：Voyager（TMLR 2024）在 OpenAlex 只有 arXiv preprint 记录、`is_published=false`，
差点被误报成"venue 造假"。**原因：TMLR 没有逐篇 DOI**，OpenAlex 常关联不上 OpenReview 托管的文章。
→ 凡 venue 写 TMLR 而 OpenAlex 查不到的，**先按索引缺失处理**，用 DBLP（`journals/tmlr/...`）
和 OpenReview 交叉验证。

### A5. 403 ≠ 链接失效
MAA、部分出版商站点对自动化工具返回 **403（Cloudflare 反爬）**，这**不能**证明链接坏了。
要判失效用 Wayback（`archive.org/wayback/available?url=`）或请人工点一下。

### A6. PDF 切分工件
从渲染 PDF 提取书目时，**以小写词开头的条目**（如 "contributors Fred …"）会被并进上一条，
造成"两篇被合并成一条"的假象。报 merged 前**先回查 PDF 原文**。

### A7. 未参与编译的章节 / 注释掉的 cite 不算数
统计 undefined/uncited **必须先剥离 `%` 注释**，且只统计真正进入 `\input` 链的文件。
真实案例：模板里注释掉的示例 `\citep{Hinton06}` 被误报成"5 个未定义引用会渲染成 [?]"。

### A8. dim 7 的类别指针不是错配
`MoE architectures~\citep{a,b,c}` 这种**类别指针**，只要被引文献属于该类别就是 SUPPORTED，
不要求精确对应某个论断。只有**逐项断言**才逐条检验（见 B3）。

---

## B. 会造成**漏检**的（人家错了、没查出来）

### B1. 绝不相信 REAL 标签 —— 对**全部条目**挖 field_diffs
大规模 sweep 倾向把字段小错记成「REAL + field_diff」而非 SUSPICIOUS，于是跳过对抗验证 → 漏检。
**纪律**：不管 verdict 是什么，把每条的 `field_diffs` 全部导出来人工过一遍，
按 author/year 类优先排序。真实案例里最严重的几个错都藏在标 REAL 的条目里。

### B2. 维度 7 能抓到维度 1–6 **结构上抓不到**的错
真实案例：某论文维度 1–6 结果是 **44/44 REAL、0 可疑、0 虚构**，看起来完美；
维度 7 抓出 2 条 MISMATCH（Gemma 3 和 DeepSeek-V2 被写成"采用了 hybrid thinking"，
而这两个模型根本没有 thinking mode）。
**被引文献 100% 真实、字段 100% 正确 —— 错的是它被挂到了哪个论点上。**
→ 只要拿得到正文源码，**维度 7 必做**，不是可选加餐。

### B3. 最危险的句式：**逐项断言**（distributive claim）
`...has been adopted by several recent systems~\citep{A,B,C,D}` ——
它对每个 key 都是可证伪的事实主张，但因为正文**没有点名**，作者和读者都看不出 key 挂错了。
同类：`X, Y, and Z all use ...`、`methods such as~\citep{...}`、
以及**属性词**（lossless / training-free / zero-shot / first to）。

真实案例：`li2026jwsvd` 被列进 "**lossless** weight compression"，但它是 SVD 低秩截断（**有损**）。

### B4. ⭐ 被注释掉的原稿行是排查错配的金矿
真实案例的根因就藏在一行 `%` 注释里：
```latex
% This paradigm has been adopted by Gemini~\citep{team2025gemma}, ..., and DeepSeek V3.1~\citep{liu2024deepseek}.
```
作者本意是 **Gemini** 和 **DeepSeek V3.1**，挂的 key 却是 **Gemma 3** 和 **DeepSeek-V2**。
改写成 "several recent systems" 后名字消失，错配被藏起来。
→ **计数要剥注释，找意图要读注释**（两者不冲突）。对可疑 key 额外 grep 一遍注释行。

### B5. 作者表被截断却**没写 `and others`** = 实打实的错误
真实案例：某条只列 6 位（真实 9 位）且结尾无 `and others` → 书目谎称这篇就 6 位作者，
漏掉的还包括通讯作者。**这比"多余的 et al."严重得多。**
→ 逐条比对**作者数**；区分「truncated **with** others」（正常）vs「**without**」（错误）。

### B6. 作者表要和**所声称的 venue 版本**对齐
同一篇的不同版本作者数可能不同：
- `shinn2023reflexion`：booktitle 写 NeurIPS，作者表却用 arXiv v4（6 位，含 Edward Berman）；
  **NeurIPS 正式版只有 5 位**。不是捏造，是"混源"。
- `hariri2026quantize`：arXiv 版 9 位、ACL Findings 版 7 位 —— 引 Findings 就该按 7 位算。

### B7. 自引最容易错
真实案例中错得最离谱的一条恰恰是**引用作者自己的 TMLR 论文**：3 个合作者名字全错 + 年份错。
**别因为"是他自己的论文"就默认没问题**——自引常靠记忆手写。
→ 一律去取**官方 BibTeX** 比对（见 C2）。

### B8. "已录用某会议"的声明必须去该会议论文集实证
真实存在的 arXiv 论文 + **未经证实的同行评审 venue 声明** = 真问题（判 SUSPICIOUS/venue）。
尤其当年/次年的新会议（"Findings of ACL 2026"）最需要查。

### B9. 重复检测（维度 8）必须**独立做一步**
不能指望逐条核查顺带发现。真实案例：251 条里 **17 对重复**，其中 6 对两个 key 都被引
（PDF 书目里同一篇出现两次），第一版漏做去重、是作者自己在 PDF 里发现的。
**信号**：带描述前缀的 key（`AlphaFold2_jumper2021highly`）常与裸 key（`jumper2021highly`）是同一篇。

### B10. 改完要确认 **PDF 重新编译过**
只交 PDF 的场合，bib 改了但没重编 = 等于没改。
→ 在渲染出的 PDF 书目里直接 grep 新值（如 `Maziarz`）确认生效。

---

## C. 可靠的查证源与技巧

### C1. 优先级
结构化 API / 稳定 URL 优先，证据可点击可复现：

| 场景 | 首选 |
|---|---|
| 通用存在性 | `api.crossref.org/works?query.bibliographic=` 、`api.openalex.org/works?filter=title.search:` |
| arXiv | `arxiv.org/abs/<id>`、`export.arxiv.org/api/query?id_list=<id>` |
| ACL/EMNLP/NAACL/Findings | ACL Anthology（`aclanthology.org/<venue-id>/`），有逐篇 DOI |
| NeurIPS/ICML | `proceedings.neurips.cc`、PMLR |
| ICLR / TMLR / 走 OpenReview 的 | **见 C2** |
| 模型 / 数据集 | HuggingFace API `huggingface.co/api/models/<org>/<name>`（`createdAt` 就是发布日期） |
| 链接是否失效 | Wayback `archive.org/wayback/available?url=` |

### C2. ⭐ OpenReview 的正确打开方式
`openreview.net/forum?id=` 和 `api2.openreview.net/notes?forum=` 会被 **302 到人机验证页**。
**绕过方法**——用 search 端点，它不在 bot 墙后面：

```
https://api2.openreview.net/notes/search?term=<论文标题>&limit=5
```

一次调用返回 `venue` / `venueid` / 完整 `authors` 数组 / **官方 `_bibtex`**（含逐字作者名和 year）。
TMLR / ICLR / NeurIPS 这类，**一次把 venue + 作者 + 年份全锁死**。核自引时这是最高效的一招。

### C3. 证据纪律
- 判 **REAL** 必须附**可点击 canonical id**（DOI / arXiv id / 稳定 URL）。
- 判 **FABRICATED** 必须附**检索轨迹**（搜过哪些源、什么关键词），否则"查无此文"不构成证据。
- 宁可标**可疑**也不轻易下**虚假**——虚假指控代价最高。
- LLM 子 agent **自己也会幻觉**"某假文献是真的" → 非平凡判定一律走对抗式二次验证。
