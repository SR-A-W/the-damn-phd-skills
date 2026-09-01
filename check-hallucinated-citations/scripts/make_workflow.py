#!/usr/bin/env python3
"""
把 stage0.py 的输出变成一个**自包含**的 Workflow 脚本（数据内嵌，不靠 args）。

用法:
    python3 make_workflow.py <stage0 输出目录> -o run.js [--keys k1,k2,...] [--no-dim7]

为什么内嵌数据：Workflow 的 args 传大 JSON 不可靠（本 session 踩过：几十 KB 的 args
到脚本里变成空/字符串）。直接把数组写进脚本最稳。

生成的 workflow：
    Verify(dims1-6, sonnet) → Adversary(每条都强制复核, opus) → Dim7(内容一致性, sonnet)
"""
import os, re, json, argparse

TPL = r'''export const meta = {
  name: 'citation-audit',
  description: 'Audit a bibliography for hallucinated/mis-cited references: existence+fields, adversarial recheck, content-consistency',
  phases: [
    { title: 'Verify',    detail: 'dims 1-6 existence + field match' },
    { title: 'Adversary', detail: 'independent adversarial recheck of EVERY entry' },
    __DIM7_PHASE__
  ],
}

const ITEMS = __DATA__
const LEVEL = '__LEVEL__'          // quick | standard | full
const DO_ADV = LEVEL !== 'quick'
const DO_DIM7 = __DO_DIM7__

log(`citation-audit [${LEVEL}]: ${ITEMS.length} entries — dims1-6${DO_ADV?' + adversarial':''}${DO_DIM7?' + dim7':''}`)

const VERDICT = {
  type:'object', additionalProperties:false,
  properties:{
    verdict:{type:'string',enum:['REAL','SUSPICIOUS','FABRICATED']},
    problem_types:{type:'array',items:{type:'string',enum:['existence','title','author','year','venue','detail','duplicate','retracted','none']}},
    canonical_id:{type:['string','null']},
    matched_title:{type:['string','null']}, matched_authors:{type:['string','null']},
    matched_year:{type:['string','null']},  matched_venue:{type:['string','null']},
    n_authors_cited:{type:['number','null'],description:'how many authors the citation lists'},
    n_authors_real:{type:['number','null'],description:'how many the real record has'},
    author_truncated_without_etal:{type:'boolean',description:'citation lists FEWER authors than the record AND has no "and others"/et al. -> bibliography silently misstates authorship = REAL ERROR'},
    venue_status:{type:'string',enum:['confirmed_published','preprint_only','venue_unconfirmed','not_applicable'],description:'if a peer-reviewed venue is claimed, did you CONFIRM it in that venue proceedings?'},
    field_diffs:{type:'array',items:{type:'object',additionalProperties:false,required:['field','cited','found'],properties:{field:{type:'string'},cited:{type:'string'},found:{type:'string'}}}},
    evidence:{type:'array',items:{type:'string'}},
    search_trail:{type:'array',items:{type:'string'}},
    notes:{type:'string'},
  },
  required:['verdict','problem_types','canonical_id','matched_title','venue_status',
            'n_authors_cited','n_authors_real','author_truncated_without_etal',
            'field_diffs','evidence','search_trail','notes'],
}

const DIM7 = {
  type:'object', additionalProperties:false,
  properties:{
    verdict:{type:'string',enum:['SUPPORTED','PARTIAL','MISMATCH','UNVERIFIABLE']},
    claim_checked:{type:'string'}, reasoning:{type:'string'},
    problem:{type:['string','null']},
    severity:{type:'string',enum:['none','minor','moderate','serious']},
    evidence:{type:'array',items:{type:'string'}},
  },
  required:['verdict','claim_checked','reasoning','problem','severity','evidence'],
}

const TOOL = `You can search and fetch the web. If WebSearch/WebFetch are unavailable, load them via ToolSearch (query "select:WebSearch,WebFetch"). If WebSearch is rate-limited/exhausted, fall back to WebFetch on direct URLs: arxiv.org/abs/<id>, export.arxiv.org/api/query?id_list=<id>, aclanthology.org, proceedings.neurips.cc, openreview.net, api.crossref.org/works?query.bibliographic=, api.openalex.org/works?filter=title.search:, api2.openreview.net/notes/search?term= . NEVER answer from training memory — model memory is unreliable about whether a specific citation exists.`

function refBlock(r){return [
 r.raw ? `- AS PRINTED IN THE PAPER (authoritative — the fields below are a best-effort parse of this string; if they disagree, trust this):\n    ${r.raw}` : '',
 `- cite key: ${r.key}`,`- entry type: ${r.type}`,`- title: ${r.title}`,`- authors: ${r.author}`,
 `- year: ${r.year}`,`- venue: ${r.venue || '(none)'}`,
 `- volume/number/pages: ${r.volume||'-'}/${r.number||'-'}/${r.pages||'-'}`,
 `- doi: ${r.doi||'(none)'}`,`- arxiv/eprint: ${r.eprint||'(none)'}`,`- url: ${r.url||'(none)'}`].filter(Boolean).join('\n')}

function p1(r){return `You are a citation-integrity auditor. Verify ONE reference from a paper's bibliography: is it a real publication, and do its fields match reality?

${refBlock(r)}

${TOOL}

Verify IN ORDER against authoritative sources (Crossref, Semantic Scholar, DBLP, arXiv/bioRxiv, ACL Anthology, OpenReview, publisher pages):
1. EXISTENCE - resolve to ONE real record; capture a clickable canonical id (DOI / arXiv id / stable URL).
2. TITLE  3. AUTHORS  4. YEAR  5. VENUE  6. DOI/locator.

TWO CHECKS THAT ARE EASY TO MISS - do them explicitly:
(a) AUTHOR COUNT. Count how many authors the citation lists vs how many the real record has.
    Fill n_authors_cited / n_authors_real. If the citation lists FEWER and has NO "and others"/et al.,
    set author_truncated_without_etal=true - the rendered bibliography then falsely claims the paper
    has only those authors. That is a REAL ERROR (worse than a spurious et al.).
(b) VENUE CONFIRMATION. If a peer-reviewed venue is claimed (ACL/EMNLP/NeurIPS/ICLR/ICML/TMLR/Findings/MLSys),
    CONFIRM it in that venue's actual proceedings. venue_status:
      confirmed_published / preprint_only / venue_unconfirmed / not_applicable.
    A real arXiv paper carrying an UNCONFIRMED peer-reviewed venue claim is a genuine problem (SUSPICIOUS, ["venue"]).

COMPARE AGAINST THE VERSION THE ENTRY CLAIMS. Different versions of the same work can have different
author lists (arXiv v4 vs the proceedings version). If booktitle says NeurIPS, compare with the NeurIPS
record, not arXiv. Report mismatches as "you cite the X version; X's official record says N authors".

DO NOT report a difference as an error when the citation faithfully reproduces the canonical record of the
version it cites (upstream typos in official metadata, initials-vs-full-name as printed, etc.). Say so in notes.

CLASSIFY: REAL (dims 1-5 match; MUST have canonical_id) / SUSPICIOUS (a field mismatch, unconfirmed venue,
or thin evidence) / FABRICATED (after genuine multi-source search NO such work exists, or a severe field
transplant; MUST populate search_trail proving the negative).
Bias toward SUSPICIOUS over FABRICATED - a false fabrication accusation is the worst possible error.
Log every source+query in search_trail. Return the structured verdict.`}

const LENS = {
  find:  `Assume it IS real and try HARD to find it: alternate titles/spellings, author-only queries, arXiv listing pages, OpenAlex, Semantic Scholar, author homepages/GitHub.`,
  refute:`Be SKEPTICAL: try to show it is fabricated, mis-cited, or carrying a venue it was never accepted to. Check the claimed venue's official proceedings directly. Do not trust the prior verdict.`,
  author:`Focus on AUTHOR/TITLE disambiguation: is the work truly by THESE authors in THIS order and count, or has a real title been attached to wrong authors? Check same-name-different-person and the author COUNT specifically.`,
}
function p2(r,prior,lens){return `Independently re-verify ONE bibliography reference. A prior pass said "${prior.verdict}" (venue_status=${prior.venue_status}; notes: ${JSON.stringify(prior.notes||'')}). Do your OWN verification and reach your own conclusion.

YOUR ASSIGNED LENS: ${LENS[lens]}

${refBlock(r)}

${TOOL}

Same rules: REAL needs a clickable canonical_id; FABRICATED needs a concrete search_trail; set venue_status
honestly (never confirmed_published unless you actually saw it in that venue's listing); fill the author-count
fields. Return the structured verdict.`}

function p7(r,v){return `Audit CONTENT CONSISTENCY (dimension 7) for one citation.

CITING PAPER CONTEXT: __PAPER_CONTEXT__

CITED WORK (existence already verified${v && v.canonical_id ? ': '+v.canonical_id : ''}):
${refBlock(r)}

HOW THE CITING PAPER USES IT (in-text, LaTeX source):
${(r.claims||[]).map((c,i)=>`  [${i+1}] (${c.file}) ...${c.text}...`).join('\n')}

${TOOL}

Read the cited work (abstract at minimum; the relevant section if the claim is specific), then judge whether
it supports the role it is given.

CALIBRATION - this is where false alarms come from, read carefully:
- CATEGORY POINTERS are legitimate: "MoE architectures~\citep{a,b,c}", "agent benchmarks~\citep{d}".
  If the cited work genuinely belongs to the named category, that is SUPPORTED. Do NOT demand a precise
  claim match for a background/one-of-a-list citation.
- DISTRIBUTIVE CLAIMS are checkable per item: "has been adopted by several recent systems~\citep{a,b,c,d}"
  asserts each of a-d did the thing. Verify each. This is where mis-keyed citations hide, because the prose
  often does not name them.
- Flag PARTIAL/MISMATCH only when the work does not belong to the category it is listed under, or a specific
  attributable assertion (introduced X / showed Y / reports number Z / is lossless) is not borne out.
- Numbers, dataset names, "first to do X", and property words (lossless, training-free, zero-shot) deserve
  the most scrutiny.

Return the structured result.`}

const out = await pipeline(
  ITEMS,
  (it) => agent(p1(it), {label:`verify:${it.key}`, phase:'Verify', schema:VERDICT, model:'sonnet', effort:'medium'}),
  (prior, it) => {
    if (!prior) return {key:it.key, dim16:{final_verdict:'ERROR'}, dim7:null}
    // quick 档只对非 REAL 的做复核；其余档位每条都复核（别信 REAL 标签）
    if (!DO_ADV && prior.verdict === 'REAL') return {prior, votes: []}
    const lenses = prior.verdict === 'REAL' ? ['author'] : ['find','refute','author']
    return parallel(lenses.map(l => () =>
      agent(p2(it,prior,l), {label:`adv:${it.key}:${l}`, phase:'Adversary', schema:VERDICT, model:'opus', effort:'high'})
    )).then(votes => ({prior, votes: votes.filter(Boolean)}))
  },
  (r, it) => {
    if (!r || !r.prior) return {key:it.key, dim16:{final_verdict:'ERROR'}, dim7:null}
    const all = [r.prior, ...r.votes]
    const realId = all.filter(v=>v.verdict==='REAL' && v.canonical_id)
    const fab    = all.filter(v=>v.verdict==='FABRICATED')
    const need = DO_ADV ? 2 : 1
    const fin = realId.length>=need ? 'REAL' : (fab.length>=2 && realId.length===0 ? 'FABRICATED' : 'SUSPICIOUS')
    const diffs=[], seen=new Set()
    for (const v of all) for (const d of (v.field_diffs||[])) {
      const k=d.field+'|'+d.found; if(!seen.has(k)){seen.add(k); diffs.push(d)}
    }
    const vs = all.map(v=>v.venue_status).filter(Boolean)
    const dim16 = {
      final_verdict: fin, votes: all.map(v=>v.verdict),
      venue_statuses: vs, venue_confirmed: vs.includes('confirmed_published'),
      author_truncated_without_etal: all.some(v=>v.author_truncated_without_etal),
      n_authors_cited: (all.find(v=>v.n_authors_cited!=null)||{}).n_authors_cited ?? null,
      n_authors_real:  (all.find(v=>v.n_authors_real !=null)||{}).n_authors_real  ?? null,
      canonical_id: (all.find(v=>v.canonical_id)||{}).canonical_id || null,
      problem_types: [...new Set(all.flatMap(v=>v.problem_types||[]).filter(p=>p&&p!=='none'))],
      field_diffs: diffs,
      evidence: [...new Set(all.flatMap(v=>v.evidence||[]))].slice(0,8),
      search_trail: [...new Set(all.flatMap(v=>v.search_trail||[]))].slice(0,10),
      notes: all.map(v=>v.notes).filter(Boolean)[0] || '',
    }
    const base = {key:it.key, title:it.title, cited_authors:it.author, cited_year:it.year, cited_venue:it.venue, dim16}
    if (!DO_DIM7 || !(it.claims||[]).length) return {...base, dim7:null}
    return agent(p7(it, r.prior), {label:`dim7:${it.key}`, phase:'Dim7', schema:DIM7, model:'sonnet', effort:'medium'})
      .then(d7 => ({...base, dim7:d7}))
  }
)

const clean = out.filter(Boolean)
const c=(v)=>clean.filter(x=>x.dim16&&x.dim16.final_verdict===v).length
const d=(v)=>clean.filter(x=>x.dim7&&x.dim7.verdict===v).length
log(`DONE: dims1-6 REAL ${c('REAL')} / SUSPICIOUS ${c('SUSPICIOUS')} / FABRICATED ${c('FABRICATED')}`
   +(DO_DIM7?` || dim7 SUP ${d('SUPPORTED')} / PART ${d('PARTIAL')} / MIS ${d('MISMATCH')}`:''))

return {
  total: clean.length,
  dim16_summary:{REAL:c('REAL'),SUSPICIOUS:c('SUSPICIOUS'),FABRICATED:c('FABRICATED')},
  dim7_summary: DO_DIM7?{SUPPORTED:d('SUPPORTED'),PARTIAL:d('PARTIAL'),MISMATCH:d('MISMATCH'),UNVERIFIABLE:d('UNVERIFIABLE')}:null,
  // 关键出口：别只看 flagged，author_truncated / venue_not_confirmed / 全部 field_diffs 都要读
  author_truncated: clean.filter(x=>x.dim16&&x.dim16.author_truncated_without_etal)
                         .map(x=>({key:x.key,cited:x.dim16.n_authors_cited,real:x.dim16.n_authors_real})),
  venue_not_confirmed: clean.filter(x=>x.dim16&&!x.dim16.venue_confirmed
                         && x.dim16.venue_statuses.some(s=>s==='preprint_only'||s==='venue_unconfirmed'))
                         .map(x=>({key:x.key,cited_venue:x.cited_venue,statuses:x.dim16.venue_statuses})),
  flagged_dim16: clean.filter(x=>x.dim16&&x.dim16.final_verdict!=='REAL'),
  flagged_dim7:  clean.filter(x=>x.dim7 &&x.dim7.verdict!=='SUPPORTED'),
  all: clean,
}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('outdir', help='stage0.py 的输出目录（含 refs.json / stage0.json）；用 --items 时可传任意占位')
    ap.add_argument('--items', help='直接给预构建的 items JSON（PDF 回退路径用；含 raw/claims 字段）')
    ap.add_argument('-o', '--out', default='run.js')
    ap.add_argument('--keys', help='只审这些 key（逗号分隔）；例如复审时只审新增的')
    ap.add_argument('--level', choices=['quick','standard','full'], default='full',
                    help='quick=只查存在性(≈1 agent/条) | standard=+对抗复核(≈2) | full=+内容一致性(≈3)')
    ap.add_argument('--no-dim7', action='store_true', help='跳过内容一致性（只有 .bib、没正文时用）')
    ap.add_argument('--context', help='正文摘要，写进 dim7 prompt 让判断更准（如"本文提出 X 方法，研究 Y"）',
                    default='(not provided)')
    a = ap.parse_args()

    if a.items:
        items = json.load(open(a.items, encoding='utf-8'))
        for it in items:
            # 归一化：模板读 c.text；允许调用方用 snippet（PDF 路径常见）
            it['claims'] = [{"file": c.get("file", "?"), "text": c.get("text") or c.get("snippet", "")}
                            for c in (it.get('claims') or []) if (c.get("text") or c.get("snippet"))]
        items.sort(key=lambda x: -len(x['claims']))
        do7 = (a.level == 'full') and (not a.no_dim7) and any(i['claims'] for i in items)
        js = (TPL.replace('__DATA__', json.dumps(items, ensure_ascii=False))
                 .replace('__DO_DIM7__', 'true' if do7 else 'false')
                 .replace('__LEVEL__', a.level)
                 .replace('__DIM7_PHASE__', "{ title: 'Dim7', detail: 'content-consistency vs the in-text claim' }," if do7 else '')
                 .replace('__PAPER_CONTEXT__', a.context.replace('`', "'")))
        open(a.out, 'w', encoding='utf-8').write(js)
        n = len(items); n7 = sum(1 for i in items if i['claims'])
        adv = 0 if a.level == 'quick' else n
        est = n + adv + (n7 if do7 else 0)
        print(f"已写出 {a.out}\n  档位 {a.level}；条目 {n}；带上下文 {n7}；dim7 {'开' if do7 else '关'}")
        print(f"  agent 数 ≈ {est}   tokens ≈ {est*15/10:.0f}–{est*30/10:.0f} 万")
        print(f"\n下一步：Workflow({{scriptPath: '{os.path.abspath(a.out)}'}})")
        return

    refs = json.load(open(os.path.join(a.outdir, 'refs.json'), encoding='utf-8'))
    s0 = json.load(open(os.path.join(a.outdir, 'stage0.json'), encoding='utf-8'))
    ctxmap = {}
    cp = os.path.join(a.outdir, 'contexts.json')
    if os.path.exists(cp):
        ctxmap = json.load(open(cp, encoding='utf-8'))

    live = set(s0['cited']) if s0.get('cited') else {e['key'] for e in refs}
    want = set(a.keys.split(',')) if a.keys else live

    items = []
    for e in refs:
        if e['key'] not in want or e['key'] not in live:
            continue
        items.append({
            "key": e['key'], "type": e['type'], "title": e.get('title', ''),
            "author": e.get('author', ''), "year": e.get('year', ''),
            "venue": (e.get('journal') or e.get('booktitle') or e.get('publisher')
                      or e.get('howpublished') or e.get('note') or ''),
            "volume": e.get('volume', ''), "number": e.get('number', ''), "pages": e.get('pages', ''),
            "doi": e.get('doi', ''), "eprint": e.get('eprint', ''), "url": e.get('url', ''),
            "claims": [{"file": c["file"], "text": c["snippet"]} for c in ctxmap.get(e['key'], [])[:3]],
        })
    items.sort(key=lambda x: -len(x['claims']))

    do7 = (a.level == 'full') and (not a.no_dim7) and any(i['claims'] for i in items)
    js = (TPL.replace('__DATA__', json.dumps(items, ensure_ascii=False))
             .replace('__DO_DIM7__', 'true' if do7 else 'false')
             .replace('__LEVEL__', a.level)
             .replace('__DIM7_PHASE__', "{ title: 'Dim7', detail: 'content-consistency vs the in-text claim' }," if do7 else '')
             .replace('__PAPER_CONTEXT__', a.context.replace('`', "'")))
    open(a.out, 'w', encoding='utf-8').write(js)
    n, n7 = len(items), sum(1 for i in items if i['claims'])
    adv = 0 if a.level == 'quick' else n
    est = n + adv + (n7 if do7 else 0)
    tok_lo, tok_hi = est * 15, est * 30          # 千 token；按 4 组实测标定 1.5-3.0 万/agent（大批量有规模效应，偏下限）
    print(f"已写出 {a.out}")
    print(f"  档位 {a.level}；条目 {n} 条；带正文上下文 {n7} 条；dim7 {'开' if do7 else '关'}")
    print(f"\n  ── 工作量与成本估算 ──")
    print(f"  agent 数 ≈ {est}  (stage1 {n}"
          + (f" + 对抗 ≥{adv}" if adv else " + 对抗 0（quick 档只复核可疑项）")
          + (f" + dim7 {n7}" if do7 else "") + ")")
    print(f"  tokens  ≈ {tok_lo/10:.0f}–{tok_hi/10:.0f} 万")
    other = {'quick': ['standard', 'full'], 'standard': ['quick', 'full'], 'full': ['quick', 'standard']}[a.level]
    print(f"  其它档位: " + " | ".join(
        f"{lv}≈{(n + (0 if lv=='quick' else n) + (n7 if lv=='full' and n7 else 0))} agents" for lv in other))
    print(f"\n下一步：Workflow({{scriptPath: '{os.path.abspath(a.out)}'}})")


if __name__ == '__main__':
    main()
