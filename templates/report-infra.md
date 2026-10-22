# Điều tra hạ tầng — {phạm vi}

> {TICKET} · {date} · môi trường {prod} · cách làm: {Console / CLI} · khung thời gian: {từ → tới, múi giờ}

## TL;DR

- {≤ 5 dòng: chậm do đâu ở tầng hạ tầng · từ khi nào · bằng chứng chính · hướng xử lý · cần ai quyết}

## Kết quả theo mục

| # | Câu hỏi | Số liệu chính | Kết luận | Mức chắc chắn |
|---|---|---|---|---|
| 1 | Lượng truy cập / độ trễ theo thời gian | {req/giờ trong và ngoài khung, p99} | | có số đo / [Giả định] |
| 2 | Ai tạo ra lượng truy cập | {UA / IP / loại URL, % URL không lặp} | | |
| 3 | Tải DB reader / writer | {CPU avg/max, connection, buffer hit, IOPS} | | |
| 4 | Replica autoscaling | {policy, lịch thêm/bớt, có chạm max không} | | |
| 5 | Top SQL / wait | {top 3 SQL theo DB load} | | |
| 6 | Cấu hình | {instance, số reader, app đọc reader hay writer} | | |
| 7 | Dung lượng dữ liệu | {VolumeBytesUsed, bảng lớn nhất} | | |
| 8 | Cache | {hit rate, eviction} | | |

Bỏ mục không làm — không để trống.

## Mốc thời gian

| Ngày | Chuyện gì | Nguồn |
|---|---|---|
| | {bậc tăng traffic / release / thay đổi cấu hình} | {CloudWatch / git log / event RDS} |

## Phương án (đưa vào report hiện trạng)

| # | Phương án | Tác động | Ai quyết | Ghi chú |
|---|---|---|---|---|

## Còn treo

| Việc | Vì sao chưa đóng | Ai / khi nào |
|---|---|---|

---

## Điều kiện

- Tài khoản / profile: {tên profile, account id} · chỉ dùng lệnh đọc
- Access log: {giờ lấy mẫu} — log gốc không lưu vào repo, chỉ số đã gộp
- Số thô: `raw-{yyyymmdd}/`
