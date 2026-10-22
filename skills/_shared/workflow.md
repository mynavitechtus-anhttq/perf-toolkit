# perf-toolkit — luồng, quy ước, an toàn (nguồn duy nhất)

Mọi skill trong plugin trỏ về file này. Đừng chép lại nội dung ở skill khác.

## Luồng 7 bước

| # | Bước | Skill | Output | Cổng |
|---|---|---|---|---|
| 1 | Phạm vi | `perf-scope` | `1-scope/` scope.md · pages.tsv · câu hỏi chốt với khách | Khách chốt trang · thiết bị · chỉ số · mục tiêu |
| 2 | Đo hiện trạng | `perf-measure` (baseline) · `infra-check` khi Server cao | `2-baseline/` report-baseline · infra · raw số đo | **Cổng quyết định** — khách/lead duyệt có làm tiếp không, làm phần nào |
| 3 | Điều tra sâu | `backend-perf` · `psi-improve` (điều tra) | `3-investigate/` report-backend · report-psi | Lead duyệt hướng xử lý |
| 4 | Test + kế hoạch | `perf-test-plan` · `planning` | `4-plan/` plan · wbs-schedule · `6-testing/` test-plan · checklist · test case | Khách duyệt lịch |
| 5 | Implement | `backend-perf` · `psi-improve` (implement) + `perf-measure` (compare) | code + `5-implement/` số trước/sau từng item | Mỗi thay đổi đạt AC mới làm thay đổi kế |
| 6 | Kiểm thử | tester chạy checklist + test case · `perf-measure` (compare) trên stg | `6-testing/results/stg-*` | Test PASS + đạt AC trên stg mới release |
| 7 | Nghiệm thu | `perf-measure` (verify) · `perf-report` | `7-delivery/` report-final ja · vn-en · số verify | Khách nghiệm thu |

Thiếu output của bước trước → chạy bước trước, không đoán bù.

**Vì sao báo cáo hiện trạng đứng trước điều tra sâu:** khách cần biết *đang ở đâu, cải thiện được cỡ nào* để quyết có đầu tư không, trước khi team tốn công đọc code. Nhưng con số "mong đợi" ở bước 2 chỉ là **khoảng ước lượng** từ dữ liệu đo — bước 3 mới chốt. Report bước 2 phải ghi rõ độ tin cậy, không thì khách cầm số sớm làm cam kết.

## Workspace

```
tasks/{TICKET}/perf/                 # = $WS
├── 1-scope/        scope.md · pages.tsv
├── 2-baseline/     report-baseline-{yyyymmdd}.md · infra-{yyyymmdd}.md · raw-{yyyymmdd}/
├── 3-investigate/  report-backend-{yyyymmdd}.md · report-psi-{yyyymmdd}.md
├── 4-plan/         plan.md · wbs-schedule.md
├── 5-implement/    item{N}-{yyyymmdd}/            # số trước/sau của từng item trong plan.md
├── 6-testing/                                     # test-plan viết ở bước 4, kết quả item ghi ở bước 5
│   ├── test-plan.md                               # ma trận item × loại test (perf-test-plan)
│   ├── checklist-{smoke|regression}.md            # checklist cho tester
│   ├── testcases/                                 # test case từ ai-qc-framework
│   └── results/{item{N}|stg|prod}-{yyyymmdd}/     # kết quả chạy: parity diff · ảnh visual · tracking · checklist đã tick · số đo stg
└── 7-delivery/     report-final-{ja|vn-en}-{yyyymmdd}.md · verify-{yyyymmdd}/
```

- Thư mục đo (`raw-*`, `item*`, `verify-*`) cùng một kiểu bên trong: `ttfb.md` · `ttfb.snap` · `psi/` · `rds/` · `cw/` · `pg-top.txt` — có gì đo thì có nấy.
- Số đo thô nằm **cạnh report dùng nó**, không gom chung một chỗ.
- Đo lại → thư mục / file **ngày mới**, không ghi đè bản cũ.

Không có ticket → hỏi 1 câu, hoặc dùng `tasks/PERF-{yyyymmdd}/perf/`.

## Đường dẫn

- `$PLUGIN` = thư mục gốc plugin = **2 cấp trên** thư mục skill (đường dẫn skill hiện khi skill được nạp). Script: `$PLUGIN/scripts/`, template: `$PLUGIN/templates/`.
- Script chạy từ plugin, **không copy vào repo dự án**.

## Profile dự án

Thứ tự tìm: `<repo>/.claude/perf-toolkit.md` → `$PLUGIN/profiles/<project>.md` → hỏi người dùng.
Profile chứa: knowledge base (repo + đường dẫn spec) · môi trường (URL, có Basic Auth không) · stack · tài nguyên AWS · gotcha đã biết · bài học dự án trước. Chưa có profile → tạo từ `$PLUGIN/profiles/kaigo.md` làm mẫu, điền `TBD` chỗ chưa biết.

## Nguyên tắc

- **Đo trước, sửa sau.** "Chắc chỗ này chậm" không phải phát hiện.
- **Mọi con số kèm điều kiện đo:** môi trường · thời điểm · số lần · engine/công cụ · thiết bị · cache nóng/lạnh · lượng dữ liệu.
- **Số cho khách lấy từ prod (hoặc stg).** Local khác máy, khác dữ liệu, không qua CDN — chỉ dùng để so *tương đối* trước/sau một thay đổi code.
- **Một thay đổi → một lần đo.** Gộp rồi đo thì không biết cái nào có tác dụng.
- **Ai nghĩ, ai gõ:** chọn hướng, chốt kết luận, quyết đánh đổi là của người phụ trách. AI đo, grep, soạn nháp theo template; người soát từng dòng.
- Claim chưa kiểm → `[Giả định — cách verify: …]`. Không có claim trần.

## An toàn (cứng)

- **AWS:** chỉ lệnh đọc (describe / get / list). Không đổi parameter group, không bật/tắt tính năng, không tạo tài nguyên.
- **Prod:** hỏi người dùng trước lần đo đầu tiên mỗi phiên. Đo tuần tự, `N ≤ 20`, `SLEEP=1`, ngoài giờ cao điểm. **Không load test (k6/ab/JMeter) lên prod.**
- **DB:** chỉ `SELECT` / `EXPLAIN`. `EXPLAIN ANALYZE` *thực thi* câu lệnh → câu ghi phải bọc `BEGIN; … ROLLBACK;`. Chạy trên stg hoặc replica; prod primary chỉ khi được duyệt. `CREATE EXTENSION`, tạo/xoá index, `ANALYZE`, `VACUUM` = thay đổi → không tự làm.
- **Bí mật** (Basic Auth, PSI API key, AWS profile): đọc từ env, không ghi vào file, không in ra report, không đặt trong URL.
- **Thay đổi tag bên thứ ba** (GTM, quảng cáo, analytics): cần người phụ trách marketing phía khách duyệt — mất tracking conversion là sự cố lớn hơn điểm PSI thấp.

## Ngân sách mặc định

Dự án có số riêng (SLA, mục tiêu khách chốt) → dùng số dự án, ghi nguồn. Không có → dùng bảng này và nói rõ là mốc chung.

| Chỉ số | Tốt | Kém | Ghi chú |
|---|---|---|---|
| LCP | ≤ 2.5s | > 4.0s | field p75 |
| INP | ≤ 200ms | > 500ms | field p75 — lab không đo được, TBT là đại diện |
| CLS | ≤ 0.1 | > 0.25 | |
| TBT | ≤ 200ms | > 600ms | lab, mobile |
| FCP | ≤ 1.8s | > 3.0s | |
| TTFB | ≤ 800ms | > 1.8s | |
| Server think time | < 200ms | | phần TTFB thuộc backend |
| JS initial | < 200KB gzip | | |
| DB connection | < 70% `max_connections` | | |

**Điểm PSI (Lighthouse 10+) gồm 5 chỉ số lab có trọng số:** TBT 30% · LCP 25% · CLS 25% · FCP 10% · SI 10%. → 80% điểm nằm ở TBT + LCP + CLS.

## Công cụ

| Script | Đo gì |
|---|---|
| `measure-ttfb.sh` | TTFB warm median/min/p95 + tách server / mạng; before/after |
| `measure_psi.py` | điểm + chỉ số lab (median N lần), field CrUX, phần tử LCP, subpart LCP, bên thứ ba, opportunities; before/after |
| `rds_pi_snapshot.py` | DB load (AAS) so với vCPU · top SQL · top wait event |
| `cloudwatch_snapshot.py` | RDS · ElastiCache (hit rate, eviction) · ALB p50/p95/p99 · ECS · CloudFront |
| `pg-top-queries.sql` | pg_stat_statements theo tổng/trung bình thời gian · seq scan · index không dùng |

Cách chạy chi tiết: skill `perf-measure`.
