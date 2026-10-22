#!/usr/bin/env python3
"""cloudwatch_snapshot.py — chụp chỉ số hạ tầng từ CloudWatch (CHỈ ĐỌC) trong một khung giờ.

Phủ: RDS (CPU, connection, IOPS, latency, RAM trống) · ElastiCache (CPU, hit rate, eviction, connection)
     · ALB (TargetResponseTime p50/p95/p99, request, 5xx) · ECS service (CPU, RAM) · CloudFront (request,
     cache hit rate, origin latency — 2 chỉ số sau cần bật "additional metrics").

Ví dụ:
  python3 cloudwatch_snapshot.py --profile my-prod --list                      # dò tên tài nguyên
  python3 cloudwatch_snapshot.py --profile my-prod --hours 24 \
      --db-instance my-db --cache-cluster my-redis-001 --alb app/my-alb/abc123 \
      --ecs my-cluster/my-web-service --cloudfront E123ABC --out perf/cw-prod
  python3 cloudwatch_snapshot.py ... --dry-run                                 # in query, không gọi AWS
  python3 cloudwatch_snapshot.py --profile my-prod --start 2026-07-01T00:00:00Z \
      --alb app/my-alb/abc123 --db-cluster my-aurora --series day --out perf/cw-trend   # xu hướng theo ngày
  Aurora: --db-cluster <cluster> lấy chỉ số gộp theo vai trò READER / WRITER (replica autoscale vẫn tính).
  --series hour|day: thêm series.md — bảng theo giờ / ngày để tìm "bắt đầu chậm từ lúc nào".
  Giờ trong series.md theo env REPORT_TZ (vd Asia/Tokyo), mặc định giờ máy.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

DRY = False


def aws(args, profile, region):
    cmd = ["aws", *args, "--output", "json", "--region", region]
    if profile:
        cmd += ["--profile", profile]
    if DRY:
        print("DRY-RUN:", " ".join(cmd))
        return {}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-400:])
    return json.loads(r.stdout or "{}")


# (metric, stat, đơn vị hiển thị, hệ số đổi, ghi chú ngưỡng)
RDS = [("CPUUtilization", "Average", "%", 1, "> 70% kéo dài: CPU nghẽn"),
       ("DatabaseConnections", "Maximum", "", 1, "so với max_connections (< 70%)"),
       ("FreeableMemory", "Minimum", "MB", 1 / 1048576, "thấp dần → thiếu RAM cache dữ liệu"),
       ("ReadIOPS", "Average", "", 1, ""), ("WriteIOPS", "Average", "", 1, ""),
       ("ReadLatency", "Average", "ms", 1000, "> 10ms: I/O chậm"),
       ("WriteLatency", "Average", "ms", 1000, ""), ("DiskQueueDepth", "Average", "", 1, "> 1 kéo dài: hàng đợi I/O")]
AURORA_ROLE = [("CPUUtilization", "Average", "%", 1, "> 70% kéo dài: CPU nghẽn"),
               ("CPUUtilization", "Maximum", "%", 1, "chạm ~100%: hết CPU"),
               ("DatabaseConnections", "Maximum", "", 1, ""),
               ("BufferCacheHitRatio", "Average", "%", 1, "< 99%: đọc đĩa nhiều"),
               ("ReadIOPS", "Average", "", 1, "")]
REDIS = [("EngineCPUUtilization", "Average", "%", 1, "> 80%: Redis nghẽn (đơn luồng)"),
         ("CPUUtilization", "Average", "%", 1, ""), ("CacheHits", "Sum", "", 1, ""),
         ("CacheMisses", "Sum", "", 1, ""), ("CurrConnections", "Maximum", "", 1, ""),
         ("Evictions", "Sum", "", 1, "> 0: hết RAM, key bị đẩy ra"),
         ("DatabaseMemoryUsagePercentage", "Maximum", "%", 1, "")]
ALB = [("TargetResponseTime", "p50", "ms", 1000, ""), ("TargetResponseTime", "p95", "ms", 1000, "so với ngân sách server"),
       ("TargetResponseTime", "p99", "ms", 1000, ""), ("RequestCount", "Sum", "", 1, ""),
       ("HTTPCode_Target_5XX_Count", "Sum", "", 1, ""), ("HTTPCode_ELB_5XX_Count", "Sum", "", 1, "")]
ECS = [("CPUUtilization", "Average", "%", 1, ""), ("CPUUtilization", "Maximum", "%", 1, "chạm 100%: thiếu CPU"),
       ("MemoryUtilization", "Average", "%", 1, ""), ("MemoryUtilization", "Maximum", "%", 1, "")]
CF = [("Requests", "Sum", "", 1, ""), ("CacheHitRate", "Average", "%", 1, "cần bật additional metrics"),
      ("OriginLatency", "p95", "ms", 1, "cần bật additional metrics"),
      ("5xxErrorRate", "Average", "%", 1, ""), ("TotalErrorRate", "Average", "%", 1, "")]


def build(resources):
    """-> list[(id, namespace, metric, dims, stat, unit, factor, note, resource_label)]"""
    out = []
    for kind, ns, mdefs, dimf in resources:
        for label, dimlist in dimf:
            for metric, stat, unit, factor, note in mdefs:
                qid = "q" + re.sub(r"[^a-z0-9]", "", (kind + label + metric + stat).lower())[:200] + str(len(out))
                out.append((qid, ns, metric, dimlist, stat, unit, factor, note, f"{kind}: {label}"))
    return out


def fetch(queries, start, end, period, profile, region):
    q = [{"Id": qid, "ReturnData": True,
          "MetricStat": {"Metric": {"Namespace": ns, "MetricName": m,
                                    "Dimensions": [{"Name": k, "Value": v} for k, v in dims]},
                         "Period": period, "Stat": stat}}
         for qid, ns, m, dims, stat, *_ in queries]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(q, f)
        path = f.name
    try:
        data, token = {}, None
        while True:
            args = ["cloudwatch", "get-metric-data", "--metric-data-queries", f"file://{path}",
                    "--start-time", start, "--end-time", end]
            if token:
                args += ["--next-token", token]
            r = aws(args, profile, region)
            for res in r.get("MetricDataResults", []):
                data.setdefault(res["Id"], []).extend(zip(res.get("Timestamps", []), res.get("Values", [])))
            token = r.get("NextToken")
            if not token or DRY:
                break
        return data
    finally:
        os.unlink(path)


def stats(vals):
    if not vals:
        return None
    s = sorted(vals)
    return {"avg": sum(s) / len(s), "p95": s[max(0, int(round(.95 * (len(s) - 1))))], "max": s[-1], "sum": sum(s)}


def list_resources(profile, region):
    print("## RDS")
    for d in aws(["rds", "describe-db-instances"], profile, region).get("DBInstances", []):
        print(f"- {d['DBInstanceIdentifier']}  ({d['DBInstanceClass']}, {d['Engine']} {d['EngineVersion']})")
    print("## ElastiCache (CacheClusterId)")
    for c in aws(["elasticache", "describe-cache-clusters"], profile, region).get("CacheClusters", []):
        print(f"- {c['CacheClusterId']}  ({c.get('CacheNodeType')}, {c.get('Engine')})")
    print("## ALB (giá trị dimension LoadBalancer)")
    for lb in aws(["elbv2", "describe-load-balancers"], profile, region).get("LoadBalancers", []):
        arn = lb["LoadBalancerArn"]
        print(f"- {arn.split('loadbalancer/', 1)[-1]}  ({lb.get('Type')}, {lb.get('DNSName')})")
    print("## ECS (cluster/service)")
    for carn in aws(["ecs", "list-clusters"], profile, region).get("clusterArns", []):
        cname = carn.split("/")[-1]
        for sarn in aws(["ecs", "list-services", "--cluster", cname], profile, region).get("serviceArns", []):
            print(f"- {cname}/{sarn.split('/')[-1]}")
    print("## CloudFront (Id — metric ở us-east-1)")
    items = ((aws(["cloudfront", "list-distributions"], profile, "us-east-1").get("DistributionList") or {})
             .get("Items") or [])
    for d in items:
        print(f"- {d['Id']}  ({', '.join((d.get('Aliases') or {}).get('Items') or [d.get('DomainName')])})")


def main():
    global DRY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=os.environ.get("AWS_PROFILE", ""))
    ap.add_argument("--region", default=os.environ.get("AWS_REGION", "ap-northeast-1"))
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--period", type=int, default=300)
    ap.add_argument("--db-instance", action="append", default=[])
    ap.add_argument("--db-cluster", action="append", default=[], help="Aurora DBClusterIdentifier (READER + WRITER)")
    ap.add_argument("--series", choices=["hour", "day"], help="thêm series.md theo giờ / ngày (đặt luôn --period)")
    ap.add_argument("--cache-cluster", action="append", default=[])
    ap.add_argument("--alb", action="append", default=[], help="app/<name>/<id>")
    ap.add_argument("--ecs", action="append", default=[], help="<cluster>/<service>")
    ap.add_argument("--cloudfront", action="append", default=[], help="Distribution Id")
    ap.add_argument("--out")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    if a.series:
        a.period = 3600 if a.series == "hour" else 86400

    if a.list:
        list_resources(a.profile, a.region)
        return
    if not a.out:
        sys.exit("--out bắt buộc (hoặc dùng --list)")
    os.makedirs(a.out, exist_ok=True)

    end = datetime.fromisoformat(a.end.replace("Z", "+00:00")) if a.end else datetime.now(timezone.utc)
    start = datetime.fromisoformat(a.start.replace("Z", "+00:00")) if a.start else end - timedelta(hours=a.hours)
    s, e = start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")

    regional = build([
        ("RDS", "AWS/RDS", RDS, [(x, [("DBInstanceIdentifier", x)]) for x in a.db_instance]),
        ("Aurora", "AWS/RDS", AURORA_ROLE, [(f"{x} {role}", [("DBClusterIdentifier", x), ("Role", role)])
                                            for x in a.db_cluster for role in ("READER", "WRITER")]),
        ("ElastiCache", "AWS/ElastiCache", REDIS, [(x, [("CacheClusterId", x)]) for x in a.cache_cluster]),
        ("ALB", "AWS/ApplicationELB", ALB, [(x, [("LoadBalancer", x)]) for x in a.alb]),
        ("ECS", "AWS/ECS", ECS, [(x, [("ClusterName", x.split("/")[0]), ("ServiceName", x.split("/")[-1])])
                                 for x in a.ecs]),
    ])
    global_q = build([("CloudFront", "AWS/CloudFront", CF,
                       [(x, [("DistributionId", x), ("Region", "Global")]) for x in a.cloudfront])])
    if not regional and not global_q:
        sys.exit("Chưa chỉ định tài nguyên nào. Dùng --list để dò tên.")

    data = {}
    if regional:
        data.update(fetch(regional, s, e, a.period, a.profile, a.region))
    if global_q:
        data.update(fetch(global_q, s, e, a.period, a.profile, "us-east-1"))
    if DRY:
        print("DRY-RUN xong — không gọi AWS.")
        return

    L = [f"# Infra snapshot (CloudWatch)", "", f"- **Window (UTC):** {s} → {e} · period {a.period}s", ""]
    raw = {}
    current = None
    hits = {}
    for qid, ns, metric, dims, stat, unit, factor, note, res in regional + global_q:
        st = stats([v * factor for _, v in data.get(qid, [])])
        raw[f"{res} {metric} {stat}"] = st
        if res != current:
            if current and current in hits:
                h, m = hits[current]
                if h is not None and m is not None and (h + m) > 0:
                    L += ["", f"**Cache hit rate:** {h / (h + m) * 100:.1f}%  (< 80% → xem key có ổn định không, TTL có quá ngắn)"]
            current = res
            L += ["", f"## {res}", "", "| Metric | Stat | Avg | P95 | Max | Sum | Ghi chú |", "|---|---|---:|---:|---:|---:|---|"]
        if metric in ("CacheHits", "CacheMisses") and st:
            h, m = hits.get(res, (None, None))
            hits[res] = (st["sum"], m) if metric == "CacheHits" else (h, st["sum"])
        if not st:
            L.append(f"| {metric} | {stat} | no data | | | | {note} |")
            continue
        u = f" {unit}" if unit else ""
        total = f"{st['sum']:.0f}" if stat == "Sum" else ""
        L.append(f"| {metric} | {stat} | {st['avg']:.1f}{u} | {st['p95']:.1f}{u} | {st['max']:.1f}{u} | "
                 f"{total} | {note} |")
    if current in hits:
        h, m = hits[current]
        if h is not None and m is not None and (h + m) > 0:
            L += ["", f"**Cache hit rate:** {h / (h + m) * 100:.1f}%"]
    json.dump(raw, open(os.path.join(a.out, "cloudwatch.json"), "w"), ensure_ascii=False, indent=2)
    open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
    print(f"Report: {os.path.join(a.out, 'report.md')}")
    if a.series:
        path = os.path.join(a.out, "series.md")
        open(path, "w").write(series_md(regional + global_q, data, a.series, s, e))
        print(f"Series: {path}")


def series_md(queries, data, unit, s, e):
    """Một bảng / tài nguyên: hàng = giờ hoặc ngày (theo REPORT_TZ), cột = metric."""
    tzname = os.environ.get("REPORT_TZ", "")
    if tzname:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tzname)
    else:
        tz = datetime.now().astimezone().tzinfo
    fmt = "%Y-%m-%d %H:00" if unit == "hour" else "%Y-%m-%d"
    L = ["# Infra series (CloudWatch)", "",
         f"- **Window (UTC):** {s} → {e} · mỗi hàng 1 {'giờ' if unit == 'hour' else 'ngày'} · giờ hiển thị: {tzname or 'giờ máy'}",
         "- Ngày theo UTC khi `--series day` (CloudWatch gom theo mốc UTC).", ""]
    by_res = {}
    for qid, ns, metric, dims, stat, u, factor, note, res in queries:
        by_res.setdefault(res, []).append((f"{metric} {stat}" + (f" ({u})" if u else ""), qid, factor))
    for res, cols in by_res.items():
        rows = {}
        for i, (_, qid, factor) in enumerate(cols):
            for ts, v in data.get(qid, []):
                rows.setdefault(ts, [None] * len(cols))[i] = v * factor
        L += [f"## {res}", "", "| Thời điểm | " + " | ".join(c[0] for c in cols) + " |",
              "|---|" + "---:|" * len(cols)]
        for ts in sorted(rows):
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            label = t.strftime(fmt) if unit == "day" else t.astimezone(tz).strftime(fmt)
            L.append(f"| {label} | " + " | ".join("" if v is None else f"{v:,.1f}" for v in rows[ts]) + " |")
        L.append("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
