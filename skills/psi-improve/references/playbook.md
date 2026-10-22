# psi-improve — playbook

Mỗi mục: **thấy gì trong LHR** → **nghĩa là gì** → **sửa thế nào**. Nguồn tổng hợp ở cuối.

## §1. Điểm mất ở đâu

Điểm hiệu năng (Lighthouse 10+) = tổng có trọng số của 5 điểm thành phần; mỗi điểm thành phần quy từ giá trị metric qua đường cong log-normal.

| Chỉ số | Trọng số | Tốt (mobile) | Kém |
|---|---:|---|---|
| TBT | 30% | ≤ 200ms | > 600ms |
| LCP | 25% | ≤ 2.5s | > 4.0s |
| CLS | 25% | ≤ 0.1 | > 0.25 |
| FCP | 10% | ≤ 1.8s | > 3.0s |
| SI | 10% | ≤ 3.4s | > 5.8s |

**Ưu tiên = trọng số × khoảng cách tới mức tốt.** TBT 900ms (trọng số 30) thường đáng làm hơn FCP 2.2s (trọng số 10). Ước điểm sau sửa bằng [Lighthouse Scoring Calculator](https://googlechrome.github.io/lighthouse/scorecalc/) — nhập giá trị mục tiêu, ra điểm.

## §2. LCP — tách 4 phần

`measure_psi.py` ghi *LCP element* và *LCP subparts* của run đại diện.

| Subpart | Là gì | Mục tiêu | Phình vì | Sửa |
|---|---|---|---|---|
| TTFB | Server trả HTML | ~40% | Server chậm, redirect, không cache | → `backend-perf`; CDN; bỏ redirect |
| Load delay | Từ TTFB tới khi bắt đầu tải tài nguyên LCP | < 10% | Ảnh không có trong HTML ban đầu (CSS background, JS chèn), bị lazy-load | Đặt `<img>` thẳng trong HTML · `fetchpriority="high"` · `<link rel="preload">` · **bỏ `loading="lazy"` ở ảnh LCP** |
| Load duration | Tải chính tài nguyên LCP | ~40% | Ảnh to, định dạng cũ, không qua CDN | Đúng kích thước hiển thị (`srcset`/`sizes`) · WebP/AVIF · nén · CDN |
| Render delay | Tải xong tới khi vẽ | < 10% | CSS/JS chặn render, phần tử bị ẩn chờ JS, font chưa tải | Critical CSS · `defer` JS · đừng ẩn phần tử LCP chờ JS |

⚠ Rút ngắn load duration mà phần tử vẫn bị ẩn chờ JS thì render delay tăng tương ứng — LCP không đổi. Luôn nhìn cả 4 phần.

## §3. TBT / INP — ai chiếm main thread

**Thấy gì:** `third-party-summary` (blocking time theo đơn vị cung cấp) · `bootup-time` (thời gian chạy từng script) · `mainthread-work-breakdown` · `unused-javascript` · `long-tasks`.

**Tag bên thứ ba** (GTM, GA, quảng cáo, chat, A/B test, heatmap) — thường là nguồn TBT số 1 ở trang tuyển dụng / thương mại:
1. **Kiểm kê trước khi tối ưu:** liệt kê tag trong GTM, tag nào còn dùng, ai chủ. Bỏ tag chết là cách rẻ nhất.
2. Tag không cần ngay → kích hoạt muộn hơn (trigger sau khi trang tải xong, hoặc sau tương tác đầu tiên).
   ⚠ **Đánh đổi:** tag chờ tương tác **bỏ lỡ người rời trang không tương tác** → số liệu analytics/quảng cáo giảm. Khách phải duyệt.
3. Tag không đụng DOM → `async`. Domain bắt buộc giữ → `preconnect`.

**JS của mình:**
- Tách bundle theo trang (code splitting của build tool) — trang chi tiết không cần JS của trang tìm kiếm.
- Bỏ thư viện chỉ dùng một hàm; thư viện cũ (plugin jQuery, slider) thay bằng CSS / API trình duyệt khi được.
- Script không cần cho lần vẽ đầu → `defer` / `type="module"`.

**Long task (> 50ms) — cho INP:** chia việc lớn thành các đoạn < 50ms, nhường main thread giữa các đoạn (`await scheduler.yield()`, có fallback `setTimeout(0)` cho trình duyệt chưa hỗ trợ). Trong handler click: cập nhật UI trước, việc nặng (gửi `dataLayer`, tính toán) để sau.

## §4. CLS — cái gì nhảy

**Thấy gì:** `layout-shifts` / `layout-shift-elements` — phần tử và điểm shift.

| Nguyên nhân | Sửa |
|---|---|
| Ảnh / iframe / video thiếu kích thước | `width` + `height` trên thẻ, hoặc `aspect-ratio` trong CSS |
| Banner / quảng cáo chèn muộn | **Giữ chỗ trước** bằng `min-height` / `aspect-ratio` theo kích thước hay gặp nhất. Khoảng trắng thừa không tính vào CLS |
| Banner cookie / app chèn đẩy nội dung | Dùng lớp phủ `position: fixed` thay vì chèn vào luồng |
| Web font thay font dự phòng làm chữ reflow | Font dự phòng khớp số đo (`size-adjust`, `ascent-override`, `descent-override`) · cân nhắc `font-display: optional` cho font không quan trọng |
| Carousel / slider khởi tạo sau khi vẽ | Đặt kích thước khung trước, khởi tạo không đổi layout |
| Nội dung chèn trên nội dung đang hiển thị | Chèn bên dưới, hoặc chỉ chèn sau tương tác |

## §5. FCP / SI — chặn render

- **`render-blocking-resources`:** CSS lớn trong `<head>` → tách **critical CSS** (phần màn hình đầu) inline, phần còn lại tải không chặn. ⚠ Làm sai gây nháy giao diện chưa style (FOUC) → visual test bắt buộc.
- JS đồng bộ trong `<head>` → `defer`.
- Chuỗi redirect (http → https → www → path) → mỗi bước một vòng mạng; trỏ thẳng URL cuối.
- `preconnect` tới domain tài nguyên quan trọng (font, CDN ảnh); đừng preconnect quá 3–4 domain.

## §6. Font tiếng Nhật

Font Nhật nặng hơn font Latin 1–2 bậc: Noto Sans JP bản đầy đủ khoảng **3.4MB mỗi độ đậm**.

| Cách | Khi nào | Lưu ý |
|---|---|---|
| Dùng font hệ thống (Hiragino / Yu Gothic / Noto có sẵn trên máy) | Thiết kế chấp nhận được | Rẻ nhất. Một case study: LCP mobile 11.0s → 5.7s chỉ nhờ bỏ Noto Sans JP trên điện thoại |
| Google Fonts (tự chia ~100+ lát theo `unicode-range`) | Cần font web | Trang dùng ký tự rải nhiều lát vẫn tải nhiều lát |
| Tự subset (vd kanji JIS cấp 1 ~3.000 chữ) + `unicode-range` | Tự host | Thiếu chữ → hiện font dự phòng; cần kiểm nội dung thật |
| Giảm số độ đậm (2–3) | Luôn | Mỗi độ đậm là một bộ file riêng |

Luôn có `font-display` (`swap` hoặc `optional`) để chữ không biến mất khi chờ font. Đo trước/sau trên chính trang — số liệu ngoài chỉ để định hướng.

## §7. Ảnh

- Kích thước tải đúng kích thước hiển thị (`srcset` + `sizes`) — ảnh 1600px hiển thị 400px là lãng phí 16 lần pixel.
- WebP / AVIF, nén hợp lý.
- `loading="lazy"` **chỉ cho ảnh dưới màn hình đầu**.
- Ảnh LCP: `fetchpriority="high"`, không lazy, có trong HTML ban đầu.
- Ảnh từ CMS / người dùng tải lên thường không tối ưu sẵn → cần bước xử lý ảnh (lúc upload, lúc build, hoặc ở tầng CDN).

## §8. Mạng, CDN, cache

- Asset có hash trong tên file → `Cache-Control: public, max-age=31536000, immutable` ở CDN.
- Nén brotli / gzip cho HTML, CSS, JS, JSON, SVG (`uses-text-compression`).
- HTTP/2 hoặc HTTP/3 ở CDN.
- **bfcache** (back/forward cache): HTML trả `Cache-Control: no-store`, hoặc có handler `unload` → trang không vào được bfcache, mỗi lần bấm Back là tải lại từ đầu. Audit `bf-cache` chỉ ra lý do.
- Dùng `cloudwatch_snapshot.py --cloudfront` để xem cache hit rate của CDN (cần bật additional metrics).

## §9. DOM và render

- DOM lớn (`dom-size`, thường > 1.400 node là nhiều): danh sách dài → phân trang / giới hạn số thẻ; vùng dưới màn hình → `content-visibility: auto`.
- Khởi tạo slider / carousel / tab lúc tải → chỉ khởi tạo cái nhìn thấy.

## §10. Lab và field

- Lab (Lighthouse) là phòng thí nghiệm: một máy, một mạng, không cache, không có người dùng. Field (CrUX) là người dùng thật, p75, 28 ngày.
- Lab tốt, field xấu → tin field; nguyên nhân thường ở thiết bị yếu hơn, trang người dùng hay vào khác trang đang đo, hoặc tương tác (INP) mà lab không đo được.
- Field scope `origin` = URL không đủ traffic, số là của cả domain → không dùng làm AC cho từng trang.
- Sau release: field cần **tới 28 ngày** mới phản ánh đủ. Ghi mốc này vào lịch (`planning`) và vào report cho khách.

## §11. Ràng buộc không được phá

- **Tracking:** sau mỗi thay đổi script / tag, kiểm event vẫn bắn (`dataLayer`, request tới endpoint analytics trong Network). Mất tracking conversion = sự cố.
- **SEO:** title, meta, structured data, canonical không đổi; không ẩn nội dung; không đổi URL.
- **Giao diện:** chụp màn hình mobile + desktop trước/sau, so sánh — CSS / font / critical CSS dễ làm lệch.

## Nguồn

- [web.dev — Optimize LCP](https://web.dev/articles/optimize-lcp) · [Lighthouse — LCP](https://developer.chrome.com/docs/lighthouse/performance/lighthouse-largest-contentful-paint) · [Smashing — LCP subpart analysis](https://www.smashingmagazine.com/2025/03/how-to-fix-largest-contentful-issues-with-subpart-analysis/)
- [web.dev — Optimize CLS](https://web.dev/articles/optimize-cls)
- [Lighthouse variability](https://github.com/GoogleChrome/lighthouse/blob/main/docs/variability.md) · [Lighthouse Scoring Calculator](https://googlechrome.github.io/lighthouse/scorecalc/)
- [DebugBear — INP](https://www.debugbear.com/docs/metrics/interaction-to-next-paint) · [Crystallize — fast GTM](https://crystallize.com/blog/fast-loading-google-tag-manager)
- [Japanese font delivery (note.com)](https://note.com/ngsm/n/na9662a22f9e6?hl=en) · [Case study: bỏ Noto Sans JP trên mobile](https://github.com/daiyanog-del/tcg-price-compare/pull/91)
