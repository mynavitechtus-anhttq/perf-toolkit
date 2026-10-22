#!/usr/bin/env python3
"""measure_psi.py — đo điểm PageSpeed Insights / Lighthouse cho danh sách trang, lấy MEDIAN nhiều lần chạy.

Engine:
  psi         Google PageSpeed Insights API. Chỉ URL công khai. Có cả field data (CrUX, p75, 28 ngày).
  lighthouse  Lighthouse CLI qua `npx lighthouse` (cần Chrome). Dùng cho môi trường có Basic Auth (stg/dev).
              Chỉ có lab data.

Ví dụ:
  python3 measure_psi.py --base-url https://example.com --pages pages.tsv --runs 5 --strategy both --out perf/psi-baseline
  python3 measure_psi.py --base-url https://stg.example.com --pages pages.tsv --engine lighthouse --out perf/psi-stg
  python3 measure_psi.py ... --compare perf/psi-baseline/summary.json --out perf/psi-after

Env:
  PSI_API_KEY   khuyên dùng — không có key thì hạn mức API rất thấp
  BASIC_AUTH    user:pass cho engine lighthouse — đọc từ env, KHÔNG ghi vào file

Vì sao median: điểm Lighthouse dao động giữa các lần chạy dù code không đổi; median 5 lần ổn định
khoảng gấp đôi 1 lần (Lighthouse docs/variability.md). Report luôn ghi cả min–max.
"""
import argparse
import base64
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# (audit id trong Lighthouse, tên ngắn, đơn vị)
LAB = [
    ("first-contentful-paint", "FCP", "ms"),
    ("largest-contentful-paint", "LCP", "ms"),
    ("total-blocking-time", "TBT", "ms"),
    ("cumulative-layout-shift", "CLS", ""),
    ("speed-index", "SI", "ms"),
    ("server-response-time", "TTFB", "ms"),
]
# (key trong loadingExperience.metrics, tên ngắn, đơn vị)
FIELD = [
    ("LARGEST_CONTENTFUL_PAINT_MS", "LCP", "ms"),
    ("INTERACTION_TO_NEXT_PAINT", "INP", "ms"),
    ("CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS", ""),
    ("FIRST_CONTENTFUL_PAINT_MS", "FCP", "ms"),
    ("EXPERIMENTAL_TIME_TO_FIRST_BYTE", "TTFB", "ms"),
]
WEIGHTS = {"TBT": 30, "LCP": 25, "CLS": 25, "FCP": 10, "SI": 10}


def read_pages(path):
    pages = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cols = line.split("\t")
            p = cols[0].strip()
            pages.append({
                "path": p,
                "label": (cols[1].strip() if len(cols) > 1 and cols[1].strip() else p),
                "group": (cols[2].strip() if len(cols) > 2 and cols[2].strip() else "all"),
            })
    if not pages:
        sys.exit(f"PAGES không có dòng hợp lệ: {path}")
    return pages


def run_psi(url, strategy, api_key):
    params = {"url": url, "strategy": strategy, "category": "performance"}
    if api_key:
        params["key"] = api_key
    q = PSI_ENDPOINT + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(q, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "ignore")
            try:
                msg = json.loads(raw)["error"]["message"]
            except Exception:
                msg = raw[:200]
            if e.code == 429 and "per day" in msg:
                hint = "" if api_key else " — chưa có PSI_API_KEY nên đang dùng quota chung (gần như luôn cạn). Tạo key, hoặc dùng --engine lighthouse."
                raise RuntimeError(f"PSI 429 hết quota ngày{hint}")
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(15 * attempt)
                continue
            raise RuntimeError(f"PSI HTTP {e.code}: {msg}")
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(10 * attempt)
                continue
            raise RuntimeError(f"PSI network error: {e}")


def run_lighthouse(url, strategy, basic_auth):
    cmd = ["npx", "--yes", "lighthouse", url, "--output=json", "--output-path=stdout", "--quiet",
           "--only-categories=performance", "--chrome-flags=--headless=new --no-sandbox"]
    if strategy == "desktop":
        cmd.append("--preset=desktop")
    hdr_file = None
    if basic_auth:
        token = base64.b64encode(basic_auth.encode()).decode()
        hdr_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"Authorization": f"Basic {token}"}, hdr_file)
        hdr_file.close()
        cmd.append(f"--extra-headers={hdr_file.name}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"lighthouse exit {r.returncode}: {r.stderr[-400:]}")
        return {"lighthouseResult": json.loads(r.stdout)}
    finally:
        if hdr_file:
            os.unlink(hdr_file.name)


def first_node_label(obj):
    """Tìm node đầu tiên (LCP element / layout shift element) trong details — cấu trúc đổi theo version LH."""
    if isinstance(obj, dict):
        node = obj.get("node")
        if isinstance(node, dict):
            return node.get("nodeLabel") or node.get("snippet") or node.get("selector")
        for v in obj.values():
            hit = first_node_label(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = first_node_label(v)
            if hit:
                return hit
    return None


def lcp_phases(audits):
    """LCP subparts (TTFB / load delay / load duration / render delay) — best-effort theo id audit."""
    for aid, a in audits.items():
        if "lcp" in aid and ("phase" in aid or "breakdown" in aid):
            items = ((a.get("details") or {}).get("items")) or []
            out = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                label = next((v for k, v in it.items() if isinstance(v, str) and k != "node"), None)
                val = next((v for k, v in it.items() if isinstance(v, (int, float))), None)
                if label and val is not None:
                    out.append((label, round(val)))
            if out:
                return out
    return []


def third_parties(audits, top=5):
    items = ((audits.get("third-party-summary") or {}).get("details") or {}).get("items") or []
    rows = []
    for it in items:
        ent = it.get("entity")
        name = ent.get("text") if isinstance(ent, dict) else (ent or "?")
        rows.append({"entity": name, "blocking_ms": round(it.get("blockingTime") or 0),
                     "main_thread_ms": round(it.get("mainThreadTime") or 0),
                     "transfer_kb": round((it.get("transferSize") or 0) / 1024)})
    rows.sort(key=lambda r: (r["blocking_ms"], r["main_thread_ms"]), reverse=True)
    return rows[:top]


def opportunities(audits, top=8):
    rows = []
    for aid, a in audits.items():
        score = a.get("score")
        if score is None or score >= 0.9:
            continue
        ms = a.get("metricSavings") or {}
        det = a.get("details") or {}
        lcp_fcp = max(ms.get("LCP") or 0, ms.get("FCP") or 0, det.get("overallSavingsMs") or 0)
        tbt = ms.get("TBT") or 0
        cls = ms.get("CLS") or 0
        if lcp_fcp <= 0 and tbt <= 0 and cls <= 0:
            continue
        rows.append({"id": aid, "title": a.get("title", aid), "lcp_fcp_ms": round(lcp_fcp),
                     "tbt_ms": round(tbt), "cls": round(cls, 3)})
    rows.sort(key=lambda r: (r["lcp_fcp_ms"] + r["tbt_ms"] + r["cls"] * 1000), reverse=True)
    return rows[:top]


def extract(data):
    lhr = data["lighthouseResult"]
    audits = lhr.get("audits", {})
    perf = (lhr.get("categories", {}).get("performance") or {}).get("score")
    lab = {}
    for aid, key, _ in LAB:
        v = (audits.get(aid) or {}).get("numericValue")
        if v is not None:
            lab[key] = round(v, 3) if key == "CLS" else round(v)
    field, scope = {}, None
    le = data.get("loadingExperience") or {}
    if le.get("metrics"):
        scope = "origin" if le.get("origin_fallback") else "url"
        for k, key, _ in FIELD:
            m = le["metrics"].get(k)
            if m and "percentile" in m:
                p = m["percentile"]
                field[key] = round(p / 100, 3) if key == "CLS" else p
                field[key + "_cat"] = m.get("category")
        field["overall"] = le.get("overall_category")
    return {
        "score": round(perf * 100) if perf is not None else None,
        "lab": lab, "field": field, "field_scope": scope,
        "lh_version": lhr.get("lighthouseVersion"),
        "lcp_element": first_node_label((audits.get("largest-contentful-paint-element") or {}).get("details")),
        "cls_element": first_node_label((audits.get("layout-shifts") or audits.get("layout-shift-elements") or {}).get("details")),
        "lcp_phases": lcp_phases(audits),
        "third_party": third_parties(audits),
        "opportunities": opportunities(audits),
    }


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:60] or "root"


def fmt(v, key=""):
    if v is None or v == "":
        return "-"
    if key == "CLS":
        return f"{v:.3f}"
    if isinstance(v, (int, float)):
        return f"{v / 1000:.2f}s" if v >= 1000 else f"{int(v)}ms"
    return str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--strategy", choices=["mobile", "desktop", "both"], default="mobile")
    ap.add_argument("--engine", choices=["psi", "lighthouse"], default="psi")
    ap.add_argument("--out", required=True, help="thư mục output (summary.json, raw/, report.md)")
    ap.add_argument("--compare", help="summary.json của lần đo trước để so sánh")
    ap.add_argument("--title", default="Page performance")
    ap.add_argument("--pause", type=float, default=2.0, help="nghỉ giữa các lần gọi (giây)")
    a = ap.parse_args()

    base = a.base_url.rstrip("/")
    pages = read_pages(a.pages)
    strategies = ["mobile", "desktop"] if a.strategy == "both" else [a.strategy]
    api_key = os.environ.get("PSI_API_KEY", "")
    basic = os.environ.get("BASIC_AUTH", "")
    os.makedirs(os.path.join(a.out, "raw"), exist_ok=True)
    if a.engine == "psi" and not api_key:
        print("! Không có PSI_API_KEY — hạn mức API thấp, dễ bị 429. Nên tạo key (Google Cloud Console).", file=sys.stderr)

    results, errors = [], []
    for pg in pages:
        url = base + pg["path"]
        for strat in strategies:
            runs = []
            for n in range(1, a.runs + 1):
                print(f"[{a.engine}] {strat:7} run {n}/{a.runs} {url}", file=sys.stderr)
                try:
                    raw = run_psi(url, strat, api_key) if a.engine == "psi" else run_lighthouse(url, strat, basic)
                    runs.append((extract(raw), raw))
                except Exception as e:  # ghi lỗi, đo tiếp trang khác
                    errors.append(f"{pg['path']} [{strat}] run {n}: {e}")
                time.sleep(a.pause)
            ok = [r for r in runs if r[0]["score"] is not None]
            if not ok:
                results.append({**pg, "strategy": strat, "runs_ok": 0})
                continue
            scores = [r[0]["score"] for r in ok]
            med = statistics.median_low(scores)
            rep_ex, rep_raw = next(r for r in ok if r[0]["score"] == med)  # run đại diện = run có điểm median
            with open(os.path.join(a.out, "raw", f"{slug(pg['path'])}-{strat}.json"), "w") as f:
                json.dump(rep_raw.get("lighthouseResult", rep_raw), f)
            lab_med = {}
            for _, key, _ in LAB:
                vals = [r[0]["lab"][key] for r in ok if key in r[0]["lab"]]
                if vals:
                    lab_med[key] = statistics.median(vals)
            results.append({**pg, "strategy": strat, "runs_ok": len(ok),
                            "score_median": med, "score_min": min(scores), "score_max": max(scores),
                            "lab": lab_med, "field": rep_ex["field"], "field_scope": rep_ex["field_scope"],
                            "lh_version": rep_ex["lh_version"], "lcp_element": rep_ex["lcp_element"],
                            "cls_element": rep_ex["cls_element"], "lcp_phases": rep_ex["lcp_phases"],
                            "third_party": rep_ex["third_party"], "opportunities": rep_ex["opportunities"]})

    summary = {"meta": {"base_url": base, "engine": a.engine, "runs": a.runs, "strategies": strategies,
                        "measured_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "basic_auth": bool(basic) if a.engine == "lighthouse" else False},
               "pages": results, "errors": errors}
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    before = None
    if a.compare:
        with open(a.compare) as f:
            before = {(p["path"], p["strategy"]): p for p in json.load(f)["pages"]}

    L = [f"# {a.title} — PageSpeed / Lighthouse", "",
         f"- **Target:** {base}",
         f"- **Engine:** {a.engine} · **Runs:** {a.runs} per page per device · **Aggregation:** median (min–max shown)",
         f"- **Measured at:** {summary['meta']['measured_at']} · **Devices:** {', '.join(strategies)}",
         f"- **Lighthouse:** {next((r.get('lh_version') for r in results if r.get('lh_version')), '-')}",
         "- Score weights: TBT 30% · LCP 25% · CLS 25% · FCP 10% · SI 10%. Lab score varies run to run — compare medians, not single runs.",
         ""]
    for strat in strategies:
        L += [f"## Lab — {strat}", "",
              "| Page | Group | Score (min–max) | FCP | LCP | TBT | CLS | SI | TTFB |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in [x for x in results if x["strategy"] == strat]:
            if not r.get("runs_ok"):
                L.append(f"| {r['label']} | {r['group']} | failed | - | - | - | - | - | - |")
                continue
            lab = r["lab"]
            L.append(f"| {r['label']} | {r['group']} | **{r['score_median']}** ({r['score_min']}–{r['score_max']}) | "
                     + " | ".join(fmt(lab.get(k), k) for k in ["FCP", "LCP", "TBT", "CLS", "SI", "TTFB"]) + " |")
        L.append("")

    if a.engine == "psi":
        L += ["## Field — real users (CrUX, p75, rolling 28 days)", "",
              "| Page | Device | Scope | LCP | INP | CLS | FCP | TTFB | Overall |",
              "|---|---|---|---:|---:|---:|---:|---:|---|"]
        for r in results:
            f_ = r.get("field") or {}
            if not f_:
                L.append(f"| {r['label']} | {r['strategy']} | no data | - | - | - | - | - | - |")
                continue
            L.append(f"| {r['label']} | {r['strategy']} | {r.get('field_scope')} | "
                     + " | ".join(fmt(f_.get(k), k) for k in ["LCP", "INP", "CLS", "FCP", "TTFB"])
                     + f" | {f_.get('overall') or '-'} |")
        L += ["", "> Scope `origin` = không đủ traffic cho URL này, CrUX trả số của cả domain.", ""]

    if before:
        L += ["## Before → After (median)", "",
              "| Page | Device | Score | LCP | TBT | CLS |", "|---|---|---:|---:|---:|---:|"]
        for r in results:
            b = before.get((r["path"], r["strategy"]))
            if not b or not r.get("runs_ok") or not b.get("runs_ok"):
                continue

            def d(k):
                bv, av = b["lab"].get(k), r["lab"].get(k)
                if bv is None or av is None:
                    return "-"
                return f"{fmt(bv, k)} → {fmt(av, k)}"
            L.append(f"| {r['label']} | {r['strategy']} | {b['score_median']} → **{r['score_median']}** "
                     f"({r['score_median'] - b['score_median']:+d}) | {d('LCP')} | {d('TBT')} | {d('CLS')} |")
        L.append("")

    L += ["## Where points are lost (representative run)", ""]
    for r in results:
        if not r.get("runs_ok"):
            continue
        L += [f"### {r['label']} — {r['strategy']}", "",
              f"- LCP element: `{(r.get('lcp_element') or '-')[:120]}`",
              f"- Largest layout shift: `{(r.get('cls_element') or '-')[:120]}`"]
        if r.get("lcp_phases"):
            L.append("- LCP subparts: " + " · ".join(f"{k} {v}ms" for k, v in r["lcp_phases"]))
        if r.get("third_party"):
            L.append("- Third-party (blocking): " + " · ".join(
                f"{t['entity']} {t['blocking_ms']}ms" for t in r["third_party"]))
        if r.get("opportunities"):
            L += ["", "| Opportunity | Est. LCP/FCP saving | Est. TBT saving | CLS |", "|---|---:|---:|---:|"]
            for o in r["opportunities"]:
                L.append(f"| {o['title']} | {o['lcp_fcp_ms']}ms | {o['tbt_ms']}ms | {o['cls']} |")
        L.append("")

    L += ["## Measurement Warnings", ""] + ([f"- {e}" for e in errors] or ["- None"])
    with open(os.path.join(a.out, "report.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"Report: {os.path.join(a.out, 'report.md')}  ·  summary: {os.path.join(a.out, 'summary.json')}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} lỗi — xem mục Measurement Warnings", file=sys.stderr)


if __name__ == "__main__":
    main()
