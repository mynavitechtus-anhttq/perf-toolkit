# Báo cáo kiểm tra tốc độ {đối tượng} sau {hạng mục} (môi trường {Production})
# {Target} Performance Report After {Item} ({Production})

## 1. Mục đích / Purpose

Kiểm tra mức cải thiện tốc độ của {trang} sau khi release {hạng mục} lên {production}.

English:

> Verify the {page} speed improvement after releasing {item} to {production}.

## 2. Điều kiện đo / Measurement Conditions

- Môi trường {production} trước release (trước tối ưu)
- Môi trường {production} sau release (sau tối ưu)
- Đo trước/sau release trên cùng môi trường
- Thời điểm đo: {YYYY/MM/DD}
- Số lần đo: {N} lần cho mỗi URL
- Đối tượng đo: {URL trang}

English:

> - {Production} before release (before optimization)
> - {Production} after release (after optimization)
> - Before/after measured on the same environment
> - Measurement date: {YYYY/MM/DD}
> - Number of measurements: {N} times per URL
> - Target: {page URLs}

## 3. Phương pháp đo / Measurement Method

{Vì sao đo ở trạng thái này — vd cache đã có dữ liệu — 2–3 câu.}

Cách đo:

- {vd: mỗi URL được truy cập trước vài lần để tạo cache}
- Mỗi URL được đo {N} lần.
- Báo cáo dùng giá trị trung vị của {N} lần đo.
- Tất cả URL đều trả về HTTP OK.

English:

> {Why this state was measured — 2–3 sentences.}
>
> - {e.g. each URL was accessed a few times beforehand to create cache data}
> - Each URL was measured {N} times.
> - The median of {N} measurements is used as the result.
> - All measured URLs returned HTTP OK.

## 4. Kết quả tổng quan / Overall Result

| Chỉ số / Metric | Trước / Before | Sau / After | Kết quả / Result |
|---|---:|---:|---|
| {chỉ số} | {giá trị} | {giá trị} | {cải thiện ~X%} |

- **{Chỉ số}**: {nghĩa là gì, kèm ví dụ bằng số thật}

English:

> - **{Metric}**: {what it means, with an example using the real numbers}

## 5. Nhận xét / Observations

- {điểm cải thiện}
- {điều kiện thấy rõ cải thiện}
- {có lỗi hay không}

English:

> - {…}

## 6. Lưu ý / Notes

- {phạm vi lần này và lý do}
- {phần số liệu chưa phản ánh: lần truy cập đầu, field data cần tới 28 ngày}
- {việc của phase sau}

English:

> - {…}

## 7. Chi tiết theo URL / Details By URL

| Trang / Page | URL | Trước / Before | Sau / After | Cải thiện / Improvement |
|---|---|---:|---:|---:|
