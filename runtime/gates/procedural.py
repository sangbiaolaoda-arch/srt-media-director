"""Procedural normalization gates."""
import json  # noqa: F401
import os  # noqa: F401
import shutil  # noqa: F401
import sys  # noqa: F401
import tempfile  # noqa: F401

from gate_lib import (  # noqa: F401
    GATES, gate, RUNTIME, ROOT, EXAMPLE_SRT, EXAMPLE_OVERRIDES,
    _example_beats, _example_dsl, pytest_approx,
    _MOTION_TRUTH_DIRS, _EASE_FINGERPRINTS, _MAT_FINGERPRINTS,
)

import beat_planner  # noqa: F401
import composition_planner  # noqa: F401
import entrance_planner  # noqa: F401
import html_adapter  # noqa: F401
import pipeline  # noqa: F401
import raster_renderer  # noqa: F401
import srt_parser  # noqa: F401
import svg_art  # noqa: F401
import visual_director  # noqa: F401


@gate("24. Procedural 归一（确定性种子 + 布局/晶格单一真相源）")
def g24():
    """PROCEDURAL NORMALIZATION · P1 的机器证据门禁。

    验证：① 唯一 Canonical Procedural 包可导入且边界守卫 PASS；
          ② 种子策略可复现且与 PYTHONHASHSEED 无关；
          ③ 生产实现不再自造 RNG / 硬编码种子（静态扫描为空）；
          ④ ref_frame 的分槽与 svg_art 的晶格已委托 canonical layout；
          ⑤ 契约 contracts/procedural_semantics.v1.json 存在且迁移映射一致。
    """
    import procedural_canonical as PC

    # ① 边界守卫：canonical procedural 只能是 stdlib 叶子
    br = PC.boundary_report()
    assert br["status"] == "PASS", br
    PC.assert_boundaries()

    # ② 确定性：默认种子与逐拍种子可复现，且不依赖 PYTHONHASHSEED
    probe = PC.audit.determinism_probe()
    assert probe["default_reproducible"], probe
    assert probe["beat_reproducible"], probe
    assert probe["hash_seed_independent"], probe
    assert PC.rng.DEFAULT_SEED == 20261003, PC.rng.DEFAULT_SEED

    # ③ 无第二个种子真相源：runtime 内（canonical 包外）不得出现 random.* / 硬编码种子
    hits = PC.audit.seed_sources()
    assert hits == [], hits

    # ④ 布局 / 晶格委托：ref_frame 必须是 canonical layout 的薄封装
    import ref_frame as _R
    from procedural_canonical import layout as _L
    assert _R.cols(3) == _L.slots(3, _R.MARGIN, _R.CONTENT_W, _R.COL_GAP)
    assert _R.rows(4, 100, 400, 20) == _L.stacks(4, 100, 400, 20)
    assert _L.lattice(3, 2, 10, 20, 5, 7) == \
        [(10, 20), (15, 20), (20, 20), (10, 27), (15, 27), (20, 27)]
    # 逐拍种子的 recipe 与旧内联 md5 零偏差（迁移 M8）
    import hashlib as _hl
    _beat = {"beat_id": "b01", "narration": "注意力被反复打断"}
    _legacy = int(_hl.md5(("%s|%s" % (_beat["beat_id"], _beat["narration"]))
                          .encode("utf-8")).hexdigest()[:8], 16)
    assert PC.rng.stable_seed(PC.rng.beat_key(_beat)) == _legacy

    # ⑤ 契约存在且映射一致
    import json as _json
    _root = ROOT
    with open(os.path.join(_root, "contracts", "procedural_semantics.v1.json")) as fh:
        _c = _json.load(fh)
    assert _c["contract_id"] == "procedural_semantics.v1"
    assert set(_c["owns"]["rng"]) >= {"stable_seed", "default_rng", "rng_for_beat"}
    assert set(_c["owns"]["layout"]) >= {"slots", "stacks", "lattice"}
