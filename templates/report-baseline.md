# Hiện trạng hiệu năng — {phạm vi}

> {TICKET} · đo ngày {date} · môi trường {prod} · điều kiện chi tiết ở cuối

## TL;DR

- {≤ 5 dòng: trang nào kém nhất · chỉ số nào kéo điểm · hướng có lợi nhất · mong đợi (khoảng) · cần khách chốt gì}

## Chỉ số hiện tại

### Điểm PSI & chỉ số lab — {mobile}, median {5} lần

| Trang | Điểm (min–max) | LCP | TBT | CLS | FCP | TTFB |
|---|---:|---:|---:|---:|---:|---:|

### Người dùng thật (CrUX, p75, 28 ngày)

| Trang | Phạm vi | LCP | INP | CLS | Đánh giá |
|---|---|---:|---:|---:|---|

### Thời gian phản hồi server (TTFB, cache nóng)

| Trang | Median | Min | P95 | Server | Mạng |
|---|---:|---:|---:|---:|---:|

## Thời gian đang mất ở đâu

| Trang | Chỉ số | Mất vì | Bằng chứng |
|---|---|---|---|
| | LCP | {ảnh LCP bị lazy-load → load delay 1.3s} | {LHR: lcp subparts} |
| | TBT | {GTM chặn 380ms} | {third-party-summary} |
| | TTFB | {server 450ms, top SQL chiếm 60% DB load} | {rds-pi} |

## Phương án cải thiện (sơ bộ)

| # | Phương án | Tác động lên | Mong đợi | Độ tin cậy | Effort | Cần duyệt / phụ thuộc |
|---|---|---|---|---|---|---|
| 1 | | | | cao / TB / thấp | S / M / L | |

## Mong đợi tổng

| Trang | Chỉ số | Hiện tại | Dự kiến | Độ tin cậy |
|---|---|---:|---:|---|

> Số dự kiến là **khoảng ước lượng** từ dữ liệu đo (Lighthouse estimated savings, tỉ trọng SQL trong DB load). **Chốt sau bước điều tra sâu**, không dùng làm cam kết.
> Field data (người dùng thật) cần tới 28 ngày sau release mới phản ánh đủ.

## Cần khách chốt

-

## Bước tiếp

- {Điều tra sâu backend / PSI cho phương án {#} — sau khi khách chốt}

---

## Điều kiện đo

| Công cụ | Môi trường | Số lần | Thiết bị | Thời điểm | Ghi chú |
|---|---|---|---|---|---|
| measure-ttfb.sh | | N={20} warm sau {4} warm-up | — | | |
| measure_psi.py | | median {5} lần | mobile / desktop | | Lighthouse {ver} |
| rds_pi_snapshot.py | | — | — | {khung giờ UTC} | |

Output thô: `raw-{yyyymmdd}/` (cùng thư mục)
