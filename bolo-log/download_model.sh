#!/usr/bin/env bash
# Parallel chunked download of the Whisper small model.bin (483,546,902 bytes)
set -e
URL="https://hf-mirror.com/Systran/faster-whisper-small/resolve/main/model.bin"
SIZE=483546902
N=8
CH=$((SIZE/N+1))
pids=()
for i in $(seq 0 7); do
  S=$((i*CH))
  E=$(( (i+1)*CH-1 ))
  [ $E -ge $SIZE ] && E=$((SIZE-1))
  curl -sL --retry 3 -r "$S-$E" -o "part_$i.bin" "$URL" &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p" || echo "part download pid $p failed"; done

# verify and assemble
TOTAL=$(cat part_*.bin | wc -c)
echo "assembling, total=$TOTAL (expected $SIZE)"
if [ "$TOTAL" -eq "$SIZE" ]; then
  cat part_0.bin part_1.bin part_2.bin part_3.bin part_4.bin part_5.bin part_6.bin part_7.bin > models/small/model.bin
  echo "sha256:"
  sha256sum models/small/model.bin
fi
