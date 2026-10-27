# backend-perf — playbook

Công thức cụ thể cho từng bước điều tra. Ví dụ code theo Laravel/PHP + PostgreSQL; phương pháp dùng cho stack khác được.

## §1. Tách TTFB

Đọc report của `measure-ttfb.sh`:

| Cột | Nghĩa | Nếu cao |
|---|---|---|
| Network | DNS + TCP + TLS | Mạng / CDN / vùng đặt server — không phải việc của code |
| Server | starttransfer − pretransfer | Server xử lý + hàng đợi → điều tra tiếp §2 |
| Cold − Warm | chênh lần đầu và lần sau | Cache đang gánh — xem §7 cho trường hợp cache miss |

TTFB > ngân sách mà *Server* < 200ms → dừng điều tra backend, chuyển sang mạng/hạ tầng (CloudFront, vùng, TLS, redirect).

## §2. Profile một request

**Đếm query + tổng thời gian SQL** — code tạm, chỉ ở local/dev, **không commit**:

```php
// AppServiceProvider::boot() — TẠM THỜI
if (config('app.debug')) {
    $q = 0; $ms = 0.0;
    \DB::listen(function ($e) use (&$q, &$ms) { $q++; $ms += $e->time; });
    app()->terminating(function () use (&$q, &$ms) {
        \Log::debug('perf', ['uri' => request()->path(), 'queries' => $q, 'sql_ms' => round($ms, 1)]);
    });
}
```

**Thời gian từng use case** — bọc `hrtime(true)` quanh từng lời gọi trong controller, log ra ms.

Công cụ local: Laravel Debugbar / Telescope (xem từng query, query lặp, thời gian). Eloquent: `Model::preventLazyLoading(! app()->isProduction())` để bắt lazy load sớm.

**Đọc kết quả:**
- Số query tăng theo số bản ghi trên trang (20 tin → 20+ query) → N+1 (§6.1).
- Cùng một câu chạy nhiều lần trong 1 request → query lặp, cần memo (§6.4).
- SQL time nhỏ nhưng request chậm → thời gian nằm ở PHP: render, serialize, gọi ngoài, log (§6.5, §6.6).

## §3. Xếp hạng SQL và đọc wait event

**pg_stat_statements** (`pg-top-queries.sql`): xếp theo **total_exec_time** — câu chậm vừa vừa nhưng chạy mỗi request thường đáng sửa hơn câu chậm chạy 1 lần/ngày. Câu đang treo ngay lúc này không có trong đó → xem `pg_stat_activity` (§7 của file SQL).

**RDS Performance Insights** (`rds_pi_snapshot.py`): DB load tính bằng *Average Active Sessions*. AAS vượt số vCPU kéo dài = DB quá tải.

| Wait event | Đọc là | Hướng |
|---|---|---|
| `CPU` | Câu lệnh tốn tính toán | Index, viết lại query, giảm sort/hash |
| `IO:DataFileRead` | Đọc dữ liệu từ đĩa | Index để bớt scan; RAM không đủ giữ working set |
| `Lock:transactionid` · `Lock:tuple` | Chờ ghi / khoá | Transaction dài, batch chồng giờ cao điểm |
| `Client:ClientRead` | DB chờ app gửi lệnh kế | App chậm giữa các câu trong cùng transaction |
| `IO:XactSync` · `IO:WALWrite` | Commit dày | Gộp ghi |
| `LWLock:BufferMapping` | Tranh buffer | Đọc lặp trên bảng nóng → cache tầng app |

## §4. Đọc EXPLAIN

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;            -- câu đọc
BEGIN; EXPLAIN (ANALYZE, BUFFERS) UPDATE ...; ROLLBACK;   -- câu ghi: ANALYZE THỰC THI câu lệnh
```

Chạy trên stg (dữ liệu gần prod). Dữ liệu dev ít → plan khác hẳn prod, kết luận sai.

| Thấy gì | Nghĩa là | Thường sửa bằng |
|---|---|---|
| `rows` ước lượng lệch `actual rows` ≥ 10× | Thống kê cũ, planner chọn sai | `ANALYZE <bảng>` (cần duyệt trên prod) |
| `actual time` × `loops` lớn | Thời gian ghi là **mỗi vòng** — nhân loops mới ra thật | Index cho điều kiện join |
| `Seq Scan` bảng lớn + `Rows Removed by Filter` nhiều | Thiếu index cho WHERE | Index (§5) |
| `SubPlan` chạy theo từng dòng | Subquery tương quan, vd `ARRAY(SELECT …)` trong SELECT | Viết lại bằng JOIN + `string_agg … GROUP BY` hoặc `LATERAL` |
| `Sort Method: external merge  Disk` | Sort tràn ra đĩa | Index đúng thứ tự ORDER BY, hoặc giảm số dòng trước khi sort |
| `Buffers: shared read` lớn | Dữ liệu không nằm trong RAM | Giảm số trang phải đọc (index, lấy ít cột hơn) |

Lưu plan **trước/sau** vào phần *Chi tiết kỹ thuật* của report — là bằng chứng, không phải trang trí.

## §5. Index

- Ứng viên lấy từ `WHERE` / `JOIN` / `ORDER BY` của top SQL — không đoán theo tên cột.
- Index nhiều cột: cột so sánh bằng (`=`) trước, cột khoảng / sort sau.
- **Partial index** cho điều kiện luôn có (vd `WHERE deleted_flg = '0'`) — nhỏ hơn, nhanh hơn.
- **Covering** (`INCLUDE (...)`) để được *index-only scan*.
- Mỗi index làm chậm ghi + tốn chỗ → kiểm index không dùng (`pg-top-queries.sql` §5) trước khi thêm cái mới.
- Prod: `CREATE INDEX CONCURRENTLY` — không khoá ghi, không chạy trong transaction; fail thì để lại index `INVALID` → phải kiểm và dọn.
- Bảng do hệ thống khác ghi (ETL, bên thứ ba) → index là thay đổi cần thống nhất với bên đó, ghi vào *Rủi ro*.

## §6. Code

**6.1 N+1 / query trong vòng lặp.** Gọi repository trong `foreach` → gom ID, query 1 lần (`WHERE id IN (…)` / eager load `with()`), map lại trong PHP. Với raw SQL không có lazy load để bắt — phải nhìn số query tăng theo số dòng (§2).

**6.2 Query trong view component.** Component tự gọi service lúc render chạy lại **theo từng lần render** — 20 thẻ = 20 lần. Chuẩn bị dữ liệu ở use case, truyền vào component.
⚠ Blade component: `data()` gộp public property **và** public method (method ghi đè property cùng tên) — refactor component phải giữ tên, đổi tên là đổi dữ liệu view nhận.

**6.3 Lấy thừa.** `SELECT *`, lấy cả bảng rồi lọc trong PHP, lấy cột lớn (text/json) không dùng → chỉ lấy cột cần, lọc ở SQL, phân trang.

**6.4 Đếm đắt / query lặp.** `COUNT(*)` trên bảng lớn mỗi lần render → cache số đếm, hoặc tái dùng số đã có. Cùng một câu chạy nhiều lần trong 1 request → memo trong request (thuộc tính của service singleton).

**6.5 Việc đồng bộ trên request.** Ghi DB mỗi lượt xem (bộ đếm truy cập…), gửi mail, gọi API ngoài, ghi log lớn — tất cả cộng thẳng vào TTFB và **không được cache che**. Hướng: đẩy sang queue, `dispatch(...)->afterResponse()`, hoặc gom bằng batch. Phải hỏi: số đếm có cần chính xác tức thì không, mất vài lượt khi queue lỗi có chấp nhận được không.

**6.6 Log và serialize trong hot path.** Log từng bước của request, đo kích thước bằng `serialize()` để log, serialize payload lớn vào cache — tốn CPU mỗi request. Bỏ log không ai đọc; log tóm tắt thay vì toàn bộ.

## §7. Cache

1. **Có bật thật không?** Kiểm gate cấu hình — vd một TTL toàn cục ≤ 0 tắt hết cache phụ dù TTL riêng đã đặt.
2. **Hit rate** (ElastiCache `CacheHits / (Hits + Misses)` — `cloudwatch_snapshot.py`). Thấp → key không ổn định (tham số UTM, thứ tự tham số, cookie) hoặc TTL quá ngắn. Kiểm bằng `UTM_CHECK` của `measure-ttfb.sh`.
3. **Cache kết quả rỗng/null không?** Không → trang tính lại mỗi request đúng ở chỗ dữ liệu trống. (Bug thật ở task trước — xem §9.)
4. **Nhiều GET lẻ → gộp 1 lần** (`Cache::many` / MGET). Mỗi GET là một vòng mạng tới Redis (vài ms nếu Redis ở máy khác, có TLS).
5. **Stampede:** nhiều key hết hạn cùng lúc → hàng loạt request cùng tính lại. Thêm jitter cho TTL, hoặc lock / refresh sớm.
6. **Invalidation:** dữ liệu đổi thì cache xoá ở đâu? TTL dài = rủi ro dữ liệu cũ — ghi vào *Rủi ro*.
7. **Payload quá lớn:** serialize tốn CPU + băng thông Redis → cache phần cần, không cache cả object.
8. **Dữ liệu theo người dùng** (yêu thích, lịch sử) không được cache chung.
9. **Preload trong request:** service cache bind `singleton` để dữ liệu nạp 1 lần dùng chung cả request (web). Cẩn thận ở queue worker / Octane — singleton sống qua nhiều request.

## §8. Runtime

- `php artisan optimize` (config / route / view / event cache) trong image; `composer install --no-dev --optimize-autoloader`. Đã cache config thì `env()` ngoài file config trả `null`.
- OPcache bật; prod `validate_timestamps=0` (xoá cache khi deploy); `memory_consumption` / `max_accelerated_files` đủ cho codebase.
- PHP-FPM `pm.max_children` theo CPU/RAM của task: nhiều quá → tranh CPU, ít quá → request xếp hàng (TTFB tăng mà SQL không đổi).
- Tổng kết nối DB = số task × `max_children` (× pool) **< 70% `max_connections`**. Chạy tốt ở 2 task, sập ở 10.
- Octane bỏ được chi phí khởi động framework mỗi request, nhưng mọi singleton sống qua request → rò state. Bước cuối, cần review toàn bộ singleton.

## §9. Bài học từ dự án trước — SHOKAI_ARCH_2506-76 (kaigo, trang tìm việc)

| Phase | Đã làm | Kết quả |
|---|---|---|
| 1 — prod 23/06/2026 | Cache dữ liệu phụ (FAQ, review, thống kê tỉnh, banner…) với TTL riêng theo loại · gộp các lần đọc cache thành 1 MGET · sửa bug **cache null** của banner vùng (rỗng → tính lại mỗi request) · bỏ `serialize()` đo kích thước để ghi log · gộp helper sinh key trùng lặp | Prod warm median **−19%** (369 → 300ms); trang lọc theo tỉnh −20%, trang khác −12%; Tokyo 655 → 302ms |
| 2 — main 21/07/2026 | Dùng lại cache đếm job · dùng lại dữ liệu city · tối ưu render thẻ job · giảm log + dọn SQL | Lần đầu (đã xoá cache trước khi đo) trung bình 5,798 → 393ms (−93%); ALB trung bình theo ngày 1.4–2.2s → 0.22–0.39s |
| Đo lại 22/10/2026 (PERF-20261022) | Không đổi code — điều tra "search vẫn chậm" | Lần đầu lại 0.7–8.5s **chỉ trong 04:00–15:00 JST**: Applebot crawl ~107k req/h, 73% URL tìm kiếm không lặp → cache miss, DB reader CPU 99%. Ngoài khung vẫn như sau Phase 2. Xem §10 |

**Bài học đo:**
- TTFB đo từ client nhiễu (mạng + tải stg) — che mất mức tiết kiệm vài chục ms. So bằng **warm min**, đo before/after cùng môi trường, cùng giờ.
- Kiểm URL có UTM: nếu chậm hơn URL sạch rõ rệt → cache key đang chứa tham số tracking.
- Muốn số server thuần, không nhiễu mạng → đo từ trong VPC (hoặc ALB `TargetResponseTime`).
- Cải thiện cache chủ yếu thấy ở lần truy cập **sau** — lần đầu (cache trống) vẫn phải tính; muốn cải thiện lần đầu phải tối ưu query.
- Muốn đo lần đầu (cache miss) thật: **xoá cache sau lượt before** rồi mới đo after, hoặc dùng URL chưa ai truy cập (`measure-ttfb.sh miss`). Before và after cách nhau ít hơn TTL mà không xoá cache → after đọc cache của before.
- "Chậm lại" sau khi đã tối ưu → khoanh vùng trước (`perf-measure` §Khoanh vùng): lần 22/10 nguyên nhân là crawler, không phải code thoái hoá.

## §10. Tải từ crawler / bot

Dấu hiệu: lượng request tăng theo **bậc**, chạy theo **khung giờ cố định** (bật / tắt đúng giờ chẵn), trang chậm **chỉ trong khung đó**, CPU DB đọc cao mà đọc RAM ~100%.

1. **Xác định ai:** access log (ALB / CloudFront) đếm theo user agent, loại URL, tỉ lệ URL không lặp — [`infra-check`](../../infra-check/SKILL.md) mục 2. Đứng sau CloudFront thì IP thật ở CloudFront log.
2. **Bot thật hay giả:** IP thuộc dải nhà cung cấp (Apple 17.0.0.0/8; Google, Bing có danh sách công bố) hoặc reverse DNS khớp. Giả → chặn được (WAF); thật → phải cân nhắc SEO.
3. **Vì sao cache vô dụng:** trang có bộ lọc (tỉnh × nghề × bằng cấp × … × trang) sinh ra **số URL gần như vô hạn**; crawler đi từng tổ hợp, mỗi URL chỉ 1 lần → gần như toàn miss, mọi lượt đều chạy query nặng.
4. **Hướng xử lý — từ rẻ tới đắt, đều cần người phụ trách SEO phía khách quyết:**

   | Cách | Tác dụng | Đánh đổi |
   |---|---|---|
   | `robots.txt` chặn tổ hợp sâu (vd ≥ 2 điều kiện, trang phân trang sâu) cho bot đó | bot không vào nữa | trang đó không còn trên công cụ của bot (Spotlight / Siri với Applebot). Kiểm bot có hỗ trợ wildcard không |
   | `noindex` / `canonical` cho tổ hợp sâu | ít giá trị nếu bot vẫn tải trang | không giảm tải ngay |
   | Không sinh link tới tổ hợp sâu trong HTML (link bộ lọc qua form / JS) | bot không tìm thấy URL mới | đổi giao diện, ảnh hưởng crawl của Google |
   | Giới hạn tốc độ theo bot (WAF rate-based rule) | chặn đỉnh | bot có thể bị 429 → crawl ít đi; cấu hình là việc của infra |
   | Tăng sức DB đọc (thêm reader, reader lớn hơn) | chịu được tải | chi phí; không sửa gốc |
   | Tối ưu query khi miss (§4–§6) | mỗi lượt miss rẻ hơn | công sức lớn nhất, nhưng có lợi cho cả người dùng thật |

5. Ghi vào report: bot nào, bao nhiêu request / giờ, từ ngày nào, chiếm bao nhiêu % tải, các cách trên kèm **ai quyết**. Team không tự đổi robots.txt / WAF / hạ tầng khi chưa có quyết định.
