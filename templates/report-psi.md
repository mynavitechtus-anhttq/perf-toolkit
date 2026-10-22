# Điều tra điểm PageSpeed — {phạm vi}

> {TICKET} · {date} · dựa trên `report-baseline-{date}.md`, `scope.md` · nghiệm thu bằng {lab mobile / field}

## TL;DR

{≤ 5 dòng: điểm hiện tại · chỉ số kéo điểm nhiều nhất · nguyên nhân chính · hướng đề xuất · điểm dự kiến}

## Vấn đề

- {mỗi vấn đề 1 dòng, có số — vd: TBT mobile 900ms (trọng số 30%), GTM chặn 380ms}

## Hiện trạng

| Trang | Thiết bị | Điểm (min–max) | LCP | TBT | CLS | FCP | Field LCP / INP / CLS |
|---|---|---:|---:|---:|---:|---:|---|

## Nguyên nhân

| # | Chỉ số | Nguyên nhân | Bằng chứng (audit · số) | Mất bao nhiêu |
|---|---|---|---|---|
| 1 | LCP | | `lcp subparts`: load delay {x}ms | |

## Hướng xử lý

| # | Phương án | Sửa ở đâu | Effort | Ưu | Nhược / đánh đổi | Cần khách duyệt |
|---|---|---|---|---|---|---|

**Đề xuất:** {phương án nào, vì sao} — *người phụ trách chốt*

## Mong đợi

| Trang | Thiết bị | Chỉ số | Hiện tại | Mục tiêu | Điểm dự kiến |
|---|---|---|---:|---:|---|

> Điểm dự kiến tính bằng Lighthouse Scoring Calculator từ giá trị mục tiêu — là khoảng, vì điểm lab dao động.
> Field data: tới 28 ngày sau release mới phản ánh đủ.

## Tiêu chí chấp nhận (AC)

- [ ] Điểm {mobile} median 5 lần trên {prod} ≥ {X}
- [ ] {LCP / TBT / CLS} ≤ {ngưỡng}
- [ ] Giao diện mobile + desktop không lệch (visual PASS)
- [ ] Tag / event vẫn bắn đủ (tracking PASS) · SEO không đổi

## Rủi ro

| Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|
| Hoãn tag tới sau tương tác làm mất số liệu người rời trang sớm | | | Khách duyệt đánh đổi |

## Quan điểm test

| Cần chứng minh | Loại test | Phạm vi |
|---|---|---|
| Giao diện không lệch | Visual regression (mobile + desktop) | {trang} |
| Tag / event vẫn bắn | Tracking parity | {event quan trọng} |
| SEO không đổi | SEO parity: title · meta · canonical · structured data | {trang} |
| Chức năng không vỡ | Regression / smoke · E2E | {màn từ scope} |
| Đạt AC | perf-measure compare (median 5 lần) | |

→ Chi tiết: `test-plan.md` (`perf-test-plan`)

## Còn treo

| Việc | Vì sao chưa đóng | Ai / khi nào | Rủi ro nếu để nguyên |
|---|---|---|---|

## Kết quả *(điền ở bước implement)*

| Item | Thiết bị | Điểm trước → sau | Chỉ số chính trước → sau | Đạt AC |
|---|---|---|---|---|

---

## Chi tiết kỹ thuật

### Opportunities & diagnostics (LHR)

### Bên thứ ba

### File liên quan

## Refs
