#!/usr/bin/env bash
# Parallel chunked downloader, generic: download_to.sh URL SIZE OUTPUT NCHUNKS
set -u
URL="$1"; SIZE="$2"; OUT="$3"; N="$4"
CH=$((SIZE/N+1))
pids=()
rm -f "$OUT".part_*
for i in $(seq 0 $((N-1))); do
  S=$((i*CH))
  E=$(( (i+1)*CH-1 ))
  [ $E -ge $SIZE ] && E=$((SIZE-1))
  curl -sL --retry 3 -r "$S-$E" -o "$OUT.part_$i" "$URL" &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p" || echo "pid $p failed"; done
TOTAL=$(cat "$OUT".part_* | wc -c)
echo "total=$TOTAL expected=$SIZE"
if [ "$TOTAL" -eq "$SIZE" ]; then
  cat $(ls "$OUT".part_* | sort -t_ -k4 -n) > "$OUT"
  rm -f "$OUT".part_*
  echo "OK: $OUT"
  sha256sum "$OUT"
else
  echo "MISMATCH; keeping parts"
fi
