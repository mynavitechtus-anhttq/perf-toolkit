# Điều tra hiệu năng backend — {phạm vi}

> {TICKET} · {date} · dựa trên `report-baseline-{date}.md`, `scope.md`

## TL;DR

{≤ 5 dòng: vấn đề chính + số · nguyên nhân gốc · hướng đề xuất · mong đợi}

## Vấn đề

- {mỗi vấn đề 1 dòng, có số — vd: TTFB warm median trang chi tiết 620ms, vượt ngân sách server 200ms}

## Hiện trạng

| Trang | TTFB median | Server | Query / request | SQL / request | Ghi chú |
|---|---:|---:|---:|---:|---|

## Nguyên nhân

| # | Nguyên nhân | Bằng chứng | Ảnh hưởng |
|---|---|---|---|
| 1 | | `file:line` · plan · số đo | {ms / % thời gian server} |

## Hướng xử lý

| # | Phương án | Sửa ở đâu | Effort | Ưu | Nhược / đánh đổi |
|---|---|---|---|---|---|

**Đề xuất:** {phương án nào, vì sao} — *người phụ trách chốt*

## Mong đợi

| Trang | Chỉ số | Hiện tại | Sau cải thiện | Cách tính |
|---|---|---:|---:|---|

## Tiêu chí chấp nhận (AC)

- [ ] {Chỉ số} trên {môi trường} đo bằng {công cụ, N lần} ≤ {ngưỡng}
- [ ] Output của {bộ URL} không đổi (parity PASS)
- [ ] Số query / request của {trang} ≤ {n}

## Rủi ro

| Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|

## Quan điểm test

| Cần chứng minh | Loại test | Phạm vi |
|---|---|---|
| Kết quả hiển thị không đổi | Parity (golden master) | {bộ URL} |
| Cache đúng: key, TTL, kết quả rỗng, cache tắt, Redis lỗi | Unit / integration | |
| Không tái phát N+1 | Query-count guard | |
| Màn liên quan không vỡ | Regression / smoke | {màn từ scope} |
| Đạt AC hiệu năng | perf-measure compare | |

→ Chi tiết: `test-plan.md` (`perf-test-plan`)

## Còn treo

| Việc | Vì sao chưa đóng | Ai / khi nào | Rủi ro nếu để nguyên |
|---|---|---|---|

*(Không có → ghi "không còn mục nào treo".)*

## Kết quả *(điền ở bước implement)*

| Item | Chỉ số | Trước | Sau | Đạt AC |
|---|---|---:|---:|---|

---

## Chi tiết kỹ thuật

### Top SQL & plan

### Code liên quan

## Refs
