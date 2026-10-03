# SRT Media Director — 常用入口
# 复杂度是刻意保留的（防 agent 犯错），但这些入口让「改 → 看」尽量短。

PY ?= python
OUT ?= sample/out

.PHONY: help install test sample video clean lint

help:
	@echo "make install   安装依赖（含 SVG / MP4 可选增强）"
	@echo "make test      运行 runtime/self_test.py（8 道门禁）"
	@echo "make sample    编译并渲染前 30 秒样例（sample/out/）"
	@echo "make video     渲染完整示例 MP4（examples/minimal）"
	@echo "make clean     清理 __pycache__ 与样例产物"

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install cairosvg imageio-ffmpeg

test:
	$(PY) runtime/self_test.py

sample:
	$(PY) runtime/make_sample.py 30

video:
	$(PY) runtime/render_video.py \
		--srt examples/minimal/attention.srt \
		--overrides examples/minimal/director_overrides.json \
		--out $(OUT)/attention-sample.mp4

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf sample/out
