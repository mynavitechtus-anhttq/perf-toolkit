---
name: infra-check
description: >-
  Investigate the infrastructure side of a web performance problem on AWS, read-only — traffic volume by
  day and hour (ALB / CloudFront), who generates it (user agent, IP, URL type from access logs), latency
  p50/p95/p99, database load split by reader and writer (Aurora / RDS CPU, connections, buffer cache hit,
  IOPS), replica autoscaling history, top SQL and wait events (Performance Insights / CloudWatch Database
  Insights), DB configuration and how the app routes reads and writes, data volume and largest tables,
  cache hit rate. First asks whether the user works in the AWS Console or the AWS CLI, then gives
  step-by-step instructions for that choice. Use when "server chậm mà code không đổi", "traffic tăng",
  "DB quá tải", "RDS CPU cao", "xem performance insight", "top query", "ai đang crawl", "check infra",
  "điều tra hạ tầng", or when perf-measure shows high Server time.
---

# infra-check — điều tra hạ tầng (chỉ đọc)

> Luồng, workspace, an toàn: [`../_shared/workflow.md`](../_shared/workflow.md). Thuộc **bước 2** — gọi khi cột *Server* của TTFB cao, hoặc khi chậm mà code không đổi.
> Ai nghĩ, ai gõ: AI chỉ đường và gom số; kết luận và quyết định đổi hạ tầng là của người phụ trách + khách / infra team.

## Bước 0 — Hỏi trước khi làm

1. **Console hay CLI?** Hỏi người dùng, rồi chỉ in hướng dẫn của cách đã chọn.
   - **Console:** in đường dẫn màn hình cho từng mục (menu → tab → metric → thống kê → khoảng thời gian). Người dùng tự xem, gửi lại ảnh hoặc số.
   - **CLI:** in lệnh; được người dùng cho phép thì AI chạy. Cần profile: `aws sts get-caller-identity --profile <p>` để xác nhận đúng tài khoản trước.
2. **Câu hỏi đang cần trả lời** — chỉ làm các mục liên quan, không chạy hết cho có.
3. **Khung thời gian** — từ lúc nào thấy chậm; lấy rộng hơn để có mốc so sánh (vd từ trước lần release / cải thiện gần nhất).

Tên tài nguyên lấy từ profile dự án. Chưa có → `cloudwatch_snapshot.py --list` rồi ghi vào profile.

## An toàn (cứng)

- **Chỉ đọc:** `describe-*`, `get-*`, `list-*`, `s3 ls`, `s3 cp` (tải về máy). Không tạo, sửa, xoá tài nguyên nào — kể cả bật Performance Insights, đổi autoscaling, **tạo bảng Athena / Glue** (là tạo tài nguyên).
- **Access log có IP người dùng:** tải về scratchpad / thư mục tạm, chỉ đưa **số đã gộp** vào report, không lưu log gốc vào repo, xoá khi xong.
- Đề xuất đổi hạ tầng (thêm reader, đổi instance, WAF, robots.txt) → ghi vào report làm phương án, khách / infra team quyết.

## Các mục điều tra

### 1. Lượng truy cập và độ trễ theo thời gian

Trả lời: tăng từ ngày nào, có khung giờ bất thường không, chậm trùng với lúc đông không.

**Console:** CloudWatch → *Metrics* → *All metrics* → *ApplicationELB* → *Per AppELB Metrics* → chọn ALB:
- `RequestCount` — thống kê *Sum*, chu kỳ *1 hour* (xem trong ngày) hoặc *1 day* (xem xu hướng).
- `TargetResponseTime` — thống kê *p99* và *Average*, cùng chu kỳ.
- Khoảng thời gian: *Custom* → từ trước mốc nghi ngờ vài tuần. Đổi múi giờ hiển thị sang giờ khách (vd JST) ở góc phải.

**CLI:**
```bash
REPORT_TZ=Asia/Tokyo python3 $PLUGIN/scripts/cloudwatch_snapshot.py --profile <p> \
  --start <ISO UTC> --alb app/<name>/<id> --series day --out $RUN/cw-trend      # xu hướng theo ngày
REPORT_TZ=Asia/Tokyo python3 $PLUGIN/scripts/cloudwatch_snapshot.py --profile <p> \
  --hours 48 --alb app/<name>/<id> --series hour --out $RUN/cw-hour            # trong ngày
```

Đọc: tìm **bậc thang** (tăng đột ngột rồi giữ) và **khung giờ bật/tắt đúng giờ chẵn** — dấu hiệu máy tự động. Đối chiếu ngày tăng với lịch release (`git log --merges`).

### 2. Ai tạo ra lượng truy cập đó

Trả lời: user agent nào, IP nào, vào loại URL nào, URL có lặp lại không (không lặp → cache không đỡ được).

**Console:** S3 → bucket log → thư mục ALB (`AWSLogs/<account>/elasticloadbalancing/<region>/<yyyy>/<mm>/<dd>/`) → tải 2–3 file của 1 giờ trong khung nghi ngờ và 1 giờ ngoài khung → đếm trên máy (đoạn lệnh ở CLI bên dưới). Athena tiện hơn nhưng phải tạo bảng → hỏi infra team, không tự tạo.

**CLI:**
```bash
aws elbv2 describe-load-balancer-attributes --profile <p> --load-balancer-arn <arn> \
  --query 'Attributes[?starts_with(Key,`access_logs`)]'                        # log bật chưa, nằm ở đâu
aws s3 cp s3://<bucket>/<prefix>/AWSLogs/<acct>/elasticloadbalancing/<region>/<yyyy/mm/dd>/ <tmp>/in/ \
  --recursive --exclude '*' --include '*_<yyyymmdd>T<HH>*' --profile <p>      # 1 giờ (UTC)
python3 -I -c '
import gzip,glob,re,sys,collections
R=re.compile(r"^(?:\S+ ){12}\"[^\"]*\" \"([^\"]*)\"")
ua=collections.Counter()
for f in glob.glob(sys.argv[1]+"/*.gz"):
    for l in gzip.open(f,"rt",errors="replace"):
        m=R.match(l); ua[m.group(1)[:120] if m else "?"]+=1
for u,n in ua.most_common(15): print(n,u)' <tmp>/in
```
Đếm thêm theo loại URL (`/r/`, `/d/`, `/api/`…) và tỉ lệ URL không lặp bằng cách đổi nhóm trong đoạn lệnh.

Lưu ý:
- **Đứng sau CloudFront** thì IP trong ALB log là IP của CloudFront. IP thật nằm ở CloudFront log (cột `c-ip`) — xem `get-distribution-config --id <id> --query DistributionConfig.Logging`.
- **Xác minh bot thật hay giả:** IP phải thuộc dải của nhà cung cấp (Apple 17.0.0.0/8; Google, Bing có danh sách công bố) hoặc reverse DNS khớp tên miền của họ.

### 3. Tải DB — reader và writer

Trả lời: DB nghẽn ở đâu (CPU / connection / đĩa), reader hay writer, lúc nào.

**Console:** RDS → *Databases* → chọn **cluster** → tab *Monitoring* → `CPUUtilization`, `DatabaseConnections`, `BufferCacheHitRatio`, `ReadIOPS` theo từng instance. Nhớ chọn khung giờ trùng khung đông ở mục 1.

**CLI:**
```bash
REPORT_TZ=Asia/Tokyo python3 $PLUGIN/scripts/cloudwatch_snapshot.py --profile <p> \
  --hours 48 --db-cluster <cluster-id> --series hour --out $RUN/cw-db
```

Đọc:
- CPU reader cao + `BufferCacheHitRatio` ~100% + `ReadIOPS` thấp → **nghẽn CPU** (đếm, sắp xếp, nhóm trên tập lớn) — thêm RAM không giúp.
- `BufferCacheHitRatio` < 99% + `ReadIOPS` cao → **đọc đĩa nhiều** — thiếu RAM hoặc thiếu index.
- Connection chạm trần → pool / số worker app.

### 4. Replica có tự tăng giảm không

**Console:** RDS → cluster → tab *Logs & events* → *Auto scaling policies* (chỉ số theo dõi, ngưỡng, min/max). Lịch sử thêm / bớt replica: RDS → *Events*, lọc theo cluster.

**CLI:**
```bash
aws application-autoscaling describe-scaling-policies --service-namespace rds --profile <p>
aws application-autoscaling describe-scalable-targets --service-namespace rds --profile <p>
aws application-autoscaling describe-scaling-activities --service-namespace rds --max-items 30 --profile <p>
```

Đọc: thêm / bớt replica **cùng giờ mỗi ngày** → tải có lịch cố định (mục 1–2). Chạm `MaxCapacity` → đã hết đường tự cứu.

### 5. SQL nào tốn nhất, đang chờ gì

**Console:** CloudWatch → *Insights* → *Database Insights* → chọn instance → *Top SQL* (theo DB load), *Top waits*. (Console Performance Insights cũ đã chuyển sang đây từ 31/07/2026.)

**CLI:** `rds_pi_snapshot.py` — xem [`perf-measure`](../perf-measure/SKILL.md) §Cách chạy. Hoặc `pg-top-queries.sql` trên stg / replica.

Lưu ý: **replica do autoscaling tạo ra thường không bật Performance Insights** → PI thiếu một phần tải đọc. Kiểm `describe-db-instances --query 'DBInstances[].[DBInstanceIdentifier,PerformanceInsightsEnabled]'`, và đối chiếu với mục 3.

### 6. Cấu hình

| Xem gì | Console | CLI / code |
|---|---|---|
| Loại instance, số reader, writer là cái nào | RDS → cluster → *Configuration*, danh sách instance | `aws rds describe-db-clusters --db-cluster-identifier <id>` |
| App đọc từ reader hay writer | — | config DB của app (vd Laravel `config/database.php` `read` / `write`, env `DB_READ_HOST`) |
| Parameter group (vd `work_mem`, `max_connections`) | RDS → *Parameter groups* | `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name <g> --source user` |
| Cache TTL, driver | — | env của app (hỏi người dùng nếu không đọc được) |

### 7. Dữ liệu lớn cỡ nào

**Console:** CloudWatch → *RDS* → *Per-Cluster Metrics* → `VolumeBytesUsed` (xu hướng theo ngày).

**CLI / SQL:** `pg-top-queries.sql` §8 (bảng lớn nhất, số dòng ước tính) trên stg / replica.

### 8. Cache có đỡ được không

**Console:** ElastiCache → cluster → *Metrics* → `CacheHits`, `CacheMisses`, `Evictions`, `EngineCPUUtilization`.

**CLI:** `cloudwatch_snapshot.py --cache-cluster <id> [--series hour]` — report tự tính hit rate.

Đọc: hit rate thấp mà Evictions = 0 → không phải thiếu RAM, mà key ít lặp lại (URL đa dạng, TTL ngắn) — xem mục 2.

## CloudWatch giữ số bao lâu

| Chu kỳ | Giữ |
|---|---|
| 1 phút | 15 ngày |
| 5 phút | 63 ngày |
| 1 giờ | 455 ngày |

So với vài tháng trước → dùng chu kỳ 1 giờ hoặc 1 ngày. `--series day` gom theo ngày **UTC**.

## Output

`$WS/2-baseline/infra-{yyyymmdd}.md` theo `$PLUGIN/templates/report-infra.md` — mỗi mục: câu hỏi → số → kết luận → mức chắc chắn. Số thô (`series.md`, `report.md`, JSON) trong `$RUN/`. Tóm tắt đưa vào report hiện trạng (mục *Thời gian đang mất ở đâu* và *Phương án*).
