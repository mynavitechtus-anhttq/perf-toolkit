# Phạm vi hiệu năng — {TICKET}

> Knowledge base: `{repo}` @ `{branch}` · commit `{hash}` ({date}) · đọc ngày {date}
> {Nếu đọc bản local vì không clone được: ⚠ tài liệu có thể cũ — nhánh {x}, commit cuối {date}}

## Trang trong phạm vi

| Nhóm | Trang | Route | Spec | Ghi chú |
|---|---|---|---|---|
| {detail} | {Chi tiết tin} | `{/d/{id}}` | `{SCR-…}` | |

## Bản đồ phụ thuộc — {trang}

| Lớp | Thành phần | File / nguồn | Nghi vấn hiệu năng |
|---|---|---|---|
| Route / controller | | | |
| Use case | | | |
| Query / bảng | | | |
| Cache (key · TTL · bật?) | | | |
| Ghi đồng bộ trên request | | | |
| Gọi ngoài | | | |
| Batch cấp dữ liệu | | | |
| View component | | | |
| Asset (JS / CSS / font / ảnh lớn) | | | |
| Tag bên thứ ba | | | |

*(Lặp bảng cho từng trang.)*

## URL đại diện

→ `pages.tsv` ({n} URL, {m} nhóm). Biến thể đã phủ: {có ảnh / không ảnh · trang 1 / trang N · …}

## Câu hỏi phải chốt với khách

| # | Câu hỏi | Vì sao cần | Trả lời |
|---|---|---|---|
| 1 | Trang nào, thiết bị nào (mobile / desktop)? | Phạm vi đo + nghiệm thu | |
| 2 | "Điểm PSI" là lab score hay Core Web Vitals field? | Hai cách đo, hai cách nghiệm thu | |
| 3 | Mục tiêu bao nhiêu? Nghiệm thu median 5 lần? | Điểm lab dao động ±5–10 | |
| 4 | Được đo prod không, khung giờ nào? | An toàn + số liệu thật | |
| 5 | Ai duyệt thay đổi tag marketing? | Chặn mọi item đụng GTM / tag | |
| 6 | Bảng dữ liệu do ai ghi, team có được thêm index không? | Chặn hướng xử lý index | |

## Lệch tài liệu ↔ code

| Tài liệu nói | Code thực tế | Nguồn |
|---|---|---|

## Rủi ro phạm vi

-
