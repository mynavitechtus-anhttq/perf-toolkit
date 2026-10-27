---
name: backend-perf
description: >-
  Investigate, then implement, server-side performance improvements for any page of a web app (method is
  generic; recipes focus on Laravel/PHP + PostgreSQL + Redis on AWS). Investigate mode splits TTFB into
  network vs server, counts queries per request, ranks SQL by total time (pg_stat_statements, RDS
  Performance Insights), reads EXPLAIN (ANALYZE, BUFFERS), finds missing/unused indexes, N+1 and queries
  inside loops (including inside view components), over-fetching, expensive counts, disabled or wrong
  caching, synchronous writes and logging on the request path, framework/runtime config — and writes
  report-backend (problem, current numbers, root cause with evidence, options, expected gain, acceptance
  criteria, risks, test viewpoint). Implement mode ships one change at a time with before/after numbers.
  Use for "trang chậm", "TTFB cao", "query chậm", "explain query", "thêm index", "N+1", "cache chưa hợp
  lý", "cải thiện performance chức năng detail/search/…", "điều tra backend perf".
---

# backend-perf — điều tra → implement phía server

> Luồng, an toàn, ngân sách: [`../_shared/workflow.md`](../_shared/workflow.md).
> Công thức chi tiết từng bước: [`references/playbook.md`](references/playbook.md).
> Ai nghĩ, ai gõ: chọn hướng xử lý là của người phụ trách — AI đưa phương án kèm đánh đổi, không chốt thay.

Chạy `backend-perf điều tra` hoặc `backend-perf implement <item>`. Không nói mode → hỏi 1 câu.

## Mode ĐIỀU TRA

**Input:** `scope.md` + `report-baseline-*.md` + số đo trong `2-baseline/raw-*/`. Thiếu baseline → chạy `perf-measure baseline` trước.

Đi từ ngoài vào trong, đúng thứ tự — checklist không kèm thứ tự thì người ta tick từ trên xuống và bỏ sót chỗ nghẽn thật:

| # | Bước | Trả lời câu hỏi | Playbook |
|---|---|---|---|
| 0 | Tải hay code? | Chậm trùng khung giờ đông / ngày traffic tăng mà không trùng release → không phải code, chuyển [`infra-check`](../infra-check/SKILL.md) | `perf-measure` §Khoanh vùng · §10 |
| 1 | Tách TTFB | Chậm ở mạng hay ở server? *Server* nhỏ → dừng, chuyển sang mạng/hạ tầng | §1 |
| 2 | Profile 1 request | Bao nhiêu query, tổng SQL bao lâu, use case nào chiếm thời gian | §2 |
| 3 | Xếp hạng SQL | Câu nào tốn **tổng** nhiều nhất (chậm × nhiều lần); DB đang chờ gì | §3 |
| 4 | Đọc plan | Vì sao câu đó chậm — seq scan, ước lượng lệch, subplan theo dòng | §4 |
| 5 | Index | Thiếu index nào, index nào thừa, có được tạo không (bảng của ai) | §5 |
| 6 | Code | N+1, query trong vòng lặp / trong view component, lấy thừa, đếm đắt, query lặp | §6 |
| 7 | Cache | Có bật thật không, hit rate, key ổn định không, cache null, MGET, stampede | §7 |
| 8 | Việc đồng bộ trên request | Ghi DB / log nặng / gọi ngoài ngay trong request | §6.5 |
| 9 | Runtime | OPcache, `optimize`, FPM pool, số connection DB | §8 |

Mỗi nguyên nhân phải có **bằng chứng** (file:line · plan · số đo) và **ảnh hưởng tính bằng ms hoặc % thời gian**. Không có số → `[Giả định — cách verify: …]`.

**Output:** `$WS/3-investigate/report-backend-{yyyymmdd}.md` theo `$PLUGIN/templates/report-backend.md`. Cấu trúc bất biến:

`TL;DR` → Vấn đề → Hiện trạng → Nguyên nhân → Hướng xử lý → Mong đợi → **AC** → Rủi ro → **Quan điểm test** → Còn treo → `---` → Chi tiết kỹ thuật → Refs

- **Ngắn, đủ ý:** TL;DR ≤ 5 dòng; phần trên `---` ≤ 1 trang; gạch đầu dòng thay đoạn văn.
- **AC phải đo được:** chỉ số + môi trường + công cụ + ngưỡng. "Nhanh hơn" không phải AC.
- **Quan điểm test:** cần chứng minh gì (hành vi không đổi, cache đúng, không tái phát N+1, màn liên quan không vỡ, đạt AC) bằng loại test nào — chi tiết để `perf-test-plan`.
- **Còn treo:** không có → ghi *"không còn mục nào treo"*. Không tự đóng nợ hộ — chấp nhận rủi ro là quyết định của người.

Handoff: *"lên phương án test (`perf-test-plan`) rồi `planning`?"*

## Mode IMPLEMENT

**Điều kiện vào:** report đã được duyệt hướng · có `test-plan.md` · item có trong `plan.md`.

1. **Đo trước** cho đúng item (local: query count / plan; stg: `perf-measure compare` phase before).
2. **Một item = một thay đổi = một PR.** Thay đổi rủi ro → bật/tắt bằng cấu hình (env) để rollback không cần deploy lại code.
3. Giữ quy ước repo (profile dự án ghi rõ — vd raw SQL ở repository, cache qua service chứ không gọi `Cache::` thẳng trong use case, code module dùng chung phải xét mọi nơi gọi).
4. Chạy test theo `test-plan.md` — tối thiểu **parity** (output không đổi) + test của phần vừa sửa. Lưu kết quả (parity diff, output test) vào `$WS/6-testing/results/item{N}-{yyyymmdd}/`.
5. **Đo sau** cùng điều kiện → điền cột *Kết quả* vào report backend. Không đạt AC → không sang item kế; ghi lại vì sao.
6. Code tạm để đo (log query, timer) **không được commit**.

## Guardrails

- **[HARD]** Không sửa khi chưa có số đo của chính chỗ định sửa.
- **[HARD]** `EXPLAIN ANALYZE` câu ghi → `BEGIN; … ROLLBACK;`. Không chạy trên prod primary khi chưa được duyệt.
- **[HARD]** Tạo index trên prod = thay đổi: `CREATE INDEX CONCURRENTLY`, có kế hoạch, có người duyệt; bảng do hệ thống khác ghi → phải thống nhất với bên đó.
- Không thêm cache khi chưa trả lời: dữ liệu đổi lúc nào, xoá cache ở đâu. Cache sai chỗ đổi bug *chậm* lấy bug *dữ liệu cũ* — khó tìm hơn nhiều.
- Không tối ưu thứ chạy 1 lần/tháng khi thứ chạy mỗi request đang chậm. Ưu tiên theo **tần suất × chi phí**.
- Octane / kiến trúc lớn chỉ đề xuất sau khi đã làm hết phần query + cache + code.
