---
name: perf-test-plan
description: >-
  Plan the before/after testing for a performance refactor so the speed-up does not silently change
  behavior: output parity (golden master of HTML/JSON responses), unit tests (cache keys, TTL, null and
  disabled-cache paths, fallback when Redis is down), integration tests (repository results, cache on/off),
  query-count guards against N+1 regressions, regression and smoke suites for every affected screen, E2E
  automation, visual regression and tracking/SEO parity for PageSpeed changes, and the performance
  acceptance measurement. Test cases are authored through the company QC framework (ai-qc-framework MCP)
  when it is connected. Use for "phương án test", "test plan cho refactor perf", "test trước sau",
  "regression cho cải thiện tốc độ", "làm sao chắc không hỏng", or right after report-backend / report-psi.
---

# perf-test-plan — chứng minh nhanh hơn mà không hỏng

> Luồng, workspace: [`../_shared/workflow.md`](../_shared/workflow.md).
> Ai nghĩ, ai gõ: tester / test lead sở hữu test case và quyết phạm vi regression; AI đề xuất ma trận + nháp.

Refactor hiệu năng có một đặc điểm: **người dùng không được thấy gì khác, ngoài tốc độ**. Nên test plan phải chứng minh hai thứ:

1. **Hành vi không đổi** — cùng input, cùng output.
2. **Hiệu năng đạt AC** — bằng số, cùng điều kiện đo.

## Input

`report-backend-*.md` / `report-psi-*.md` (thay đổi + *Quan điểm test*) · `scope.md` (màn bị ảnh hưởng) · cấu hình test hiện có của repo (PHPUnit/Pest, Playwright…).

## Bước 1 — Ma trận thay đổi × loại test

Mỗi thay đổi (item) một dòng, đánh dấu loại test cần. Thay đổi càng chạm chỗ dùng chung thì regression càng rộng.

| Loại | Chứng minh | Áp cho | Cách / công cụ |
|---|---|---|---|
| **Parity (golden master)** | Output không đổi | Mọi refactor backend | Lưu response HTML/JSON của bộ URL **trước** khi sửa, chuẩn hoá phần động (CSRF token, timestamp, thứ tự ngẫu nhiên, nonce), diff **sau** khi sửa |
| **Unit** | Logic mới đúng | Cache key, TTL, xử lý null/rỗng, cache tắt, fallback | PHPUnit / Pest — `unittest-toolkit` nếu có cài |
| **Integration** | Dữ liệu thật đúng | Query viết lại, repository, cache bật/tắt, Redis down | Test có DB (fixture) |
| **Query-count guard** | Không tái phát N+1 | Chỗ vừa sửa N+1 | Assert số query ≤ ngưỡng / request (vd `expectsDatabaseQueryCount` của Laravel) |
| **Regression / smoke** | Màn liên quan không vỡ | Mọi màn trong *impact* của scope | Test case theo QC framework (Bước 3) |
| **E2E tự động** | Luồng chính vẫn chạy | Luồng người dùng chính | Playwright / e2e-automator nếu repo đã có |
| **Visual regression** | Giao diện không lệch | Đổi CSS, font, ảnh, thứ tự script | Chụp mobile + desktop trước/sau, so sánh (vd `toHaveScreenshot`) |
| **Tracking parity** | Tag / event vẫn bắn | Đổi tag, đổi thứ tự / thời điểm script | Kiểm `dataLayer` + request tới endpoint analytics |
| **SEO parity** | SEO không đổi | Đổi `<head>`, render, lazy load | title · meta · canonical · structured data · nội dung không bị ẩn |
| **Perf acceptance** | Đạt AC | Mọi item | `perf-measure compare`, cùng điều kiện baseline |

## Bước 2 — Dữ liệu & môi trường

- Parity cần dữ liệu **cố định** giữa hai lần chạy — chụp và so trên cùng môi trường, cùng snapshot dữ liệu; dữ liệu đổi giữa chừng thì diff vô nghĩa.
- Đo hiệu năng cần dữ liệu gần prod (stg). Dev ít dữ liệu che mất N+1 và seq scan.
- Ghi rõ test chạy ở đâu (local / dev / stg) và ai chạy.

## Bước 3 — Test case qua ai-qc-framework (khi MCP đã kết nối)

Test case regression / smoke là việc của tester, theo bộ khung QC công ty — **không tự chế format**.

1. Gọi `get_doc("AGENTS.md")` của MCP `ai-qc-framework` trước tiên và làm theo routing trong đó. Cần `<project-name>` (thư mục trong `QC-Knowledge/`) — hỏi tester nếu chưa biết.
2. Skill thường dùng cho loại việc này: `smoke-test-checklist` (từ spec / mô tả màn) · `regression-test-suite` · `create-test-case` (cần Analysis Report của `analyze-spec`) · `classify-test-case` (phân loại Auto/Manual).
3. Đưa cho tester: danh sách màn bị ảnh hưởng (từ `scope.md`) + thay đổi + rủi ro (từ report) làm input.
4. Lưu output vào workspace: checklist → `$WS/6-testing/checklist-{smoke|regression}.md` · test case → `$WS/6-testing/testcases/` (giữ nguyên format QC framework trả về).

MCP chưa kết nối / lỗi xác thực → dừng phần này, ghi *"test case: chờ tester tạo qua QC framework"* vào *Còn treo*; không đoán format.

## Bước 4 — Tiêu chí dừng & rollback

- Item chỉ "xong" khi: parity PASS · test của item PASS · regression của màn liên quan PASS · đạt AC hiệu năng.
- Mỗi item ghi **cách rollback**: tắt cờ cấu hình / revert PR / xoá index (`DROP INDEX CONCURRENTLY`).

## Output

`$WS/6-testing/test-plan.md` theo `$PLUGIN/templates/test-plan.md` · checklist + test case ở `$WS/6-testing/` (Bước 3). Kết quả chạy test ở bước implement / stg / prod → `$WS/6-testing/results/{item{N}|stg|prod}-{yyyymmdd}/`. Handoff: *"lên kế hoạch + lịch (`planning`)?"*
