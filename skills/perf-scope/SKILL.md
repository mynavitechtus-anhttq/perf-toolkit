---
name: perf-scope
description: >-
  Step 1 of perf-toolkit — define the performance scope of one or more web pages BEFORE anything is
  measured or changed. Syncs the project's knowledge base (clone/pull the doc repo, e.g. kaigo-doc), reads
  the screen spec, data source and DB spec of every target page, maps page → route → controller → use
  cases → queries/tables → cache → synchronous writes → external calls → batch that feeds the data →
  view components → assets and third-party tags, picks representative URLs (pages.tsv) and lists the
  questions the customer must answer (which pages, mobile or desktop, lab or field, target numbers). Use it
  whenever a performance or PageSpeed/PSI improvement task starts — "cải thiện performance trang X",
  "cải thiện điểm PSI", "trang chi tiết chậm", "khảo sát phạm vi perf", "chuẩn bị cải thiện tốc độ" — even
  if the user jumps straight to "đo" or "tối ưu". Works for any page, not only search.
---

# perf-scope — phạm vi trước khi đo

> Luồng, workspace, profile, an toàn: [`../_shared/workflow.md`](../_shared/workflow.md).
> Ai nghĩ, ai gõ: chốt phạm vi là của người phụ trách và khách; AI đọc tài liệu, đối chiếu code, soạn nháp.

## Bước 1 — Nạp profile dự án

Theo thứ tự trong `workflow.md`. Cần ít nhất: knowledge base (repo, nhánh, đường dẫn spec) và môi trường.

## Bước 2 — Đồng bộ knowledge base

Clone vào **cache riêng của plugin**, không đụng bản làm việc của người dùng (họ có thể đang ở nhánh khác, có thay đổi chưa commit):

```bash
KB=~/.cache/perf-toolkit/<project>-doc
if [ -d "$KB/.git" ]; then git -C "$KB" pull --ff-only
else git clone --depth 1 -b <branch> <repo> "$KB"; fi
git -C "$KB" log -1 --format='%h %ad %s' --date=short     # ghi vào scope.md
```

Clone/pull lỗi (máy không có SSH key cho repo…) → đọc **bản local** trong profile, **chỉ đọc**; ghi nhánh + ngày commit cuối vào `scope.md` thành rủi ro *"tài liệu có thể cũ"*, và đề nghị người dùng pull. Không tự checkout/pull trên bản làm việc của họ.

## Bước 3 — Đọc tài liệu theo thứ tự

1. **Mục lục nguồn** → biết tài liệu nào có, nằm đâu.
2. **Spec màn** của từng trang: khối/element, nguồn dữ liệu / API, states, error.
3. **DB spec** của các bảng trang đọc / ghi.
4. **Data flow / batch**: ai ghi dữ liệu trang đọc, chạy lúc nào, bảng có do hệ thống khác sở hữu không.

Tài liệu nói một đằng, code một nẻo → ghi `[Lệch doc–code]`; **code là sự thật hiện hành**.

## Bước 4 — Đối chiếu code (nhẹ — chưa điều tra sâu)

Repo có `.codegraph/` → dùng codegraph trước grep. Với mỗi trang, điền bảng phụ thuộc trong template:

| Lớp | Hỏi gì |
|---|---|
| Route / controller | Controller gọi bao nhiêu use case, tuần tự hay không |
| Use case → repository | Query nào, bảng nào |
| Cache | Key gì, TTL bao nhiêu, **có thực sự bật không** (gate cấu hình) |
| Việc ghi đồng bộ trên request | Có ghi DB / gửi mail / gọi ngoài ngay trong request không |
| Gọi ngoài | API bên thứ ba, có timeout không |
| Batch cấp dữ liệu | Batch nào ghi, chạy lúc nào |
| View component | Component nào tự gọi service / query trong lúc render |
| Asset | Entry JS/CSS nào, font, ảnh lớn |
| Tag bên thứ ba | GTM, analytics, quảng cáo, chat widget |

Chỉ ghi **nghi vấn** ở bước này — chứng minh để dành cho `backend-perf` / `psi-improve`.

## Bước 5 — Chọn URL đại diện (`pages.tsv`)

Mỗi nhóm trang 2–5 URL, phủ biến thể **nặng và nhẹ**: có ảnh / không ảnh · nhiều / ít dữ liệu · trang 1 / trang N · nhiều điều kiện lọc · trạng thái đặc biệt (ẩn danh, hết hạn…).
Định dạng `path<TAB>nhãn<TAB>nhóm` — mẫu `$PLUGIN/templates/pages.example.tsv`. URL phải trả 200 trên môi trường sẽ đo.

## Bước 6 — Câu hỏi phải chốt với khách

Ghi vào `scope.md`, mỗi câu kèm *vì sao cần*:

- Trang nào? Thiết bị nào (mobile / desktop)?
- "Điểm PSI" là **lab score** hay **Core Web Vitals của người dùng thật (field)**? Hai thứ đo khác nhau, nghiệm thu khác nhau.
- Mục tiêu bao nhiêu? Nghiệm thu bằng **median 5 lần** (điểm lab dao động ±5–10 giữa các lần).
- Được đo prod không, khung giờ nào?
- Ai duyệt thay đổi tag marketing (GTM…)?
- Bảng dữ liệu trang đọc do ai ghi — team có được thêm index không?

## Output & handoff

- `$WS/1-scope/scope.md` theo `$PLUGIN/templates/scope.md` + `$WS/1-scope/pages.tsv` (`workflow.md` §Workspace).
- Đề nghị 1 dòng: *"chạy `perf-measure baseline` cho pages.tsv?"* — không tự chạy, vì đo prod cần người dùng đồng ý.
