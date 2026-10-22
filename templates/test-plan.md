# Phương án test — {TICKET}

> Thay đổi: từ `report-backend-{date}.md` / `report-psi-{date}.md` · Màn bị ảnh hưởng: từ `scope.md`

## Mục tiêu

1. **Hành vi không đổi** — cùng input, cùng output.
2. **Hiệu năng đạt AC** — bằng số, cùng điều kiện với baseline.

## Ma trận

| Item | Thay đổi | Có thể hỏng gì | Parity | Unit | Integ. | Query guard | Regression | E2E | Visual | Tracking | SEO | Perf |
|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | | | ✓ | | | | ✓ | | | | | ✓ |

## Chi tiết

### Parity (golden master)
- Bộ URL: {pages.tsv + URL biến thể}
- Phần động chuẩn hoá trước khi so: {CSRF token, timestamp, thứ tự ngẫu nhiên…}
- Chụp **trước** khi sửa, so **sau** khi sửa, cùng môi trường + cùng dữ liệu.

### Unit / integration
| Item | Case | Kỳ vọng |
|---|---|---|

### Regression / smoke
- Màn: {danh sách}
- Test case: tạo qua ai-qc-framework — project `{project-name}`, skill `{smoke-test-checklist / regression-test-suite / create-test-case}` · người phụ trách: {tester}
- Lưu: checklist → `checklist-{smoke|regression}.md` · test case → `testcases/` · kết quả → `results/` (cùng thư mục `6-testing/`)

### E2E tự động
- {luồng} — {đã có / cần thêm}

### Visual · tracking · SEO
- Visual: {trang} × mobile + desktop
- Tracking: {event / tag}
- SEO: title · meta · canonical · structured data

### Hiệu năng (AC)
| Item | Chỉ số | Công cụ | Môi trường | Ngưỡng |
|---|---|---|---|---|

## Dữ liệu & môi trường

| Loại test | Chạy ở | Dữ liệu | Ai chạy |
|---|---|---|---|

## Tiêu chí xong & rollback

| Item | Xong khi | Rollback |
|---|---|---|
| 1 | parity · test item · regression · AC đều PASS | {tắt cờ env / revert PR / DROP INDEX CONCURRENTLY} |
