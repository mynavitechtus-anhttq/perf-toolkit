# Profile — kaigo (介護求人 renewal)

Mẫu profile cho dự án khác: copy file này, thay nội dung, giữ nguyên các mục.

## Knowledge base

| | |
|---|---|
| Repo | `git@bitbucket.org:nal-solutions/kaigo-doc.git` |
| Nhánh | `main` |
| Bản local (chỉ đọc, dùng khi không clone được) | `~/Documents/nals/projects/mynavi-pj/SSOT-docs/kaigo-doc` — thường đang ở nhánh khác, kiểm ngày commit cuối |
| Mục lục nguồn | `memory/source-index.md` |
| Spec màn | `analysis/business/technical/screens/SCR-*.md` — `SCR-JS-01` tìm việc · `SCR-JD-01` chi tiết tin · `SCR-HO-01` trang chủ · `SCR-RK` ranking · `SCR-LP` landing · `SCR-ST` static · `SCR-ET` entry · `SCR-personalization` |
| DB spec | `analysis/technical/db-specs/*.md` (`job-offer`, `master`, `mnv`, `batch`, `entry`, `company`, `erd`…) |

## Môi trường

| Env | URL | Basic Auth | Đo PSI bằng |
|---|---|---|---|
| prod | `https://kaigoshoku.mynavi.jp` (không có `www`) | không | `--engine psi` |
| stg | `https://stg.kaigoshoku.mynavi.jp` | **có, toàn site** | `--engine lighthouse` + `BASIC_AUTH` |
| dev1 | `https://dev1.kaigoshoku.mynavi.jp` (= nhánh `develop`) | **có, toàn site** | `--engine lighthouse` + `BASIC_AUTH` |

Basic Auth: hỏi người dùng, đặt vào env (`AUTH` / `BASIC_AUTH`), không ghi vào file.

## Route chính

| Trang | Route | Controller |
|---|---|---|
| Trang chủ | `/` | `HomeController@index` |
| Tìm việc | `/r/{searchParams?}` — vd `/r/pr_tokyo`, `/r/pr_tokyo/cf_050390/pg_2` (bare `/r/` → 404) | `JobSearchController@index` |
| Chi tiết tin | `/d/{recruitno}` (chỉ số; tin không tồn tại → 404) | `JobDetailController@index` |

Gợi ý `pages.tsv` cho trang chi tiết: lấy `recruitno` thật đang mở trên env đo, phủ tin có / không ảnh, tin công khai / ẩn danh (`job_ofr_st_cd` 01 / 02).

## Stack

- Laravel 12 DDD: `src/{Module}/{Application,Domain,Infrastructure,Presentation}`.
- PostgreSQL trên RDS — schema tham chiếu `kgk-renew-kaigoshoku-sys-batch/ecs/schema.sql`. Movable Type CMS dùng MySQL riêng (connection `movabletype`).
- Cache: ElastiCache Redis (TLS) · chạy trên ECS Fargate · CloudFront phía trước · static CMS trên EFS.
- Repo liên quan: web `kgk-renew-kaigoshoku-sys-web` · batch `kgk-renew-kaigoshoku-sys-batch` · hạ tầng CDK `kaigo-infra`.
- Asset qua Vite (`vite.config.js` + `@vite()`), **build trong docker** (node_modules dùng chung Mac ↔ Linux).

## Tài nguyên AWS

| Loại | Tên / ID |
|---|---|
| AWS profile | `TBD` |
| RDS instance (prod / stg) | `TBD` — dò bằng `cloudwatch_snapshot.py --list` |
| ElastiCache cluster | `TBD` |
| ALB | `TBD` |
| ECS cluster / service web | `TBD` |
| CloudFront distribution | `TBD` |

## Quy ước code khi implement

- Repository viết raw SQL (`DB::select`) — giữ style, không đổi sang Eloquent.
- Cache qua `JobCacheService` / kế thừa `AbstractCacheService`, không gọi `Cache::` thẳng trong use case.
- `src/Shared/…` dùng chung nhiều module — sửa phải xét mọi nơi gọi.

## Gotcha đã biết

- **Cache gate:** `config('job.cache.ttl')` = env `JOB_SEARCH_CACHE_TTL` (mặc định 0). `≤ 0` → **tắt toàn bộ cache phụ**, TTL riêng từng loại bị bỏ qua. Trang chi tiết (`rememberJobDetail`) cũng đi qua TTL này.
- **Trang chi tiết ghi DB mỗi lượt xem:** `JobDetailController` gọi `recordJobAccess()` → `IncrementJobAccessCountUseCase` → `incrementCount()` **đồng bộ trong request**, ngoài phạm vi cache. Nghi vấn hotspot — cần đo.
- `JobCacheService` bind singleton để preload MGET dùng chung trong 1 request (web; không dùng ở queue).
- Blade component `data()` gộp public property + public method; method ghi đè property cùng tên.
- **Dữ liệu tin tuyển do hệ thống bên thứ ba của khách ghi** (import / update / delete); kaigo chỉ đọc. Thêm index trên bảng tin = thay đổi phải thống nhất với khách.
- Batch ghi `batch_data` vào DB, web tự cache vào Redis.

## Bài học dự án trước

SHOKAI_ARCH_2506-76 (tối ưu trang tìm việc, 2 phase) — xem [`backend-perf` playbook §9](../skills/backend-perf/references/playbook.md).
