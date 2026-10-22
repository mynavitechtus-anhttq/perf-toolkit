-- pg-top-queries.sql — tìm câu SQL tốn nhất và dấu hiệu thiếu/thừa index. CHỈ SELECT.
--
-- Chạy:   psql "$DATABASE_URL" -v lim=20 -f pg-top-queries.sql > pg-top.txt
-- Nơi chạy: stg (dữ liệu gần prod) hoặc read replica. Prod primary chỉ khi người phụ trách duyệt.
-- Cột *_exec_time dùng cho PostgreSQL 13+; bản cũ hơn đổi thành total_time / mean_time.
-- Số liệu cộng dồn từ lần reset gần nhất (xem dòng stats_reset ở §0). Đừng tự reset trên prod.
\set ON_ERROR_STOP off
\if :{?lim} \else \set lim 20 \endif
\pset null '-'

\echo '== §0. pg_stat_statements có bật không (không có thì dừng — CREATE EXTENSION là thay đổi, cần duyệt) =='
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_stat_statements';
SELECT stats_reset FROM pg_stat_statements_info;   -- PG14+; bản cũ hơn sẽ báo lỗi ở dòng này, các mục sau vẫn chạy

\echo '== §1. Top theo TỔNG thời gian — chậm × nhiều lần. Đây là danh sách nên xem trước tiên =='
SELECT round(total_exec_time::numeric / 1000, 1)                             AS total_s,
       calls,
       round(mean_exec_time::numeric, 2)                                     AS mean_ms,
       round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 1) AS pct,
       rows / NULLIF(calls, 0)                                               AS rows_per_call,
       round(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 1) AS hit_pct,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200)                     AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT :lim;

\echo '== §2. Top theo thời gian TRUNG BÌNH (calls >= 50) — từng lần chạy chậm =='
SELECT round(mean_exec_time::numeric, 2) AS mean_ms,
       round(max_exec_time::numeric, 2)  AS max_ms,
       calls,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200) AS query
FROM pg_stat_statements
WHERE calls >= 50
ORDER BY mean_exec_time DESC
LIMIT :lim;

\echo '== §3. Đọc đĩa nhiều nhất (shared_blks_read) — dữ liệu không nằm trong RAM =='
SELECT shared_blks_read, shared_blks_hit, calls,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200) AS query
FROM pg_stat_statements
ORDER BY shared_blks_read DESC
LIMIT :lim;

\echo '== §4. Bảng bị seq scan nhiều — ứng viên thiếu index (bảng lớn + seq_tup_read cao) =='
SELECT relname,
       n_live_tup,
       seq_scan, seq_tup_read,
       idx_scan,
       round(100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0), 1) AS idx_pct,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE n_live_tup > 10000
ORDER BY seq_tup_read DESC
LIMIT :lim;

\echo '== §5. Index không được dùng — tốn chỗ + làm chậm ghi (đừng xoá index phục vụ UNIQUE/PK) =='
SELECT s.relname AS table_name, s.indexrelname AS index_name, s.idx_scan,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size,
       i.indisunique AS is_unique
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0
ORDER BY pg_relation_size(s.indexrelid) DESC
LIMIT :lim;

\echo '== §6. Cache hit ratio toàn DB (OLTP thường > 99%) =='
SELECT datname,
       round(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS hit_pct
FROM pg_stat_database
WHERE datname = current_database();

\echo '== §7. Câu đang chạy lâu ngay lúc này (pg_stat_statements chỉ ghi câu đã chạy xong) =='
SELECT pid, now() - query_start AS running_for, state, wait_event_type, wait_event,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200) AS query
FROM pg_stat_activity
WHERE state <> 'idle' AND query_start < now() - interval '5 seconds' AND pid <> pg_backend_pid()
ORDER BY query_start;

\echo '== §8. Bảng lớn nhất (dung lượng gồm index + TOAST, số dòng ước tính) =='
SELECT relname,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
       pg_size_pretty(pg_relation_size(relid))       AS table_size,
       n_live_tup                                    AS est_rows,
       n_dead_tup                                    AS dead_rows,
       last_autoanalyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT :lim;
