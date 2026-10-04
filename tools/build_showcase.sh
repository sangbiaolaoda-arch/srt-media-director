#!/usr/bin/env bash
# 重渲 showcase 全部样例为 MP4，并生成 README 用的 GIF 预览。
# 依赖：imageio-ffmpeg（自带静态 ffmpeg）。
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${OUT:-out/showcase}"
mkdir -p "$OUT"

FF="$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')"

for case in examples/showcase/*/; do
  name="$(basename "$case")"
  srt="$case/case.srt"
  [ -f "$srt" ] || continue
  mp4="$OUT/$name.mp4"
  echo "== render $name =="
  python3 runtime/render_video.py --srt "$srt" --out "$mp4"

  # GIF 预览：前 6 秒，560px 宽，10fps，调色板优化（README 内联播放用）
  echo "   preview.gif"
  "$FF" -y -ss 2 -t 6 -i "$mp4" \
    -vf "fps=10,scale=560:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5" \
    "$case/preview.gif" >/dev/null 2>&1
done

echo "done. MP4 -> $OUT ; GIF -> examples/showcase/*/preview.gif"
