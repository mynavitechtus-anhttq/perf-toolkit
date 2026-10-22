---
description: Bản đồ perf-toolkit — luồng 7 bước, skill nào làm gì, script nào đo gì. Chỉ in hướng dẫn, không chạy gì.
---

In nguyên văn khối dưới cho người dùng, không chạy skill hay script nào.

```
perf-toolkit — cải thiện hiệu năng trang web (mọi trang)

 #  Bước            Skill                         Ra
 1  Phạm vi         perf-scope                    scope.md · pages.tsv · câu hỏi chốt với khách
 2  Đo hiện trạng   perf-measure baseline         report hiện trạng (chỉ số · phương án · mong đợi)   ← cổng quyết định
 3  Điều tra sâu    backend-perf điều tra         report-backend
                    psi-improve điều tra          report-psi
 4  Test + kế hoạch perf-test-plan · planning     test-plan · plan · wbs-schedule
 5  Implement       backend-perf / psi-improve implement <item>  + perf-measure compare
 6  Kiểm thử        tester + perf-measure compare (stg)  kết quả test · số đo stg
 7  Nghiệm thu      perf-measure verify · perf-report   report khách ja / vn-en

Report điều tra: TL;DR → Vấn đề → Hiện trạng → Nguyên nhân → Hướng xử lý → Mong đợi → AC
                 → Rủi ro → Quan điểm test → Còn treo → --- → Chi tiết kỹ thuật

Script ($PLUGIN/scripts)
  measure-ttfb.sh          TTFB warm median/min/p95, tách server vs mạng, before/after · miss (lúc chưa có cache)
  measure_psi.py           điểm PSI + lab (median N lần) + field CrUX, LCP subparts, bên thứ ba
                           --engine psi (prod, cần PSI_API_KEY) | lighthouse (stg có Basic Auth)
  rds_pi_snapshot.py       DB load vs vCPU, top SQL, top wait event  (chỉ đọc)
  cloudwatch_snapshot.py   RDS · ElastiCache hit rate · ALB p95/p99 · ECS · CloudFront  (--list, --dry-run)
  pg-top-queries.sql       pg_stat_statements, seq scan, index không dùng

Luật cứng: đo trước sửa sau · mọi số kèm điều kiện đo · prod hỏi trước + không load test ·
           AWS / DB chỉ đọc · đổi tag marketing phải khách duyệt · một thay đổi một lần đo.
Profile dự án: <repo>/.claude/perf-toolkit.md → profiles/<project>.md (có sẵn: kaigo)
```
