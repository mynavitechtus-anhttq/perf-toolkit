# perf-toolkit

Bộ cải thiện hiệu năng trang web — **mọi trang**, không riêng trang tìm kiếm. Từ khảo sát phạm vi, đo hiện trạng, điều tra sâu backend và điểm PageSpeed, lên phương án test + kế hoạch, tới implement và báo cáo khách.

Rút từ dự án SHOKAI_ARCH_2506-76 (tối ưu trang tìm việc kaigo, 2 phase, prod −19% warm median) và best practice cộng đồng (web.dev, Lighthouse, PostgreSQL, AWS).

## Cài

```text
/plugin marketplace add ~/claude-plugins
/plugin install perf-toolkit@anhttq-local
```

Gõ `/perf-toolkit:help` để xem bản đồ.

## Luồng

| # | Bước | Skill | Output |
|---|---|---|---|
| 1 | Phạm vi | `perf-scope` | `scope.md` · `pages.tsv` · câu hỏi chốt với khách |
| 2 | Đo hiện trạng | `perf-measure` baseline | **report hiện trạng** — cổng quyết định |
| 3 | Điều tra sâu | `backend-perf` · `psi-improve` | `report-backend` · `report-psi` |
| 4 | Test + kế hoạch | `perf-test-plan` · `planning` | `test-plan` · `plan` · `wbs-schedule` |
| 5 | Implement | `backend-perf` / `psi-improve` implement + `perf-measure` compare | code + số trước/sau |
| 6 | Kiểm thử | tester + `perf-measure` compare trên stg | kết quả test · số đo stg |
| 7 | Nghiệm thu | `perf-measure` verify · `perf-report` | report khách ja / vn-en |

Chi tiết luồng, workspace, an toàn, ngân sách: [`skills/_shared/workflow.md`](skills/_shared/workflow.md).

## Script

| Script | Đo gì | Cần |
|---|---|---|
| `scripts/measure-ttfb.sh` | TTFB warm median/min/p95, tách server vs mạng, before/after | bash, curl |
| `scripts/measure_psi.py` | điểm + lab (median N lần), field CrUX, LCP subparts, bên thứ ba, opportunities | python3; `PSI_API_KEY` (engine psi) hoặc Chrome + npx (engine lighthouse) |
| `scripts/rds_pi_snapshot.py` | DB load vs vCPU, top SQL, top wait event | aws cli, quyền đọc `pi:*` |
| `scripts/cloudwatch_snapshot.py` | RDS, ElastiCache, ALB, ECS, CloudFront | aws cli, quyền đọc CloudWatch |
| `scripts/pg-top-queries.sql` | pg_stat_statements, seq scan, index không dùng | psql, extension pg_stat_statements |

Không cần cài thêm thư viện Python. Mọi lệnh AWS / DB đều chỉ đọc.

## Profile dự án

Đặc thù từng dự án (knowledge base, môi trường, tài nguyên AWS, gotcha) nằm ở profile:
`<repo>/.claude/perf-toolkit.md` → `profiles/<project>.md`. Có sẵn: [`profiles/kaigo.md`](profiles/kaigo.md).

## Liên quan

- `task-toolkit:perf-check` — cổng hiệu năng cho **một task bình thường** (thay đổi này có làm chậm gì không). perf-toolkit dành cho **dự án cải thiện hiệu năng**.
- `planning` ở đây là bản copy từ `task-toolkit:planning`, chỉnh cho dự án hiệu năng. Planning task thường → dùng bản của task-toolkit.
