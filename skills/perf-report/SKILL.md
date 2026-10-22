---
name: perf-report
description: >-
  Write the customer-facing before/after performance report at the end of a performance or PageSpeed
  improvement — purpose, measurement conditions, method (why warm-cache numbers, why median of N runs),
  overall result, observations, notes and per-URL details, in Japanese or Vietnamese/English bilingual,
  built only from numbers produced by perf-measure. Use for "viết report kết quả cải thiện", "báo cáo khách
  sau release", "レポート作成 速度改善", "report before after cho khách", or at the verify step after a
  production release.
---

# perf-report — báo cáo kết quả cho khách

> Luồng, workspace: [`../_shared/workflow.md`](../_shared/workflow.md).

## Input

- Số đo `compare` / `verify` của `perf-measure` (report + summary trong `5-implement/item*/` · `6-testing/results/stg-*/` · `7-delivery/verify-*/`).
- `report-backend-*.md` / `report-psi-*.md` — đã làm gì, vì sao.

Không có số đo sau release → **không viết**, chạy `perf-measure verify` trước. Report khách không có số ước lượng.

## Cấu trúc (giữ nguyên thứ tự)

Template: `$PLUGIN/templates/report-final-ja.md` · `report-final-vn-en.md` (song ngữ, phân cách bằng khối `English:`).

1. **Mục đích** — 1–2 câu.
2. **Điều kiện đo** — môi trường, trước/sau, ngày, số lần, đối tượng.
3. **Phương pháp đo** — vì sao đo trạng thái cache nóng / median N lần; khách không cần biết curl hay Lighthouse CLI, cần biết *đo cái gì và vì sao công bằng*.
4. **Kết quả tổng** — 1 bảng, mỗi chỉ số giải thích 1 câu bằng ví dụ số thật.
5. **Nhận xét** — 3 gạch đầu dòng: cải thiện ở đâu, có lỗi không.
6. **Lưu ý** — giới hạn: lần truy cập đầu, field data cần tới 28 ngày, phần chưa làm (phase sau).
7. **Chi tiết theo URL** — bảng trước / sau / %.

## Quy tắc

- Mọi số lấy từ output của script — **không làm tròn đẹp**, không chọn lần đo đẹp nhất.
- Có chỉ số xấu đi → ghi ra, kèm lý do. Giấu số xấu là mất uy tín khi khách tự đo.
- Không lộ: URL nội bộ (stg/dev), tên người, credential, tên tài nguyên AWS.
- Giữ nguyên chuỗi UI tiếng Nhật ở mọi bản.
- Môi trường có agent thẩm định (vd `task-toolkit:report-reviewer`, `verify-claims`) → chạy trước khi gửi.

## Output

`$WS/7-delivery/report-final-{ja|vn-en}-{yyyymmdd}.md`. Xuất docx/pdf: `pandoc` từ file `.md` (CJK: `-V mainfont="Hiragino Sans"`); file `.md` là bản gốc để sửa.
