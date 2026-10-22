#!/usr/bin/env python3
"""rds_pi_snapshot.py — chụp tải DB từ Performance Insights API (CHỈ ĐỌC): DB load, top SQL, top wait event.

Lưu ý 2026: console Performance Insights đã EOL ngày 31/07/2026, chuyển sang CloudWatch Database Insights.
API `aws pi` giữ nguyên (script này dùng nó). Execution plan + on-demand analysis chỉ có ở Database
Insights Advanced mode — không có trong script.

Ví dụ:
  python3 rds_pi_snapshot.py --profile my-prod --db-instance my-db --hours 24 --out perf/rds-prod
  python3 rds_pi_snapshot.py --profile my-prod --db-instance my-db --start 2026-10-20T09:00:00Z --end 2026-10-20T12:00:00Z --out x
  python3 rds_pi_snapshot.py ... --dry-run          # in lệnh sẽ chạy, không gọi AWS

Cần: aws cli v2 + quyền rds:DescribeDBInstances, pi:DescribeDimensionKeys, pi:GetResourceMetrics,
pi:GetDimensionKeyDetails (và ec2:DescribeInstanceTypes nếu muốn biết số vCPU).
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

DRY = False


def aws(args, profile, region):
    cmd = ["aws", *args, "--output", "json", "--region", region]
    if profile:
        cmd += ["--profile", profile]
    if DRY:
        print("DRY-RUN:", " ".join(cmd))
        return {}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-400:])
    return json.loads(r.stdout or "{}")


def pct(values, q):
    if not values:
        return None
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[k]


WAIT_HINT = {
    "CPU": "Câu lệnh tốn tính toán: thiếu index, sort/hash lớn, plan tệ.",
    "IO:DataFileRead": "Đọc trang dữ liệu từ đĩa: scan lớn do thiếu index, hoặc RAM không đủ giữ working set.",
    "Lock:transactionid": "Chờ transaction khác commit: ghi tranh chấp, transaction dài, batch chồng giờ cao điểm.",
    "Lock:tuple": "Nhiều phiên sửa cùng dòng.",
    "Lock:relation": "Khoá bảng (DDL, VACUUM FULL, LOCK TABLE).",
    "Client:ClientRead": "DB chờ app gửi lệnh kế: app xử lý chậm giữa các câu lệnh trong transaction, hoặc mạng.",
    "IO:WALWrite": "Ghi WAL nhiều: commit nhỏ, dày.",
    "IO:XactSync": "Chờ flush khi commit: commit quá dày, nên gộp.",
    "LWLock:BufferMapping": "Tranh buffer: đọc lặp nhiều trên bảng nóng.",
}


def main():
    global DRY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db-instance", required=True, help="DBInstanceIdentifier")
    ap.add_argument("--profile", default=os.environ.get("AWS_PROFILE", ""))
    ap.add_argument("--region", default=os.environ.get("AWS_REGION", "ap-northeast-1"))
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--start", help="ISO8601 UTC, vd 2026-10-20T09:00:00Z (ghi đè --hours)")
    ap.add_argument("--end", help="ISO8601 UTC")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    os.makedirs(a.out, exist_ok=True)

    end = datetime.fromisoformat(a.end.replace("Z", "+00:00")) if a.end else datetime.now(timezone.utc)
    start = datetime.fromisoformat(a.start.replace("Z", "+00:00")) if a.start else end - timedelta(hours=a.hours)
    s, e = start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")
    span_h = (end - start).total_seconds() / 3600
    period = 60 if span_h <= 6 else (300 if span_h <= 48 else 3600)

    inst = (aws(["rds", "describe-db-instances", "--db-instance-identifier", a.db_instance], a.profile, a.region)
            .get("DBInstances") or [{}])[0]
    rid = inst.get("DbiResourceId", "db-DRYRUN")
    if not DRY and not inst.get("PerformanceInsightsEnabled"):
        msg = (f"Performance Insights / Database Insights CHƯA bật trên {a.db_instance}. "
               "Bật là thay đổi cấu hình (có chi phí) — cần người phụ trách hạ tầng quyết, script không tự bật.")
        open(os.path.join(a.out, "report.md"), "w").write(f"# RDS snapshot — {a.db_instance}\n\n{msg}\n")
        sys.exit(msg)

    base = ["pi", "--service-type", "RDS", "--identifier", rid, "--start-time", s, "--end-time", e]

    def dims(group):
        return aws(["pi", "describe-dimension-keys", *base[1:], "--metric", "db.load.avg",
                    "--group-by", json.dumps({"Group": group, "Limit": a.top})], a.profile, a.region)

    sql = dims("db.sql_tokenized")
    waits = dims("db.wait_event")
    load = aws(["pi", "get-resource-metrics", *base[1:], "--period-in-seconds", str(period),
                "--metric-queries", json.dumps([{"Metric": "db.load.avg"}])], a.profile, a.region)
    if DRY:
        print("DRY-RUN xong — không gọi AWS.")
        return

    points = [p["Value"] for p in (load.get("MetricList") or [{}])[0].get("DataPoints", []) if "Value" in p]
    avg = sum(points) / len(points) if points else 0

    vcpu = None
    try:
        itype = inst.get("DBInstanceClass", "").replace("db.", "", 1)
        it = aws(["ec2", "describe-instance-types", "--instance-types", itype], a.profile, a.region)
        vcpu = it["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"]
    except Exception:
        pass

    top_sql = []
    for i, k in enumerate(sql.get("Keys", [])):
        d = k.get("Dimensions", {})
        sid, stmt = d.get("db.sql_tokenized.id"), d.get("db.sql_tokenized.statement", "")
        if i < 5 and sid:  # lấy full text cho top 5 (statement trong describe bị cắt)
            try:
                det = aws(["pi", "get-dimension-key-details", "--service-type", "RDS", "--identifier", rid,
                           "--group", "db.sql_tokenized", "--group-identifier", sid,
                           "--requested-dimensions", "statement"], a.profile, a.region)
                full = next((x.get("Value") for x in det.get("Dimensions", []) if x.get("Value")), None)
                stmt = full or stmt
            except Exception:
                pass
        top_sql.append({"id": sid, "load": k.get("Total", 0), "statement": stmt})
    top_waits = [{"name": k.get("Dimensions", {}).get("db.wait_event.name"),
                  "type": k.get("Dimensions", {}).get("db.wait_event.type"),
                  "load": k.get("Total", 0)} for k in waits.get("Keys", [])]
    total = avg or sum(x["load"] for x in top_sql) or 1

    json.dump({"instance": a.db_instance, "class": inst.get("DBInstanceClass"), "engine": inst.get("Engine"),
               "engine_version": inst.get("EngineVersion"), "insights_mode": inst.get("DatabaseInsightsMode"),
               "window": [s, e], "period": period, "load_points": points, "vcpu": vcpu,
               "top_sql": top_sql, "top_waits": top_waits},
              open(os.path.join(a.out, "rds-pi.json"), "w"), ensure_ascii=False, indent=2)

    L = [f"# RDS DB load — {a.db_instance}", "",
         f"- **Window (UTC):** {s} → {e} · period {period}s",
         f"- **Instance:** {inst.get('DBInstanceClass')} · {inst.get('Engine')} {inst.get('EngineVersion')} · "
         f"Database Insights mode: {inst.get('DatabaseInsightsMode') or '-'}",
         f"- **vCPU:** {vcpu or '?'}", "",
         "## DB load (Average Active Sessions)", "",
         "| Avg | P95 | Max | vCPU |", "|---:|---:|---:|---:|",
         f"| {avg:.2f} | {(pct(points, .95) or 0):.2f} | {(max(points) if points else 0):.2f} | {vcpu or '?'} |", "",
         "> AAS vượt số vCPU kéo dài = DB quá tải (phiên phải chờ CPU hoặc I/O).", "",
         "## Top SQL theo DB load", "", "| # | % load | AAS | Statement |", "|---:|---:|---:|---|"]
    for i, q in enumerate(top_sql, 1):
        st = " ".join((q["statement"] or "").split())[:220].replace("|", "\\|")
        L.append(f"| {i} | {q['load'] / total * 100:.1f}% | {q['load']:.3f} | `{st}` |")
    L += ["", "## Top wait events", "", "| Wait | Type | % load | Gợi ý đọc |", "|---|---|---:|---|"]
    for w in top_waits:
        L.append(f"| {w['name']} | {w['type']} | {w['load'] / total * 100:.1f}% | {WAIT_HINT.get(w['name'] or '', '')} |")
    L += ["", "> Câu SQL đầy đủ của từng dòng ở `rds-pi.json`. Bước kế: `EXPLAIN (ANALYZE, BUFFERS)` câu top trên stg "
          "(xem backend-perf playbook §4)."]
    open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
    print(f"Report: {os.path.join(a.out, 'report.md')}")


if __name__ == "__main__":
    main()
