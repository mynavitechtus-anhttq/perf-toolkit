---
name: perf-measure
description: >-
  Measure web page performance with real numbers and write the measurement report — TTFB split into
  network vs server time (curl, warm median/min/p95), PageSpeed Insights / Lighthouse lab score and
  Core Web Vitals plus real-user field data (CrUX p75), median of several runs on mobile and desktop, RDS
  database load with top SQL and wait events (Performance Insights API, now part of CloudWatch Database
  Insights), CloudWatch metrics (RDS, ElastiCache hit rate and evictions, ALB p95/p99, ECS, CloudFront)
  and pg_stat_statements. Three modes: baseline → current-state report (numbers, where the time goes,
  improvement options, expected range with confidence); compare → before/after one change; verify →
  after release. Use for "đo hiện trạng", "report hiện trạng", "đo PSI", "đo TTFB", "lấy số RDS
  performance insight", "check metrics", "so sánh trước sau", or whenever a performance claim needs a number.
---

# perf-measure — đo, rồi mới kết luận

> Luồng, workspace, an toàn, ngân sách: [`../_shared/workflow.md`](../_shared/workflow.md).
> **Prod:** hỏi người dùng trước lần đo đầu mỗi phiên. Không load test lên prod.

## Chọn công cụ theo câu hỏi — không chạy hết cho có

| Câu hỏi | Công cụ | Môi trường |
|---|---|---|
| Server trả byte đầu mất bao lâu? Chậm do mạng hay server? | `measure-ttfb.sh` | prod · stg (`AUTH`) |
| Lúc chưa có cache (người đầu tiên tìm tổ hợp đó) chậm cỡ nào? | `measure-ttfb.sh miss` | prod · stg |
| Điểm PSI + chỉ số lab là bao nhiêu? Mất điểm ở đâu? | `measure_psi.py --engine psi` | prod (URL công khai) |
| Như trên, nhưng môi trường có Basic Auth | `measure_psi.py --engine lighthouse` | stg — chỉ có lab |
| Người dùng thật trải nghiệm thế nào? | `measure_psi.py` (mục Field) | prod — CrUX 28 ngày, p75 |
| DB bận vì câu SQL nào, chờ cái gì? | `rds_pi_snapshot.py` | prod · stg |
| Hạ tầng có nghẽn không (CPU, connection, hit rate, p95)? | `cloudwatch_snapshot.py` | prod · stg |
| Câu SQL nào tốn **tổng** thời gian nhất? | `pg-top-queries.sql` | stg / replica |
| 1 request chạy bao nhiêu query? | code tạm, không commit — [`backend-perf` playbook §2](../backend-perf/references/playbook.md) | local / dev |

## Cách chạy

`$PLUGIN/scripts/…` — xem `workflow.md` §Đường dẫn. Thư mục đo `$RUN` theo mode (`workflow.md` §Workspace): baseline → `$WS/2-baseline/raw-{yyyymmdd}/` · compare → `$WS/5-implement/item{N}-{yyyymmdd}/` · đo tổng trên stg trước release → `$WS/6-testing/results/stg-{yyyymmdd}/` · verify → `$WS/7-delivery/verify-{yyyymmdd}/`.

```bash
# TTFB — before (lưu snapshot) / after (so với snapshot)
BASE_URL=<url> PAGES=$WS/1-scope/pages.tsv PERF_SNAP=$RUN/ttfb.snap REPORT=$RUN/ttfb.md \
  N=20 SLEEP=1 [AUTH="$STG_BASIC_AUTH"] [UTM_CHECK=/some/path] $PLUGIN/scripts/measure-ttfb.sh before

# TTFB khi cache miss — URL chưa ai truy cập trong TTL (tổ hợp hiếm, trang phân trang sâu); mỗi URL chỉ đo được 1 lần
BASE_URL=<url> PAGES=$RUN/fresh.tsv REPORT=$RUN/ttfb-miss.md SLEEP=1 $PLUGIN/scripts/measure-ttfb.sh miss

# PSI — cần PSI_API_KEY (không có key: quota chung, gần như luôn 429)
PSI_API_KEY=… python3 $PLUGIN/scripts/measure_psi.py --base-url <url> --pages $WS/1-scope/pages.tsv \
  --runs 5 --strategy both --out $RUN/psi [--compare <summary.json cũ>]
# stg có Basic Auth → Lighthouse CLI (npx tải gói lighthouse lần đầu; cần Chrome)
BASIC_AUTH="$STG_BASIC_AUTH" python3 $PLUGIN/scripts/measure_psi.py --engine lighthouse ...

# AWS — chỉ đọc. Chưa biết tên tài nguyên → --list. Thử lệnh trước → --dry-run
python3 $PLUGIN/scripts/cloudwatch_snapshot.py --profile <p> --list
python3 $PLUGIN/scripts/rds_pi_snapshot.py --profile <p> --db-instance <id> --hours 24 --out $RUN/rds
python3 $PLUGIN/scripts/cloudwatch_snapshot.py --profile <p> --hours 24 --db-instance <id> \
  --cache-cluster <id> --alb app/<name>/<id> --ecs <cluster>/<service> [--cloudfront <dist>] --out $RUN/cw

# pg_stat_statements — stg / replica
psql "$DATABASE_URL" -v lim=20 -f $PLUGIN/scripts/pg-top-queries.sql > $RUN/pg-top.txt
```

Cảnh báo AWS: console Performance Insights đã EOL 31/07/2026 → CloudWatch Database Insights; API `aws pi` vẫn chạy. Instance chưa bật → script dừng và báo, **không tự bật** (là thay đổi có chi phí).

## Quy tắc đo

- **Before/after:** cùng môi trường, cùng mạng client, cùng khung giờ, chạy sát nhau.
- **Giờ đo:** đặt `REPORT_TZ` theo profile (vd `Asia/Tokyo`) để giờ trong report khớp log của khách; report luôn ghi kèm offset UTC.
- **Cache miss:** cột *1st request* của phase thường **không** chắc là miss (URL có thể vừa có người truy cập). Muốn biết lúc miss chậm cỡ nào → phase `miss` với URL mới, và ghi TTL cache của môi trường vào report.
- **TTFB:** so bằng **warm min** — ít nhiễu mạng/tải nhất. Đọc cột *Server* trước: TTFB cao mà Server nhỏ → nghẽn ở mạng/hạ tầng, tối ưu query là tối ưu nhầm chỗ.
- **PSI:** median **≥ 5 lần**, ghi cả min–max. Điểm lab dao động dù code không đổi.
- **Field (CrUX):** cửa sổ trượt **28 ngày** → sau release phải đợi tới 28 ngày mới phản ánh đủ. Scope `origin` = URL không đủ traffic, số là của cả domain.
- Ghi đủ điều kiện đo vào report (xem `workflow.md` §Nguyên tắc).

## Mode `baseline` → report hiện trạng

Đây là **cổng quyết định** cho khách/lead trước khi team đầu tư điều tra sâu.

1. Bắt buộc: TTFB + PSI cho toàn bộ `pages.tsv`. Thêm RDS + CloudWatch khi cột *Server* vượt ngân sách hoặc nghi DB/hạ tầng.
2. Viết `$WS/2-baseline/report-baseline-{yyyymmdd}.md` theo `$PLUGIN/templates/report-baseline.md`: chỉ số → thời gian mất ở đâu → phương án sơ bộ → mong đợi → cần khách chốt.
3. **Ước lượng "mong đợi" — tính, không đoán:**
   - **Backend:** không thể tiết kiệm nhiều hơn phần *Server* của TTFB. Trong đó phần DB ≈ tỉ trọng top SQL của trang (RDS PI / pg_stat_statements) → đó là **trần** cải thiện.
   - **PSI:** lấy *estimated savings* của từng opportunity → giá trị metric mục tiêu → nhập vào [Lighthouse Scoring Calculator](https://googlechrome.github.io/lighthouse/scorecalc/) ra điểm dự kiến. Ghi thành **khoảng**.
   - **Độ tin cậy:** *cao* = có số đo + đã có tiền lệ (vd task trước) · *TB* = có số đo, chưa thử · *thấp* = suy từ checklist.
4. Ghi rõ trong report: số mong đợi **chốt ở bước điều tra sâu**.

## Mode `compare` (sau mỗi thay đổi)

Chạy lại đúng công cụ đã dùng ở baseline cho thay đổi đó, cùng `pages.tsv`, `--compare` / phase `after`. So với AC của item. Không đạt → chưa sang thay đổi kế.

## Mode `verify` (sau release prod)

TTFB + PSI lab ngay sau release. Field (CrUX): đo lại hằng tuần tới tuần thứ 4, ghi diễn biến. Kết quả → `perf-report`.

## Output

Report của script nằm trong `$RUN`. Report hiện trạng ở `$WS/2-baseline/`. Handoff baseline: đề nghị *"điều tra sâu: `backend-perf` / `psi-improve`?"* theo phần khách đã chốt.
