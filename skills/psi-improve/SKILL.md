---
name: psi-improve
description: >-
  Investigate, then implement, improvements to the PageSpeed Insights / Lighthouse score and Core Web
  Vitals of any page. Investigate mode reads where the score is lost (weights: TBT 30, LCP 25, CLS 25,
  FCP 10, SI 10), breaks LCP into its four subparts, attributes main-thread blocking to third-party tags
  (GTM, analytics, ads, chat widgets) and own JS, finds layout-shift sources (unsized images, late
  banners, web-font swap), render-blocking CSS/JS, heavy Japanese web fonts, oversized images, missing
  CDN caching/compression, large DOM — then writes report-psi (problem, current lab + field numbers, root
  cause with Lighthouse evidence, options, expected score, acceptance criteria, risks, test viewpoint).
  Implement mode ships one change at a time, re-measured as a 5-run median, with visual, tracking and SEO
  parity checks. Use for "cải thiện điểm PSI", "PageSpeed thấp", "Lighthouse", "Core Web Vitals", "LCP
  chậm", "CLS", "TBT", "INP", "tối ưu tốc độ hiển thị", "tối ưu font/ảnh/JS".
---

# psi-improve — điều tra → implement điểm PSI

> Luồng, an toàn, ngân sách, trọng số điểm: [`../_shared/workflow.md`](../_shared/workflow.md).
> Công thức chi tiết theo từng chỉ số: [`references/playbook.md`](references/playbook.md).
> Ai nghĩ, ai gõ: chọn hướng là của người phụ trách; **đổi tag marketing là của khách** — AI chỉ đưa phương án kèm đánh đổi.

Chạy `psi-improve điều tra` hoặc `psi-improve implement <item>`. Không nói mode → hỏi 1 câu.

## Trước hết: hiểu đang tối ưu cái gì

| | Lab (điểm PSI) | Field (Core Web Vitals) |
|---|---|---|
| Là gì | Lighthouse chạy 1 lần trên máy giả lập mobile yếu, mạng chậm | Số đo người dùng Chrome thật, p75, cửa sổ 28 ngày |
| Đo bằng | `measure_psi.py` (median ≥ 5 lần) | `measure_psi.py` mục Field |
| Phản hồi khi sửa | Ngay | **Tới 28 ngày** |
| Chỉ số tương tác | TBT (đại diện) | INP |

Scope phải ghi rõ khách nghiệm thu bằng cái nào. Không rõ → hỏi lại trước khi điều tra.

## Mode ĐIỀU TRA

**Input:** `scope.md` + `report-baseline-*.md` + `2-baseline/raw-*/psi/` (summary.json + raw LHR của run đại diện).

| # | Bước | Trả lời câu hỏi | Playbook |
|---|---|---|---|
| 1 | Điểm mất ở đâu | Chỉ số nào kéo điểm nhiều nhất = trọng số × khoảng cách tới mức tốt | §1 |
| 2 | LCP | Phần tử LCP là gì; 4 subpart cái nào phình | §2 |
| 3 | TBT / INP | Ai chiếm main thread: tag bên thứ ba hay JS của mình; long task | §3 |
| 4 | CLS | Phần tử nào nhảy; vì sao (ảnh, banner, font) | §4 |
| 5 | FCP / SI | CSS/JS chặn render, font, redirect | §5 |
| 6 | Font tiếng Nhật | Có tự host bản đầy đủ không; bao nhiêu độ đậm | §6 |
| 7 | Ảnh | Kích thước, định dạng, lazy sai chỗ, thiếu width/height | §7 |
| 8 | Mạng / CDN | Cache header, nén, preconnect, bfcache | §8 |
| 9 | DOM / render | DOM lớn, khởi tạo carousel/slider nặng | §9 |

Bằng chứng lấy từ LHR (audit id + số), DevTools Performance trace, Coverage. TTFB là phần lớn của LCP → chuyển sang `backend-perf`.

**Output:** `$WS/3-investigate/report-psi-{yyyymmdd}.md` theo `$PLUGIN/templates/report-psi.md`. Cấu trúc bất biến giống `backend-perf`:

`TL;DR` → Vấn đề → Hiện trạng → Nguyên nhân → Hướng xử lý → Mong đợi → **AC** → Rủi ro → **Quan điểm test** → Còn treo → `---` → Chi tiết kỹ thuật → Refs

- **Mong đợi** = giá trị metric mục tiêu → điểm dự kiến qua [Lighthouse Scoring Calculator](https://googlechrome.github.io/lighthouse/scorecalc/), ghi **khoảng**; field ghi kèm mốc thời gian (tới 28 ngày sau release).
- **AC** dạng: *điểm mobile median 5 lần trên prod ≥ X · LCP ≤ Y · không vỡ giao diện · tag vẫn bắn đủ*.
- **Quan điểm test** bắt buộc có: visual regression · tracking parity · SEO parity · regression chức năng · đo lại.

## Mode IMPLEMENT

**Điều kiện vào:** report đã duyệt · có `test-plan.md` · item có trong `plan.md` · đổi tag → **có xác nhận của khách bằng văn bản**.

1. **Đo trước** đúng trang / thiết bị của item (median 5 lần, cùng môi trường).
2. **Một item = một thay đổi.** Đổi CSS / font / ảnh / thứ tự script đều có thể làm vỡ giao diện hoặc tracking.
3. Build asset theo quy ước dự án (profile — vd build trong docker, asset qua pipeline của framework).
4. Kiểm **visual** (chụp mobile + desktop trước/sau), **tracking** (event / tag vẫn bắn), **SEO** (title, meta, structured data, nội dung không bị ẩn) theo `test-plan.md`. Lưu ảnh chụp + kết quả vào `$WS/6-testing/results/item{N}-{yyyymmdd}/`.
5. **Đo sau** → điền *Kết quả* vào report PSI. Không đạt AC → không sang item kế.

## Guardrails

- **[HARD]** Không kết luận từ 1 lần chạy Lighthouse — median ≥ 5 lần.
- **[HARD]** Không xoá / hoãn / đổi tag bên thứ ba khi khách chưa duyệt. Hoãn tag tới sau tương tác làm **mất số liệu của người rời trang trước khi tương tác** — phải nói rõ đánh đổi này.
- **[HARD]** Không lazy-load ảnh LCP. Không ẩn nội dung để "ăn điểm" — ảnh hưởng SEO và người dùng thật.
- Đừng tối ưu chỉ số đã ở mức tốt; theo thứ tự trọng số × khoảng cách.
- Lab tốt mà field xấu → tin field (đó là người dùng thật); tìm nguyên nhân ở thiết bị / mạng / trang người dùng thật hay vào.
