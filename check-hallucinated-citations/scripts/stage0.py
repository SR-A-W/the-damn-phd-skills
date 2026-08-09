#!/usr/bin/env python3
"""
Stage 0 —— 引用核查的确定性部分（不联网，不用 LLM）。

用法:
    python3 stage0.py <项目目录或 .bib 路径> [-o 输出目录] [--pdf <论文.pdf>]

做四件事：
  1. 锁定编译链（主 .tex → \\input 链，**剥离注释**后统计），得出真正 live 的 cite key
  2. 解析 .bib 为结构化条目
  3. 维度 8 重复检测（归一化标题 / arXiv id / DOI 分桶 + 模糊标题比对）
  4. 确定性红旗扫描（占位符、arXiv-id 与 year 矛盾、未来年份、作者表截断却无 and others …）

输出 <out>/refs.json 与 <out>/stage0.json，供后续联网核查 workflow 使用。
"""
import re, os, sys, json, difflib, argparse, unicodedata


# ---------------------------------------------------------------- bib 解析
def parse_bib(text):
    entries = []
    for m in re.finditer(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', text):
        etype, key = m.group(1).lower(), m.group(2)
        if etype in ('comment', 'preamble', 'string'):
            continue
        i = text.index('{', m.start())
        depth = 0
        for j in range(i, len(text)):
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0:
                    break
        body, fields, pos = text[m.end():j], {}, 0
        while pos < len(body):
            fm = re.compile(r'\s*(\w+)\s*=\s*').match(body, pos)
            if not fm:
                break
            fname, vs = fm.group(1).lower(), fm.end()
            if vs >= len(body):
                break
            if body[vs] == '{':
                d = 0
                for k in range(vs, len(body)):
                    if body[k] == '{':
                        d += 1
                    elif body[k] == '}':
                        d -= 1
                        if d == 0:
                            break
                val, pos = body[vs + 1:k], k + 1
            elif body[vs] == '"':
                k = body.index('"', vs + 1)
                val, pos = body[vs + 1:k], k + 1
            else:
                k = body.find(',', vs)
                k = len(body) if k == -1 else k
                val, pos = body[vs:k].strip(), k
            fields[fname] = ' '.join(val.split())
            c = body.find(',', pos)
            if c == -1:
                break
            pos = c + 1
        entries.append({"key": key, "type": etype, **fields})
    return entries


# ------------------------------------------------- LaTeX 注释剥离（关键！）
def strip_comments(s):
    """去掉每行未转义 % 之后的内容。统计 undefined/uncited 前必须做，否则模板里
    注释掉的示例 \\cite 会被误判为未定义引用。"""
    out = []
    for line in s.split('\n'):
        r, i = '', 0
        while i < len(line):
            if line[i] == '\\' and i + 1 < len(line):
                r += line[i:i + 2]
                i += 2
                continue
            if line[i] == '%':
                break
            r += line[i]
            i += 1
        out.append(r)
    return '\n'.join(out)


CITE = re.compile(
    r'\\(?:cite|citep|citet|citeal[pt]|citeyear|citeauthor|citenum|nocite|Citep|Citet)'
    r'\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}')


def find_main_candidates(root):
    """返回所有含 \\begin{document} 的 .tex（= 候选主文件），按"像主文件"排序。

    ⚠️ 多候选时**绝不能静默选一个**——投稿包里常同时存在 tmlr.tex(模板原版) 和
    tmlr_new.tex(真正编译的)，选错会审错整份文献表。多候选时必须让人确认。
    """
    cands = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if not n.endswith('.tex'):
                continue
            p = os.path.join(dirpath, n)
            try:
                t = open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            s = strip_comments(t)
            if '\\begin{document}' not in s:
                continue
            cands.append({
                "path": os.path.relpath(p, root),
                "has_bibliography": ('\\bibliography' in s or '\\printbibliography' in s),
                "n_inputs": len(re.findall(r'\\(?:input|include)\{', s)),
                "n_cites": len(CITE.findall(s)),
            })
    # 更像主文件：有 bibliography > \input 更多 > 自身 cite 更多
    cands.sort(key=lambda c: (not c["has_bibliography"], -c["n_inputs"], -c["n_cites"]))
    return cands


def resolve_chain(main_path, root):
    """跟随 \\input/\\include 链（剥离注释后），返回参与编译的文件列表。"""
    seen, order, stack = set(), [], [main_path]
    while stack:
        p = stack.pop(0)
        rp = os.path.realpath(p)
        if rp in seen or not os.path.exists(p):
            continue
        seen.add(rp)
        order.append(os.path.relpath(p, root))
        txt = strip_comments(open(p, encoding='utf-8', errors='replace').read())
        for inc in re.findall(r'\\(?:input|include)\{([^}]+)\}', txt):
            cand = inc if inc.endswith('.tex') else inc + '.tex'
            for base in (os.path.dirname(p), root):
                f = os.path.join(base, cand)
                if os.path.exists(f):
                    stack.append(f)
                    break
    return order


# ------------------------------------------------------------ 维度 8 去重
def norm_title(t):
    t = unicodedata.normalize('NFKD', t or '')
    t = re.sub(r'\{|\}|\\[a-zA-Z]+', '', t)
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', t.lower()).split())


def arxiv_id(e):
    blob = ' '.join(str(e.get(f, '')) for f in
                    ('eprint', 'journal', 'booktitle', 'url', 'note', 'howpublished', 'archiveprefix'))
    m = re.search(r'(\d{4}\.\d{4,5})', blob)
    return m.group(1) if m else None


def find_dups(entries, live):
    buckets, byk = {}, {e['key']: e for e in entries}
    for e in entries:
        tags = []
        if e.get('title'):
            tags.append(('title', norm_title(e['title'])))
        if arxiv_id(e):
            tags.append(('arxiv', arxiv_id(e)))
        if e.get('doi'):
            tags.append(('doi', e['doi'].lower().strip()))
        for t in tags:
            buckets.setdefault(t, []).append(e['key'])
    exact, seen = [], set()
    for (by, val), ks in buckets.items():
        if len(ks) > 1:
            sig = tuple(sorted(ks))
            if sig in seen:
                continue
            seen.add(sig)
            exact.append({"by": by, "value": val, "keys": sorted(ks),
                          "both_live": sorted(k for k in ks if k in live)})
    lk = sorted(live & {e['key'] for e in entries})
    fuzzy = []
    for i in range(len(lk)):
        for j in range(i + 1, len(lk)):
            a, b = norm_title(byk[lk[i]].get('title', '')), norm_title(byk[lk[j]].get('title', ''))
            if not a or not b:
                continue
            r = difflib.SequenceMatcher(None, a, b).ratio()
            if r >= 0.86 and not any(set([lk[i], lk[j]]) <= set(d['keys']) for d in exact):
                fuzzy.append({"ratio": round(r, 3), "keys": [lk[i], lk[j]],
                              "titles": [byk[lk[i]].get('title', ''), byk[lk[j]].get('title', '')]})
    return exact, fuzzy


# ------------------------------------------------------- 确定性红旗扫描
PLACEHOLDER = re.compile(r'YYYY|MM-DD|\bTBD\b|\btbd\b|XXXX|TODO|FIXME|\?\?\?', re.I)


def red_flags(entries, live, this_year):
    F = []
    for e in entries:
        if e['key'] not in live:
            continue
        k, y = e['key'], str(e.get('year', ''))

        for f, v in e.items():
            if isinstance(v, str) and PLACEHOLDER.search(v):
                F.append({"key": k, "kind": "placeholder", "detail": f"{f} = {v[:80]}",
                          "why": "模板占位符没替换，会原样印进 PDF"})

        aid = arxiv_id(e)
        if aid and y.isdigit():
            yy, mm = int(aid[:2]), int(aid[2:4])
            axy = 2000 + yy
            if 1 <= mm <= 12:
                if int(y) < axy:
                    F.append({"key": k, "kind": "year_before_arxiv",
                              "detail": f"year={y} 早于 arXiv {axy}-{mm:02d}",
                              "why": "不可能：年份早于预印本本身"})
                elif int(y) > axy and re.search(r'arxiv|preprint', str(e.get('journal', '')), re.I):
                    F.append({"key": k, "kind": "year_venue_conflict",
                              "detail": f"venue 写 arXiv {axy}-{mm:02d} 但 year={y}",
                              "why": "自相矛盾：要么改 year，要么把 venue 换成正式发表处"})
                if axy > this_year:
                    F.append({"key": k, "kind": "future_arxiv",
                              "detail": f"arXiv id 指向 {axy}-{mm:02d}（未来）",
                              "why": "arXiv id 月份晚于今天，需确认是否编造"})

        if y.isdigit() and int(y) > this_year:
            F.append({"key": k, "kind": "future_year", "detail": f"year={y}",
                      "why": "晚于当前年份，常见于把 12 月会议标成次年"})

        au = e.get('author', '')
        if au and re.search(r'\band\s+others\b|\bet\s+al\.?', au, re.I) \
                and len(re.split(r'\s+and\s+', au)) <= 2:
            F.append({"key": k, "kind": "suspicious_et_al", "detail": au[:90],
                      "why": "作者极少却带 et al./others，可能是多余的"})
    return F


def author_counts(entries, live):
    """离线只能数出"列了几位、有没有 and others"；**是否被截断必须联网核**。
    输出给联网那一步当输入：无 and others 的条目要逐条比对真实作者数。"""
    out = []
    for e in entries:
        if e['key'] not in live or not e.get('author'):
            continue
        au = e['author']
        out.append({"key": e['key'],
                    "n_listed": len(re.split(r'\s+and\s+', au)),
                    "has_others": bool(re.search(r'\band\s+others\b', au, re.I))})
    return out


# ------------------------------------------------------------- PDF 回退
def pdf_checks(pdf):
    import subprocess, tempfile
    out = {"available": False}
    try:
        txt = subprocess.run(['pdftotext', '-layout', pdf, '-'],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception as ex:
        out["error"] = str(ex)
        return out
    out["available"] = True
    out["undefined_marks"] = len(re.findall(r'\[\?\]', txt))
    i = txt.rfind('\nReferences')
    if i < 0:
        i = txt.rfind('\nREFERENCES')
    if i >= 0:
        seg = txt[i + 11:]
        m = re.search(r'\n\s*(?:A\s+[A-Z][a-z].*|Appendix\b.*)\n', seg)
        seg = seg[:m.start()] if m else seg
        ents, cur = [], None
        for l in seg.split('\n'):
            if not l.strip():
                continue
            if not l.startswith(' ') and re.match(r'^[A-Z\{"\u201c]', l):
                if cur:
                    ents.append(' '.join(cur.split()))
                cur = l
            else:
                if cur is not None:
                    cur += ' ' + l.strip()
        if cur:
            ents.append(' '.join(cur.split()))
        out["rendered_entries"] = len(ents)
        out["entries"] = ents
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='LaTeX 项目目录，或直接给 .bib 文件')
    ap.add_argument('-o', '--out', default='./citation_audit_out')
    ap.add_argument('--main', help='主 .tex（多候选时必须指定；相对项目目录）')
    ap.add_argument('--pdf', help='已编译 PDF（做渲染核对：[?] 数、书目条目数）')
    ap.add_argument('--year', type=int, default=None, help='当前年份（判断"未来年份"用）')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    this_year = a.year or __import__('datetime').date.today().year

    if a.target.endswith('.bib'):
        root, bibs = os.path.dirname(a.target) or '.', [a.target]
    else:
        root = a.target
        bibs = [os.path.join(d, n) for d, _, ns in os.walk(root) for n in ns if n.endswith('.bib')]
    if not bibs:
        sys.exit('找不到 .bib 文件')

    entries, seen_keys = [], set()
    for b in bibs:
        for e in parse_bib(open(b, encoding='utf-8', errors='replace').read()):
            if e['key'] in seen_keys:
                continue
            seen_keys.add(e['key'])
            entries.append(e)

    chain, cited, main_tex, cands = [], {}, None, []
    if not a.target.endswith('.bib'):
        cands = find_main_candidates(root)
        if a.main:
            main_tex = os.path.join(root, a.main) if not os.path.isabs(a.main) else a.main
            if not os.path.exists(main_tex):
                sys.exit(f'--main 指定的文件不存在: {main_tex}')
        elif len(cands) == 1:
            main_tex = os.path.join(root, cands[0]["path"])
        elif len(cands) > 1:
            print("⚠️  发现多个候选主文件——**不猜**。请用 --main <路径> 指定真正编译的那个：")
            for c in cands:
                print(f"    {c['path']:<34} bibliography={c['has_bibliography']} "
                      f"\\input={c['n_inputs']} 自身cite={c['n_cites']}")
            print("  （判据：看投稿系统/Overleaf 实际编译的主文件；\\input 多的通常是真主文件）")
            sys.exit(2)
        if main_tex:
            chain = resolve_chain(main_tex, root)
            for f in chain:
                p = os.path.join(root, f)
                txt = strip_comments(open(p, encoding='utf-8', errors='replace').read())
                for m in CITE.finditer(txt):
                    for k in m.group(1).split(','):
                        k = k.strip()
                        if k:
                            cited.setdefault(k, []).append(f)

    defined = {e['key'] for e in entries}
    live = set(cited) if cited else defined      # 只给 .bib 时视全部为 live
    undefined = sorted(set(cited) - defined)
    uncited = sorted(defined - set(cited)) if cited else []
    exact, fuzzy = find_dups(entries, live)
    flags = red_flags(entries, live, this_year)

    # 未参与编译的 .tex（其中的 \cite 不算数）
    orphan = []
    if main_tex:
        allt = {os.path.relpath(os.path.join(d, n), root)
                for d, _, ns in os.walk(root) for n in ns if n.endswith('.tex')}
        orphan = sorted(allt - set(chain))

    s0 = {"root": root, "main_tex": os.path.relpath(main_tex, root) if main_tex else None,
          "main_candidates": cands,
          "compile_chain": chain, "not_compiled": orphan,
          "bib_files": [os.path.relpath(b, root) for b in bibs],
          "n_defined": len(defined), "n_live_cited": len(live),
          "cited": {k: v for k, v in cited.items()},
          "undefined": undefined, "uncited": uncited,
          "dup_exact": exact, "dup_fuzzy": fuzzy, "red_flags": flags,
          "author_counts": author_counts(entries, live)}
    if a.pdf:
        s0["pdf"] = pdf_checks(a.pdf)

    # 维度 7 素材：每个 key 的 in-text 上下文（供 make_workflow.py 用）
    ctx = {}
    for f in chain:
        p = os.path.join(root, f)
        flat = ' '.join(strip_comments(open(p, encoding='utf-8', errors='replace').read()).split())
        for m in CITE.finditer(flat):
            lo, hi = max(0, m.start() - 420), min(len(flat), m.end() + 160)
            for k in m.group(1).split(','):
                k = k.strip()
                if k:
                    ctx.setdefault(k, []).append({"file": f, "snippet": flat[lo:hi]})

    json.dump(entries, open(os.path.join(a.out, 'refs.json'), 'w'), indent=1, ensure_ascii=False)
    json.dump(s0, open(os.path.join(a.out, 'stage0.json'), 'w'), indent=1, ensure_ascii=False)
    json.dump(ctx, open(os.path.join(a.out, 'contexts.json'), 'w'), indent=1, ensure_ascii=False)

    p = print
    p(f"主文件      : {s0['main_tex']}")
    p(f"编译链      : {len(chain)} 个 .tex")
    if orphan:
        p(f"  未编译    : {orphan}   ← 其中的 \\cite 不计入")
    p(f"bib 条目    : {len(defined)}")
    p(f"live 引用   : {len(live)}    (未被引用 {len(uncited)} 条，不进 PDF)")
    p(f"UNDEFINED   : {len(undefined)} {undefined if undefined else '✅ 不会出现 [?]'}")
    p(f"重复(精确)  : {len(exact)}")
    for d in exact:
        mark = "❗两个都被引→PDF 里重复" if len(d['both_live']) > 1 else "（仅 bib 冗余）"
        p(f"    by {d['by']}: {d['keys']}  {mark}")
    p(f"重复(模糊)  : {len(fuzzy)}")
    for d in fuzzy:
        p(f"    {d['ratio']} {d['keys']}")
    p(f"确定性红旗  : {len(flags)}")
    for f in flags:
        p(f"    [{f['key']}] {f['kind']}: {f['detail']}")
    noth = [c for c in s0['author_counts'] if not c['has_others'] and c['n_listed'] >= 6]
    p(f"待联网核作者数: {len(noth)} 条列了 ≥6 位却无 'and others' —— 逐条比对真实作者数，"
      f"被截断却没写 others = 真错误（离线判不了）")
    if a.pdf and s0.get('pdf', {}).get('available'):
        q = s0['pdf']
        p(f"PDF          : [?]={q['undefined_marks']}  渲染书目={q.get('rendered_entries','?')} 条"
          f"  (应等于 live 引用数 {len(live)})")
    p(f"\n已写出 {a.out}/refs.json 与 {a.out}/stage0.json")


if __name__ == '__main__':
    main()
