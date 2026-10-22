---
name: planning
description: >-
  Plan and schedule a PERFORMANCE / PageSpeed improvement project (perf-toolkit) — turn the approved
  report-backend / report-psi options and test-plan into a WBS (one item = one change that can be measured
  on its own, est + scope & impact + expected outcome + acceptance numbers) with a per-item progress
  checklist, plus wbs-schedule.md, the customer schedule in calendar dates that also carries the
  perf-specific milestones: baseline measurement, staging verification, production release window,
  customer approval of third-party tag changes, and the up-to-28-day wait for Core Web Vitals field data.
  Use for "lên kế hoạch cải thiện performance", "planning PSI", "lịch cải thiện tốc độ", "WBS tối ưu trang",
  "schedule perf". For generic (non-performance) task planning use task-toolkit:planning instead.
  Locale vn (default) / en / ja.
---

# Planning — kế hoạch & lịch cho dự án hiệu năng

> **Luồng, workspace, an toàn**: [`../_shared/workflow.md`](../_shared/workflow.md) — nguồn duy nhất, đừng chép lại đường dẫn.
>
> Bản copy từ `task-toolkit:planning`, chỉnh cho dự án hiệu năng: đầu vào là report của perf-toolkit, item là *một thay đổi đo được*, lịch có mốc đo / duyệt tag / chờ field data. Phần chung (WBS, checklist, lịch, cổng số học) giữ nguyên.

> Ngôn ngữ giao tiếp: tiếng Việt. Nội dung plan theo `locale` (mặc định vn). Gõ `planning help` → in Help cuối file, không chạy gì.

> **Ai nghĩ, ai gõ** — bước *phán đoán* (nêu giả thuyết, chọn hướng, chốt kết luận, quyết định đánh đổi) là của **người phụ trách**; AI chỉ đưa *câu hỏi* hoặc *lựa chọn kèm đánh đổi* khi họ bí, không kết luận thay. Bước *thao tác* (grep, chạy lệnh verify, dựng bảng, soạn nháp theo template) AI làm, người soát từng dòng. Xem README §Nguyên tắc gốc.

Chia 1 task/epic thành **kế hoạch các việc sẽ làm**: một **bảng WBS tổng quan** (nhìn toàn cảnh + tổng est) và một **checklist theo item** (tick tiến độ khi làm). Đây là stage giữa *điều tra* và *sinh ticket* — mỗi item của plan sẽ thành 1 backlog-ticket chi tiết sau.

## Bước 1 — Adapter: quy ước dự án (dừng khi đủ)

Cần: `EST_UNIT` (mặc định man-day `md`; đổi story point nếu repo dùng point), `PROJECT conventions` (gitflow, layer). Precedence như các skill khác: repo config (`.claude/*.config.md`) → `project-context`/`CLAUDE.md` → hỏi 1 câu nếu thiếu `EST_UNIT`.

## Bước 2 — Đọc evidence stage trước (KHÔNG điều tra lại)

Plan ăn từ artifact đã có trong `tasks/{TICKET}/perf/` (`$WS`, xem `../_shared/workflow.md` §Workspace):

- `report-backend-*.md` / `report-psi-*.md` → mục *Hướng xử lý* đã được duyệt (mỗi phương án được chọn → ≥ 1 item), *AC*, *Rủi ro*.
- `test-plan.md` → loại test + phạm vi regression của từng thay đổi (đưa vào checklist của item).
- `scope.md` → màn bị ảnh hưởng (cột Scope & Impact), câu hỏi khách chưa trả lời (thành rủi ro / mốc chờ).
- `report-baseline-*.md` → số hiện tại (cột Expected outcome ghi *từ → tới*).

Chưa có report điều tra → chạy `backend-perf` / `psi-improve` điều tra trước. Chưa có `test-plan.md` → chạy `perf-test-plan` trước. Không lập kế hoạch cho phương án chưa được duyệt.

## Bước 3 — Chia item (granularity)

Nguyên tắc tách:

- **1 item = 1 deliverable mạch lạc** ≈ 1 PR / 1 ticket, thường **0.5–3 md**. To hơn 3 md → tách nhỏ; nhỏ hơn 0.5 md và cùng file → gộp.
- Tách theo **ranh giới tự nhiên**: layer (BE/FE), màn hình, endpoint, bước migration, nhóm regression.
- Mỗi item **độc lập test được** nếu có thể; item phụ thuộc nhau → ghi thứ tự/dependency ở Bước 4.
- Item suy thẳng từ phương án **đã duyệt** trong report backend / PSI: mỗi phương án → 1 item; phương án gồm nhiều thay đổi đo riêng được → tách.
- **Phép thử ranh giới**: chỉ tách khi reviewer **có thể từ chối item này mà vẫn duyệt item bên cạnh**. Không tách được theo tiêu chí đó thì đang tách theo cảm tính, gộp lại.
- **Setup / config / scaffolding / doc không thành item riêng** — gộp vào item có deliverable cần chúng. Một item "chuẩn bị môi trường" không ai review độc lập được, và nó che mất tiến độ thật.

## Bước 3.5 — Quy tắc riêng cho dự án hiệu năng

**Item = một thay đổi đo được riêng.** Hai thay đổi gộp chung một item thì đo xong không biết cái nào có tác dụng — tách. Cột *Expected outcome* ghi **từ → tới** bằng số (lấy *từ* ở report-baseline, *tới* ở AC của report điều tra).

Checklist của mọi item có đủ 5 bước — thiếu bước nào là item chưa xong:

````markdown
### [ ] Item {No} — {thay đổi}   ({est} {EST_UNIT})
- [ ] Đo trước (perf-measure compare · before) — {chỉ số, môi trường}
- [ ] Sửa — {file/function thật}
- [ ] Test theo test-plan — parity · {loại test riêng của item}
- [ ] Đo sau cùng điều kiện — {chỉ số}: {từ} → {tới}
- [ ] Đạt AC: {AC copy từ report}
````

**Est của item phải gồm thời gian đo** (một vòng PSI median 5 lần × 2 thiết bị × N trang mất cỡ chục phút tới cả giờ) và thời gian chờ deploy lên môi trường đo.

**Bốn giai đoạn** (dùng cho lịch ở Bước 6):

| Giai đoạn | Gồm |
|---|---|
| Chuẩn bị | scope · đo baseline · report hiện trạng · điều tra sâu · test plan |
| Triển khai | các item, mỗi item kèm đo trước/sau ở local/dev |
| Kiểm thử & đo trên stg | regression · visual · tracking · đo stg so AC |
| Release & theo dõi | release prod · đo verify · theo dõi field data · report khách |

**Mốc lịch đặc thù — đều là ngày chờ, không phải công làm, nhưng làm trượt lịch nếu quên:**

- **Duyệt tag bên thứ ba** của marketing phía khách — chặn mọi item đụng GTM / tag.
- **Khung release prod** của khách — không release ngoài khung.
- **Field data (CrUX) tới 28 ngày** sau release mới phản ánh đủ — nghiệm thu bằng field phải đặt sau mốc này. Ghi rõ trong lịch gửi khách, không thì nghiệm thu ngay hôm sau sẽ thấy "không đổi".
- **Khung giờ đo prod** (ngoài giờ cao điểm) nếu khách giới hạn.

## Bước 4 — WBS overview (bảng tổng quan)

````markdown
## Kế hoạch (WBS) — {task/epic}

| No | Task title | Task detail | Est ({EST_UNIT}) | Scope & Impact | Expected outcome |
|---|---|---|---|---|---|
| 1 | {tiêu đề ngắn} | {làm gì — file/function thật từ report điều tra} | {est sơ bộ, gồm thời gian đo} | edit: {file}; ảnh hưởng: {màn hình liên quan từ scope.md} | {chỉ số}: {từ} → {tới} |
| 2 | … | … | … | … | … |

**Tổng est:** {Σ} {EST_UNIT} (confidence: {cao/tb/thấp}).
**Thứ tự / phụ thuộc:** {item nào chặn item nào; critical path; song song được cái nào}.
**Rủi ro kế hoạch:** {2–3 yếu tố có thể trượt — spec chưa chốt, shared component nhiều consumer, cross-repo}.
````

Cột:
- **Est sơ bộ** = ước lượng nhanh theo độ phức tạp + số file (⚠/🆕) + số màn hình impact. Là **khoảng thô** để lập kế hoạch; est tinh để ở backlog-ticket từng item.
- **Scope & Impact** = file sẽ sửa (từ ⚠/🆕) + màn hình/chức năng liên quan (từ dependency walk `scope.md`). Không nhớ tay — lấy từ evidence.
- **Expected outcome** = mỗi item đạt được gì, **kiểm chứng được** (không "làm xong phần X" chung chung).

## Bước 5 — Checklist tiến độ (detail, tick khi làm)

Với mỗi item ở bảng, sinh 1 khối checkbox để theo dõi thực thi:

````markdown
### [ ] Item {No} — {task title}   ({est} {EST_UNIT})
- [ ] {sub-task thực thi 1 — file/function thật}
- [ ] {sub-task 2}
- [ ] {test / QA của item}
- [ ] Outcome đạt: {điều kiện kiểm chứng ở cột Expected outcome}
````

Bảng WBS = **overview** (toàn cảnh + tổng est, xuất xlsx dễ); checklist = **detail** để tick `4/12` tiến độ thật.

## Bước 5.5 — Tự soát (chạy trước khi ghi file, không dispatch subagent)

Ba phép kiểm, tự làm, thấy lỗi thì sửa luôn rồi đi tiếp — không cần soát lại vòng hai:

1. **Coverage** — mở lại report backend / PSI, rà từng phương án **đã duyệt**: phải trỏ được vào đúng một (hoặc vài) WBS item. Phương án không trỏ được = **thiếu item**, thêm ngay. Ngược lại item không trỏ về phương án nào = việc ngoài phạm vi đã duyệt, bỏ hoặc hỏi lại.
2. **Đối chiếu overview ↔ checklist** — tên item, số thứ tự, est, dependency ở Bước 4 phải khớp Bước 5. Item số 3 tên khác nhau ở hai bảng là lỗi, không phải cách diễn đạt.
3. **Quét chữ rỗng** — `hoàn thiện`, `cải thiện`, `xử lý`, `optimize`, `refactor cho tốt hơn` ở cột task detail hoặc expected outcome. Thay bằng điều kiện đo được, hoặc bỏ item nếu không nói được nó giao ra cái gì.

## Bước 6 — Lịch gửi khách (`wbs-schedule.md`)

Plan xong mới ra được **khối lượng**. Lịch là bước dịch khối lượng → **ngày**, và nó là artifact **thứ hai, cho người đọc khác**:

| | `plan.md` | `wbs-schedule.md` |
|---|---|---|
| Người đọc | nội bộ team | **khách / PM** |
| Độ mịn | từng item (0.5–3 {EST_UNIT}) | **gom theo hạng mục** — mỗi hạng mục 1 dòng |
| Nội dung riêng | đánh đổi, phương án cắt, item bị bỏ, ghi chú kỹ thuật | ngày bắt đầu/kết thúc, giả định lập lịch |
| Ngôn ngữ | theo `locale` | theo `locale`; khách nước ngoài → **song ngữ** (vn/ja hoặc vn/en), phân cách `ーーー` |

Chỉ sinh khi task có **giao kèo thời gian với bên ngoài** (deadline khách, EOL, release window). Task nội bộ thuần thì bỏ qua bước này — đừng đẻ lịch cho thứ không ai hỏi ngày.

**Hỏi trước khi lập lịch — 3 tham số không suy được từ code, thiếu cái nào thì hỏi cái đó:**

1. **Ngày bắt đầu** và deadline cứng (nếu có).
2. **Quy đổi**: 1 {EST_UNIT} = mấy giờ; người thực hiện dành **mấy giờ/ngày** cho task này. Hai số này ra **hệ số kéo dài** — vd 1 MD = 7h, dành 5h/ngày → 1.4 ngày lịch / 1 MD. Không hỏi mà lấy 1 MD = 1 ngày là **sai hệ thống**, lịch ngắn hơn thực tế ~40%.
3. **Số người / có chạy song song không.** Mặc định: 1 người, tuần tự.

````markdown
# WBS Schedule — {task}

> Bắt đầu **{start}** · Tổng **{Σ} {EST_UNIT}** · Kết thúc dự kiến **{end}**
> {Deadline ngoài nếu có} → còn {n} tuần đệm sau khi xong.
>
> **Quy đổi:** 1 {EST_UNIT} = **{h}h**. Người thực hiện dành **{x}h/ngày** cho task này
> → hệ số kéo dài **{h/x} ngày lịch / 1 {EST_UNIT}**. Tổng {Σ} = {Σ·h}h = **{n} ngày làm việc**.

**Giả định khi lập lịch — đổi giả định thì đổi ngày:**

1. **{Tuần tự / song song}, {n} người, {x}h/ngày.** Cột Est ghi cả **{EST_UNIT}** (khối lượng) và **ngày lịch** (đã nhân hệ số). Đổi phân bổ giờ hoặc thêm người → ngày đổi, khối lượng giữ nguyên.
2. **Chỉ trừ T7/CN.** ⚠ Ngày lễ: {liệt kê ngày lễ rơi vào khung, cả phía khách nếu khác quốc gia} — cần dời hoặc cộng ngày.
3. **Buffer:** {có/không}. Mốc phụ thuộc bên ngoài ({liệt kê}) có thể trượt, ngoài tầm kiểm soát của team.

| No | Category | Detail | Est | Start | Due |
|---|---|---|---|---|---|
| 1 | {tên hạng mục} | {gạch đầu dòng: đã xong ✅ / còn lại / rủi ro đã biết} | {n} {EST_UNIT}<br>({n·hệ số} ngày) | {date} | {date} |
| | **Total** | | **{Σ}**<br>({n} ngày) | **{start}** | **{end}** |
````

**Ba luật của bước này:**

- **Σ {EST_UNIT} của lịch = Σ của plan.** Lệch là lỗi, không phải làm tròn. Nếu buộc phải gửi khách con số khác (đã cam kết trước, hoặc đã cắt phạm vi) → ghi **một mục lệch số liệu** trong `plan.md`: số nào gửi khách, số nào là thực tế, chênh bao nhiêu, vì sao. Im lặng để hai file khác nhau là cách chắc chắn nhất để cả hai cùng sai.
- **Mọi con số trong lịch phải cùng nguồn với report-baseline / report điều tra.** Số site, số màn hình, số file — lịch là bản gửi khách nên số sai ở đây đắt hơn nhiều so với sai trong ghi chú nội bộ. Ghi rõ **nguồn** của số ngay tại chỗ dùng.
- **Ngày không tự trượt theo phạm vi.** Phạm vi dày lên mà {EST_UNIT} giữ nguyên thì lịch giữ nguyên — nhưng phải ghi thành **rủi ro vượt khung**, đừng để nó im lặng biến thành trễ hạn.

### Lịch nói *cái gì*, không nói *làm thế nào*

Cụ thể tới mức gọi tên được thứ đang đụng vào, rồi dừng trước công thức thực thi.

| Viết vào lịch | Để trong `plan.md` / ghi chú nội bộ |
|---|---|
| "Bỏ cơ chế gửi lệnh trực tiếp xuống máy chủ (`aws ssm send-command`)" | cú pháp và tham số của lệnh |
| "Nâng `actions/checkout` v4 → v5" | vì sao v4 bị khai tử |
| "Đồng bộ mã nguồn ra thư mục web, giữ nguyên danh sách loại trừ" | `rsync -a --delete-delay --delay-updates --exclude-from=…` |
| "Viết script health check chạy sau khi đồng bộ" | `sleep 3` vì `opcache.revalidate_freq=2` |

Phép thử: **tên riêng thì giữ, cờ và giá trị cấu hình thì bỏ.** Người đọc cần biết đang đụng vào cái gì, không cần biết gõ ra sao. Viết chung chung kiểu "nâng phiên bản các action" thì lại thiếu — họ không biết action nào.

### Cắt chữ rỗng

Xoá mọi câu không đổi hành vi người đọc. Ba dạng hay gặp:

- "Không phụ thuộc mốc nào, làm được ngay" — bảng đã cho biết ngày bắt đầu
- "Chỉ bắt đầu sau khi X ổn định" — nếu thứ tự đã hiển nhiên từ cột ngày
- Câu giải thích lý do nối sau một điều kiện vốn đã rõ

### Lịch chỉ chứa lịch

Bốn thứ hay bị nhét vào nhưng thuộc chỗ khác:

| Nội dung | Thuộc về |
|---|---|
| Bảng mốc phụ thuộc bên ngoài | ticket |
| Bảng rủi ro tiến độ | ticket |
| Nguồn của từng con số | ghi chú nội bộ |
| Chi tiết kỹ thuật (cờ, ARN, đường dẫn, giá trị config) | ghi chú nội bộ |

Header giữ tối thiểu — tổng {EST_UNIT} và khoảng ngày đã nằm ở dòng **Tổng** của bảng tổng quan, đừng lặp lại ở đầu file.

### Bố cục: giai đoạn, không phải một bảng phẳng

Task nhiều hơn ~6 hạng mục thì gom thành **4 giai đoạn** — chuẩn bị / triển khai / dựng và kiểm thử / bàn giao — mỗi giai đoạn một bảng chi tiết, phía trên là bảng tổng quan. **Một file, nhiều mục** — đừng tách thành nhiều file: deadline là một mốc, tách file làm mất đường găng.

Giai đoạn "chuẩn bị" hay bị bỏ sót. Nó gồm tài liệu thiết kế và checklist cấu hình, sơ đồ, kế hoạch rollback, kịch bản kiểm thử — thứ phải có **trước** khi gõ dòng code đầu tiên.

Đồng bộ hình thức trong toàn file: cùng tên cột (`Hạng mục / 項目`), cùng dạng tên dòng ("Triển khai môi trường dev", không phải "dev"), cùng có dòng `**Est:**` dưới mỗi heading giai đoạn.

Trong một ô có nhiều ý thì tách bằng `<br>` — kể cả danh sách đánh số `①②③`. Đừng viết thành câu dài nối bằng dấu chấm phẩy.

### Dự phòng là một dòng riêng

Không giấu buffer vào từng hạng mục. Cho nó một dòng cuối bảng, làm tròn, và nói rõ dùng cho việc gì: *"trục trặc phát sinh hoặc feedback của khách"*. Không dùng tới thì lịch kết thúc sớm — ghi luôn ngày đó.

### Cổng kiểm số học — chạy bằng script, không đọc bằng mắt

Ba phép kiểm, bắt buộc trước khi giao và sau **mỗi lần** sửa est hoặc ngày:

1. **Σ bảng tổng quan == Σ bảng chi tiết.** Lệch là lỗi.
2. **Không ô `Start`/`Due` nào rơi vào T7/CN hoặc ngày lễ.** Kể cả ô hạn chót dành cho khách.
3. **Xếp tuần tự theo khung ngày, không ngày nào vượt công suất.** Duyệt từng hạng mục theo thứ tự, đổ {EST_UNIT} vào các ngày làm việc trong khung `Start`→`Due`, mỗi ngày tối đa mức phân bổ. Hạng mục nào không xếp đủ = khung ngày quá hẹp.

Phép 3 bắt được lỗi mắt không thấy. Lưu ý khi tự viết checker: **đừng chia đều** {EST_UNIT} cho các ngày trong khung — cách đó báo quá tải giả. Phải xếp tuần tự theo thứ tự hạng mục.

Kiểm cả tính nhất quán nội dung: điều kiện dạng "sau N ngày làm việc" phải thoả được với ngày đã xếp; hạng mục A trỏ tới hạng mục B thì B phải tồn tại và nằm trước.

### Đừng gọi tên bên thứ ba khi chưa chắc

Suy ra tên công ty từ tên miền email hay tên user hệ thống là **suy luận**, không phải bằng chứng. Trong lịch gửi khách dùng vai trò — "bên vận hành WordPress", "bên vận hành hạ tầng". Giữ tên kèm dẫn chứng ở ghi chú nội bộ, nơi người đọc tự đánh giá được độ tin.

### Cảnh báo khi sửa file lịch bằng script

Lịch là bảng markdown dài, sửa nhiều vòng. **Chỉ dùng `replace` với chuỗi cố định.** Đừng cắt đoạn bằng `s[s.index(A):s.index(B)]` — nếu `B` đứng trước `A` thì lát cắt ra chuỗi rỗng, và `str.replace('', x)` trong Python chèn `x` vào **giữa mọi ký tự**, phá nát file. Nếu buộc phải cắt thì assert `index(B) > index(A)` trước.

## Bước 7 — Ghi & handoff

- Ghi `$WS/4-plan/plan.md` (bảng WBS + checklists) và `$WS/4-plan/wbs-schedule.md` (nếu có Bước 6).
- **Handoff xuống implement**: mỗi item chạy `backend-perf implement <item>` hoặc `psi-improve implement <item>`.
- **Handoff xuống ticket** (nếu cài task-toolkit): mỗi row WBS → 1 `task-toolkit:backlog-ticket`. Đề nghị 1 dòng, không tự chạy.
- **Artifact contract**: plan tái dùng report + test-plan; implement tái dùng plan — không bước nào điều tra lại từ đầu.

## Content rules

- Mỗi item nêu **file/function thật** từ report điều tra; thiếu evidence → `[verify in code]`, không bịa.
- Est là **khoảng + confidence**, không số cứng; input thiếu → `[Giả định — cần: …]`.
- Expected outcome kiểm chứng được; cấm "hoàn thiện", "cải thiện" trần.
- Giữ nguyên chuỗi UI gốc (tiếng Nhật…) ở mọi locale.
- Scope & Impact của item phải khớp `scope.md` — im lặng ≠ đã kiểm tra.
- Không nhồi mọi việc thành 1 item khổng lồ; không đẻ item < 0.5 md rời rạc.
- Lịch (Bước 6): không tự chọn hệ số quy đổi giờ → **hỏi**; không tự thêm buffer im lặng → **ghi thành giả định**.

## Help

```
planning <TICKET-ID> [locale=vn|en|ja]
  Kế hoạch + lịch cho dự án hiệu năng (perf-toolkit).
  - Ăn từ report-backend / report-psi (phương án đã duyệt, AC, rủi ro) + test-plan.md — KHÔNG điều tra lại.
  - Item = 1 thay đổi đo được riêng; checklist mỗi item có: đo trước · sửa · test · đo sau · đạt AC.
  - Ra plan.md (nội bộ) + wbs-schedule.md (gửi khách) — lịch có mốc đo baseline, verify stg, release,
    duyệt tag, chờ field data tới 28 ngày.
  Planning task thường (không phải hiệu năng) → dùng task-toolkit:planning.
```
