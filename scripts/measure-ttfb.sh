#!/usr/bin/env bash
#
# measure-ttfb.sh — đo TTFB (curl) cho một danh sách trang, có so sánh before/after.
# Tổng quát hoá từ script đo của SHOKAI_ARCH_2506-76.
#
# Usage:
#   BASE_URL=<url> PAGES=pages.tsv ./measure-ttfb.sh before   # đo + lưu snapshot
#   BASE_URL=<url> PAGES=pages.tsv ./measure-ttfb.sh after    # đo + so với snapshot
#   BASE_URL=<url> PAGES=pages.tsv ./measure-ttfb.sh          # ảnh chụp hiện trạng
#   BASE_URL=<url> PAGES=fresh.tsv ./measure-ttfb.sh miss     # thời gian khi cache miss: lần 1 vs lần 2 ngay sau
#     → PAGES phải là URL chưa ai truy cập trong TTL cache (tổ hợp hiếm, trang phân trang sâu).
#       Lần 2 ≈ lần 1 nghĩa là URL không có cache, hoặc đã nóng sẵn từ trước — chọn URL khác.
#
# PAGES: TSV  <path><TAB><nhãn><TAB><nhóm>   (dòng trống / bắt đầu bằng # bị bỏ qua)
#
# Env tuỳ chọn:
#   N=20 WARMUP=4 MAX_TIME=30   số mẫu warm / số request làm nóng (bỏ) / timeout curl (giây)
#   PERF_SNAP=.perf-snapshot.tsv   snapshot dùng chung giữa before và after
#   REPORT=<file.md>            đường dẫn report (mặc định tự đặt theo phase + giờ)
#   AUTH=user:pass              Basic Auth cho stg/dev — đọc từ env, KHÔNG ghi vào file
#   UTM_CHECK=/path             so URL sạch với URL có utm_* (phát hiện cache key lệch)
#   SLEEP=0                     nghỉ giữa các request (giây) — đặt 1 khi đo prod
#   TITLE="Page performance"    tiêu đề report
#   REPORT_TZ=Asia/Tokyo        múi giờ ghi trong report (mặc định: giờ máy đo, luôn kèm offset UTC)
#
# Đọc kết quả:
#   TTFB    = time_starttransfer (byte đầu tiên về tới client)
#   Server  = starttransfer - pretransfer  (server xử lý + hàng đợi; không gồm DNS/TCP/TLS)
#   Network = pretransfer                  (DNS + TCP + TLS — mỗi lần curl là 1 kết nối mới)
#   So before/after nên đọc warm MIN: ít bị nhiễu mạng/tải nhất.
#
set -u

PHASE="${1:-}"
: "${BASE_URL:?BASE_URL bắt buộc (vd https://example.com) — script không tự trỏ môi trường nào}"
: "${PAGES:?PAGES bắt buộc — file TSV path<TAB>nhãn<TAB>nhóm}"
[ -f "$PAGES" ] || { echo "Không thấy file PAGES: $PAGES"; exit 1; }

BASE="${BASE_URL%/}"
N="${N:-20}"
WARMUP="${WARMUP:-4}"
MAX_TIME="${MAX_TIME:-30}"
SNAP="${PERF_SNAP:-.perf-snapshot.tsv}"
SLEEP="${SLEEP:-0}"
TITLE="${TITLE:-Page performance}"
AUTH="${AUTH:-}"
UTM_CHECK="${UTM_CHECK:-}"
REPORT_TZ="${REPORT_TZ:-}"

case "$PHASE" in
  before) DEFREP="perf-ttfb-before-$(date +%Y%m%d-%H%M).md"; PHLABEL="Before";;
  after)  DEFREP="perf-ttfb-compare-$(date +%Y%m%d-%H%M).md"; PHLABEL="Before / After";;
  miss)   DEFREP="perf-ttfb-miss-$(date +%Y%m%d-%H%M).md"; PHLABEL="Cache miss";;
  "")     DEFREP="perf-ttfb-snapshot-$(date +%Y%m%d-%H%M).md"; PHLABEL="Current snapshot";;
  *) echo "Phase không hợp lệ: '$PHASE' (before | after | miss | để trống)"; exit 1;;
esac
REPORT="${REPORT:-$DEFREP}"

# ---------- đọc danh sách trang (bash 3.2: không mapfile, không mảng kết hợp) ----------
# Lưu ý: không đặt tên biến là GROUPS — đó là biến đặc biệt của bash.
P_PATH=(); P_LABEL=(); P_GROUP=()
while IFS=$'\t' read -r p l g || [ -n "${p:-}" ]; do
  case "${p:-}" in ''|'#'*) continue;; esac
  P_PATH+=("$p"); P_LABEL+=("${l:-$p}"); P_GROUP+=("${g:-all}")
done < "$PAGES"
[ "${#P_PATH[@]}" -gt 0 ] || { echo "PAGES không có dòng hợp lệ"; exit 1; }

# ---------- tiện ích ----------
hr(){ printf '%.0s-' {1..96}; echo; }
toms(){ awk -v s="${1:-0}" 'BEGIN{ if (s == "") print "-"; else printf "%d", s * 1000 }'; }

# 1 request -> code<TAB>pretransfer<TAB>starttransfer<TAB>total
measure(){
  local out
  if [ -n "$AUTH" ]; then
    out="$(curl -L -s -o /dev/null --max-time "$MAX_TIME" -u "$AUTH" \
      -w '%{http_code}\t%{time_pretransfer}\t%{time_starttransfer}\t%{time_total}' "$1" 2>/dev/null)"
  else
    out="$(curl -L -s -o /dev/null --max-time "$MAX_TIME" \
      -w '%{http_code}\t%{time_pretransfer}\t%{time_starttransfer}\t%{time_total}' "$1" 2>/dev/null)"
  fi
  [ -n "$out" ] || out="000	0	0	0"
  printf '%s\n' "$out"
  [ "$SLEEP" = "0" ] || sleep "$SLEEP"
}
is_ok(){ case "$1" in 2*|3*) return 0;; *) return 1;; esac; }

# đọc danh sách số (giây) từ stdin -> median | min | p95
stat_med(){ sort -n | awk '{a[++n]=$1} END{ if(n==0){print ""; exit} print a[int((n+1)/2)] }'; }
stat_min(){ sort -n | awk 'NR==1{print $1}'; }
stat_p95(){ sort -n | awk '{a[++n]=$1} END{ if(n==0){print ""; exit} i=int(n*0.95); if(i<n*0.95)i++; if(i<1)i=1; print a[i] }'; }
median_ints(){ [ "$#" -eq 0 ] && { echo "-"; return; }; printf '%s\n' "$@" | sort -n | awk '{a[++n]=$1} END{ print a[int((n+1)/2)] }'; }
pct(){ [ "$1" = "-" ] && echo "n/a" || echo "$1%"; }

now_str(){
  if [ -n "$REPORT_TZ" ]; then TZ="$REPORT_TZ" date '+%Y-%m-%d %H:%M %Z (UTC%z)'
  else date '+%Y-%m-%d %H:%M %Z (UTC%z)'; fi
}
write_errors(){ if [ "${#ERRORS[@]}" -eq 0 ]; then echo "- Không có"; else for e in "${ERRORS[@]}"; do echo "- $e"; done; fi; }

meta_block(){
  echo "- **Target:** ${BASE}"
  echo "- **Measured at:** $(now_str)"
  echo "- **Method:** ${1:-curl TTFB (time_starttransfer); ${WARMUP} warm-up requests ignored, then ${N} warm samples per URL.}"
  echo "- **Basic Auth:** $([ -n "$AUTH" ] && echo used || echo not used)"
  echo "- **Comparison condition:** before and after on the same environment, same client network, similar time/load."
}
glossary(){
  echo "## How To Read"; echo
  echo "- **1st request:** first request of this run. It is a cache miss **only if** nobody requested this URL within the cache TTL — do not read it as cache-miss time. Use phase \`miss\` with fresh URLs for that."
  echo "- **Warm median / min / P95:** typical / best-case / slow-end TTFB after warm-up. Use **warm min** to compare before/after — least affected by network and load noise."
  echo "- **Server:** starttransfer − pretransfer = server processing + queueing (excludes DNS/TCP/TLS)."
  echo "- **Network:** DNS + TCP + TLS (each curl opens a new connection)."
  echo "- If TTFB is high but **Server** is small, the bottleneck is network/infra — tuning queries will not help."
}

# ---------- phase miss: lần 1 (cache miss) vs lần 2 (vừa được cache) ----------
if [ "$PHASE" = "miss" ]; then
  ERRORS=(); rows=""; RATIOS=()
  echo "[$PHLABEL] BASE=$BASE AUTH=$([ -n "$AUTH" ] && echo yes || echo no) -> $REPORT"
  hr
  printf "%-44s %-6s %9s %9s %9s %7s\n" "PATH" "status" "1st" "1st-srv" "2nd" "ratio"
  hr
  for i in "${!P_PATH[@]}"; do
    path="${P_PATH[$i]}"; url="$BASE$path"
    l1="$(measure "$url")"; l2="$(measure "$url")"
    c1="$(printf '%s' "$l1" | cut -f1)"; c2="$(printf '%s' "$l2" | cut -f1)"
    if ! is_ok "$c1" || ! is_ok "$c2"; then
      ERRORS+=("$path trả HTTP $c1 / $c2")
      rows+="| ${P_LABEL[$i]} | ${P_GROUP[$i]} | \`${path}\` | - | - | - | - | HTTP $c1/$c2 |"$'\n'
      printf "%-44s %-6s\n" "$path" "HTTP$c1"; continue
    fi
    pre1="$(printf '%s' "$l1" | cut -f2)"; st1="$(printf '%s' "$l1" | cut -f3)"; st2="$(printf '%s' "$l2" | cut -f3)"
    srv1="$(awk -v a="$st1" -v b="$pre1" 'BEGIN{ d=a-b; if(d<0)d=0; printf "%.6f", d }')"
    ratio="$(awk -v a="$st1" -v b="$st2" 'BEGIN{ if(b+0>0) printf "%.1f", a/b; else print "-" }')"
    RATIOS+=("$ratio")
    note=""; awk -v r="$ratio" 'BEGIN{ exit !(r+0 < 1.5) }' && note=" · 2nd ≈ 1st: no cache, or already warm"
    rows+="| ${P_LABEL[$i]} | ${P_GROUP[$i]} | \`${path}\` | $(toms "$st1") ms | $(toms "$srv1") ms | $(toms "$st2") ms | ×${ratio} | OK${note} |"$'\n'
    printf "%-44s %-6s %7sms %7sms %7sms %6s\n" "$path" "OK" "$(toms "$st1")" "$(toms "$srv1")" "$(toms "$st2")" "x$ratio"
  done
  {
    echo "# ${TITLE} — TTFB ${PHLABEL}"; echo
    meta_block "curl TTFB, 2 requests back to back per URL: 1st = cache miss (URL assumed not requested within the cache TTL), 2nd = just cached."; echo
    echo "## Results By Page"; echo
    echo "| Page | Group | Path | 1st request | 1st server | 2nd request | 1st / 2nd | Status |"
    echo "|---|---|---|---:|---:|---:|---:|---|"
    printf '%s' "$rows"; echo
    echo "## Measurement Warnings"; echo; write_errors; echo
    echo "## How To Read"; echo
    echo "- **1st request** is cache-miss time only if the URL was not requested within the cache TTL. Pick rare condition combinations or deep pagination pages."
    echo "- **1st / 2nd ≈ 1** → the URL has no cache, or was already warm. Pick another URL before concluding."
    echo "- Each URL is measured once — repeat on several fresh URLs instead of re-running the same ones (the 2nd run is no longer a miss)."
  } > "$REPORT"
  hr; echo "Report: $REPORT"
  exit 0
fi

# ---------- đo ----------
COLD=(); MED=(); MIN=(); P95=(); SRV=(); NET=(); STATUS=()
ERRORS=()

echo "[$PHLABEL] BASE=$BASE N=$N WARMUP=$WARMUP AUTH=$([ -n "$AUTH" ] && echo yes || echo no) -> $REPORT"
hr
printf "%-44s %-9s %8s %9s %9s %9s %9s\n" "PATH" "status" "1st-req" "warm-med" "warm-min" "server" "network"
hr

for i in "${!P_PATH[@]}"; do
  path="${P_PATH[$i]}"; url="$BASE$path"
  line="$(measure "$url")"
  code="$(printf '%s' "$line" | cut -f1)"
  cold="$(printf '%s' "$line" | cut -f3)"
  COLD[$i]="$cold"

  if ! is_ok "$code"; then
    STATUS[$i]="HTTP $code"; ERRORS+=("$path trả HTTP $code ở request lạnh")
    printf "%-44s %-9s %7sms %9s %9s %9s %9s\n" "$path" "HTTP$code" "$(toms "$cold")" "-" "-" "-" "-"
    continue
  fi

  w=1; while [ "$w" -le "$WARMUP" ]; do measure "$url" >/dev/null; w=$((w+1)); done

  ttfb_list=""; srv_list=""; net_list=""; bad=0
  k=1
  while [ "$k" -le "$N" ]; do
    l="$(measure "$url")"
    c="$(printf '%s' "$l" | cut -f1)"
    if is_ok "$c"; then
      pre="$(printf '%s' "$l" | cut -f2)"; st="$(printf '%s' "$l" | cut -f3)"
      ttfb_list="$ttfb_list$st"$'\n'
      net_list="$net_list$pre"$'\n'
      srv_list="$srv_list$(awk -v a="$st" -v b="$pre" 'BEGIN{ d=a-b; if(d<0)d=0; printf "%.6f", d }')"$'\n'
    else
      bad=$((bad+1))
    fi
    k=$((k+1))
  done

  if [ -z "$ttfb_list" ]; then
    STATUS[$i]="warm failed"; ERRORS+=("$path không có response warm hợp lệ ($bad lỗi)")
    printf "%-44s %-9s %7sms %9s %9s %9s %9s\n" "$path" "FAILED" "$(toms "$cold")" "-" "-" "-" "-"
    continue
  fi

  MED[$i]="$(printf '%s' "$ttfb_list" | stat_med)"
  MIN[$i]="$(printf '%s' "$ttfb_list" | stat_min)"
  P95[$i]="$(printf '%s' "$ttfb_list" | stat_p95)"
  SRV[$i]="$(printf '%s' "$srv_list" | stat_med)"
  NET[$i]="$(printf '%s' "$net_list" | stat_med)"
  STATUS[$i]="OK"
  if [ "$bad" -gt 0 ]; then STATUS[$i]="OK/${bad}fail"; ERRORS+=("$path có $bad response warm lỗi"); fi

  printf "%-44s %-9s %7sms %7sms %7sms %7sms %7sms\n" "$path" "${STATUS[$i]}" "$(toms "$cold")" \
    "$(toms "${MED[$i]}")" "$(toms "${MIN[$i]}")" "$(toms "${SRV[$i]}")" "$(toms "${NET[$i]}")"
done

# ---------- UTM check (tuỳ chọn) ----------
utm_verdict="Không kiểm (UTM_CHECK chưa đặt)."; clean_ms="-"; utm_ms="-"
if [ -n "$UTM_CHECK" ]; then
  case "$UTM_CHECK" in *\?*) sep="&";; *) sep="?";; esac
  utm_path="${UTM_CHECK}${sep}utm_source=perf-toolkit&utm_medium=check"
  warm_med_of(){
    measure "$BASE$1" >/dev/null
    vals=""
    for _ in 1 2 3 4 5 6 7; do
      l="$(measure "$BASE$1")"; c="$(printf '%s' "$l" | cut -f1)"
      is_ok "$c" && vals="$vals$(printf '%s' "$l" | cut -f3)"$'\n'
    done
    printf '%s' "$vals" | stat_med
  }
  cv="$(warm_med_of "$UTM_CHECK")"; uv="$(warm_med_of "$utm_path")"
  clean_ms="$(toms "$cv")"; utm_ms="$(toms "$uv")"
  if [ -n "$cv" ] && [ -n "$uv" ]; then
    gap="$(awk -v a="$cv" -v b="$uv" 'BEGIN{d=b-a; if(d<0)d=-d; printf "%d", d*1000}')"
    if [ "$gap" -le 50 ]; then utm_verdict="OK — URL có UTM gần bằng URL sạch (lệch ${gap} ms)."
    else utm_verdict="CẢNH BÁO — URL có UTM lệch ${gap} ms so với URL sạch: nghi cache key chứa tham số tracking."; fi
  else
    utm_verdict="CẢNH BÁO — không đo được cặp UTM."
  fi
fi

# danh sách nhóm duy nhất
UNIQ_GROUPS=()
for g in "${P_GROUP[@]}"; do
  found=0
  for u in ${UNIQ_GROUPS[@]+"${UNIQ_GROUPS[@]}"}; do [ "$u" = "$g" ] && found=1; done
  [ "$found" -eq 0 ] && UNIQ_GROUPS+=("$g")
done

hr
if [ "$PHASE" = "after" ]; then
  [ -f "$SNAP" ] || { echo "Không thấy snapshot $SNAP — chạy 'before' trước."; exit 1; }
  B_MED=(); B_MIN=()
  for i in "${!P_PATH[@]}"; do B_MED[$i]=""; B_MIN[$i]=""; done
  while IFS=$'\t' read -r sp scold smed sp95 sst smin ssrv; do
    for i in "${!P_PATH[@]}"; do
      if [ "${P_PATH[$i]}" = "$sp" ]; then B_MED[$i]="$smed"; B_MIN[$i]="$smin"; fi
    done
  done < "$SNAP"

  rows=""; ALL_IMP=()
  for i in "${!P_PATH[@]}"; do
    bm="${B_MED[$i]:-}"; am="${MED[$i]:-}"
    if [ -z "$bm" ] || [ -z "$am" ]; then
      rows+="| ${P_LABEL[$i]} | ${P_GROUP[$i]} | - | - | - | - | - | - | not comparable |"$'\n'; continue
    fi
    imp="$(awk -v b="$bm" -v a="$am" 'BEGIN{ if(b+0>0) printf "%d",(b-a)/b*100; else print 0 }')"
    ALL_IMP+=("$imp")
    rows+="| ${P_LABEL[$i]} | ${P_GROUP[$i]} | $(toms "$bm") ms | $(toms "$am") ms | $(toms "${B_MIN[$i]}") ms | $(toms "${MIN[$i]}") ms | $(toms "${SRV[$i]}") ms | ${imp}% | ${STATUS[$i]} |"$'\n'
  done

  group_lines=""
  for g in "${UNIQ_GROUPS[@]}"; do
    gi=()
    for i in "${!P_PATH[@]}"; do
      [ "${P_GROUP[$i]}" = "$g" ] || continue
      bm="${B_MED[$i]:-}"; am="${MED[$i]:-}"
      [ -n "$bm" ] && [ -n "$am" ] || continue
      gi+=("$(awk -v b="$bm" -v a="$am" 'BEGIN{ if(b+0>0) printf "%d",(b-a)/b*100; else print 0 }')")
    done
    group_lines+="| ${g} | $(pct "$(median_ints ${gi[@]+"${gi[@]}"})") |"$'\n'
  done

  {
    echo "# ${TITLE} — TTFB Before / After"; echo
    meta_block; echo
    echo "## Summary"; echo
    echo "- Median improvement, all pages (warm median): **$(pct "$(median_ints ${ALL_IMP[@]+"${ALL_IMP[@]}"})")**"
    echo "- UTM check: ${utm_verdict}"; echo
    echo "| Group | Median improvement |"; echo "|---|---:|"; printf '%s' "$group_lines"; echo
    echo "## Results By Page"; echo
    echo "| Page | Group | Before median | After median | Before min | After min | After server | Improvement | Status |"
    echo "|---|---|---:|---:|---:|---:|---:|---:|---|"
    printf '%s' "$rows"; echo
    echo "## UTM / Tracking Parameter Check"; echo
    echo "| URL | Warm median |"; echo "|---|---:|"
    echo "| Clean | ${clean_ms} ms |"; echo "| With UTM | ${utm_ms} ms |"; echo
    echo "## Measurement Warnings"; echo; write_errors; echo
    glossary
  } > "$REPORT"
  echo "Report: $REPORT"
else
  rows=""
  for i in "${!P_PATH[@]}"; do
    if [ -z "${MED[$i]:-}" ]; then
      rows+="| ${P_LABEL[$i]} | ${P_GROUP[$i]} | \`${P_PATH[$i]}\` | $(toms "${COLD[$i]:-}") ms | - | - | - | - | - | ${STATUS[$i]} |"$'\n'; continue
    fi
    rows+="| ${P_LABEL[$i]} | ${P_GROUP[$i]} | \`${P_PATH[$i]}\` | $(toms "${COLD[$i]}") ms | $(toms "${MED[$i]}") ms | $(toms "${MIN[$i]}") ms | $(toms "${P95[$i]}") ms | $(toms "${SRV[$i]}") ms | $(toms "${NET[$i]}") ms | ${STATUS[$i]} |"$'\n'
  done
  {
    echo "# ${TITLE} — TTFB ${PHLABEL}"; echo
    meta_block; echo
    echo "## Results By Page"; echo
    echo "| Page | Group | Path | 1st request | Warm median | Warm min | Warm P95 | Server | Network | Status |"
    echo "|---|---|---|---:|---:|---:|---:|---:|---:|---|"
    printf '%s' "$rows"; echo
    echo "## UTM / Tracking Parameter Check"; echo
    echo "| URL | Warm median |"; echo "|---|---:|"
    echo "| Clean | ${clean_ms} ms |"; echo "| With UTM | ${utm_ms} ms |"; echo
    echo "${utm_verdict}"; echo
    echo "## Measurement Warnings"; echo; write_errors; echo
    glossary
  } > "$REPORT"

  if [ "$PHASE" = "before" ]; then
    : > "$SNAP"
    for i in "${!P_PATH[@]}"; do
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "${P_PATH[$i]}" "${COLD[$i]:-}" "${MED[$i]:-}" \
        "${P95[$i]:-}" "${STATUS[$i]:-}" "${MIN[$i]:-}" "${SRV[$i]:-}" >> "$SNAP"
    done
    echo "Snapshot: $SNAP"
    echo "Next: chạy lại với cùng BASE_URL / PAGES / PERF_SNAP + phase 'after' sau khi deploy thay đổi."
  fi
  echo "Report: $REPORT"
fi
