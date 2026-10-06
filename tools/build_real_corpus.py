#!/usr/bin/env python3
"""Build the fixed Real Content Evaluation Corpus (P0-3).

Writes 21 realistic SRTs (20-30 target) across 6 categories into
``tests/corpus/real-content/``.  Realistic subtitle content, NOT machine
placeholders: each cue is a genuine sentence a narrator might say.  Committed so
the corpus is fixed and reproducible.

Categories (matching the P0-3 brief):
    explanation           科普解释
    narrative_emotion     叙事情感
    data_comparison       数据对比
    abstract_philosophy   抽象哲理
    longform              长内容
    adversarial_repetition 易重复/对抗
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "tests", "corpus", "real-content")


def _ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def srt(cues):
    """cues: list of (start_sec, end_sec, text)."""
    blocks = []
    for i, (a, b, t) in enumerate(cues, 1):
        blocks.append("%d\n%s --> %s\n%s\n" % (i, _ts(a), _ts(b), t))
    return "\n".join(blocks)


# --------------------------------------------------------------------------- #
# Each entry: path -> list of (start, end, text).  Durations ~2.0-4.5s.
CORPUS = {
    "explanation/e01-quantum-computing.srt": [
        (0.0, 3.2, "传统计算机用比特存储信息"),
        (3.2, 6.6, "每个比特只能是 0 或者 1"),
        (6.6, 10.2, "而量子比特可以同时是 0 和 1 的叠加"),
        (10.2, 14.0, "这意味着它能并行探索海量的可能性"),
        (14.0, 17.8, "在特定问题上, 量子计算机指数级地更快"),
        (17.8, 21.6, "但它并不适合所有任务, 这是常见的误解"),
    ],
    "explanation/e02-black-hole.srt": [
        (0.0, 3.4, "黑洞并不是宇宙里的一个洞"),
        (3.4, 7.2, "它是质量极大、体积极小的天体"),
        (7.2, 11.0, "引力强到连光都无法逃离它的边界"),
        (11.0, 14.6, "这个边界叫做事件视界"),
        (14.6, 18.4, "一旦越过视界, 任何物体都无法返回"),
        (18.4, 22.0, "时间和空间在这里被彻底重新定义"),
    ],
    "explanation/e03-mrna-vaccine.srt": [
        (0.0, 3.0, "mRNA 疫苗的核心是一段信使 RNA"),
        (3.0, 6.6, "它只是把病毒的刺突蛋白图纸送进细胞"),
        (6.6, 10.4, "细胞照着图纸生产刺突蛋白"),
        (10.4, 14.0, "免疫系统认出它并建立记忆"),
        (14.0, 17.6, "真正的病毒到来时, 身体已经准备好了"),
    ],
    "explanation/e04-cpu-vs-gpu.srt": [
        (0.0, 3.2, "CPU 像几个博士, 擅长处理复杂的逻辑"),
        (3.2, 7.0, "GPU 像成千上万个小学生, 擅长重复的运算"),
        (7.0, 10.8, "图形渲染恰好需要大量相同的并行计算"),
        (10.8, 14.4, "这就是 GPU 在游戏和 AI 里如此重要的原因"),
    ],
    "narrative_emotion/n01-reunion.srt": [
        (0.0, 3.4, "十年了, 她终于又站在了这家店门口"),
        (3.4, 7.0, "橱窗里还挂着那张泛黄的照片"),
        (7.0, 10.8, "她伸手推门, 风铃的声音和记忆里一模一样"),
        (10.8, 14.6, "老板娘抬起头, 愣了两秒钟"),
        (14.6, 18.2, "然后她笑了, 眼眶却红了"),
        (18.2, 21.8, "有些地方, 是走多远都忘不掉的"),
    ],
    "narrative_emotion/n02-regret.srt": [
        (0.0, 3.2, "他总觉得来日方长"),
        (3.2, 6.8, "总觉得那个电话明天打也一样"),
        (6.8, 10.4, "直到有一天, 号码再也无人接听"),
        (10.4, 14.2, "遗憾从来不是轰然降临的"),
        (14.2, 18.0, "它藏在每一个被推迟的今天里"),
    ],
    "narrative_emotion/n03-courage.srt": [
        (0.0, 3.0, "她第一次站上那个舞台"),
        (3.0, 6.6, "手心全是汗, 稿子在抖"),
        (6.6, 10.2, "台下几百双眼睛望着她"),
        (10.2, 13.8, "她深吸一口气, 说出了第一个字"),
        (13.8, 17.4, "勇气不是不害怕, 而是害怕但仍然向前"),
    ],
    "narrative_emotion/n04-farewell.srt": [
        (0.0, 3.2, "火车缓缓驶出站台"),
        (3.2, 6.8, "他隔着车窗挥手, 嘴唇在动"),
        (6.8, 10.4, "她知道他说的是 别等我"),
        (10.4, 14.0, "但她还是站在原地, 一直站到看不见"),
    ],
    "data_comparison/d01-gdp.srt": [
        (0.0, 3.2, "两国 GDP 在二十年前基本持平"),
        (3.2, 6.8, "但增速出现了明显分化"),
        (6.8, 10.6, "A 国年均增长 6.8%, B 国只有 2.1%"),
        (10.6, 14.4, "到 2024 年, 差距被拉大到三倍以上"),
        (14.4, 18.0, "复利的力量在长时间尺度上极其惊人"),
    ],
    "data_comparison/d02-market-share.srt": [
        (0.0, 3.0, "智能手机市场份额前三名合计 61%"),
        (3.0, 6.8, "其中第一名独占 27%"),
        (6.8, 10.4, "剩下的 39% 被十几家厂商瓜分"),
        (10.4, 14.0, "这是一个典型的高集中度市场"),
    ],
    "data_comparison/d03-growth-rate.srt": [
        (0.0, 3.2, "用户数从 100 万增长到 800 万"),
        (3.2, 6.8, "只用了十八个月"),
        (6.8, 10.6, "月均复合增长率达到 12.4%"),
        (10.6, 14.2, "这种曲线往往难以持续三年以上"),
    ],
    "data_comparison/d04-benchmark.srt": [
        (0.0, 3.2, "新芯片单核跑分提升了 18%"),
        (3.2, 6.8, "但功耗只增加了 5%"),
        (6.8, 10.6, "能效比是这一代最大的进步"),
        (10.6, 14.2, "综合体验的提升远大于数字本身"),
    ],
    "abstract_philosophy/a01-time.srt": [
        (0.0, 3.4, "时间并不存在, 存在的只是变化"),
        (3.4, 7.2, "我们从未真正抓住过任何一个瞬间"),
        (7.2, 11.0, "所谓现在, 不过是过去与未来的缝隙"),
        (11.0, 14.8, "人无法两次踏入同一条河流"),
    ],
    "abstract_philosophy/a02-freedom.srt": [
        (0.0, 3.2, "自由不是想做什么就做什么"),
        (3.2, 7.0, "而是不想做什么时, 可以不做"),
        (7.0, 10.8, "真正的自由是一种拒绝的能力"),
        (10.8, 14.6, "它需要清醒, 也需要代价"),
    ],
    "abstract_philosophy/a03-paradox.srt": [
        (0.0, 3.4, "这句话是假话"),
        (3.4, 7.2, "如果它是真的, 那它就是假的"),
        (7.2, 11.0, "如果它是假的, 那它就是真的"),
        (11.0, 14.8, "悖论提醒我们, 语言也有它的边界"),
    ],
    "longform/l01-history.srt": [
        (0.0, 3.4, "公元前三世纪, 这里还是一片荒原"),
        (3.4, 7.4, "第一批移民沿着河流定居下来"),
        (7.4, 11.4, "他们开垦、筑城、通商, 逐渐繁荣"),
        (11.4, 15.4, "此后的一千年里, 王朝更替了十余次"),
        (15.4, 19.4, "但这座城市始终没有离开这片土地"),
        (19.4, 23.4, "直到近代, 蒸汽机改变了它的一切"),
        (23.4, 27.4, "铁路把这里和世界连在了一起"),
        (27.4, 31.4, "今天, 我们仍能看见那些旧日的痕迹"),
    ],
    "longform/l02-tutorial.srt": [
        (0.0, 3.2, "第一步, 先安装运行环境"),
        (3.2, 6.8, "第二步, 创建一个新的项目目录"),
        (6.8, 10.6, "第三步, 把示例代码复制进去"),
        (10.6, 14.4, "第四步, 运行测试确认一切正常"),
        (14.4, 18.2, "第五步, 根据需求修改配置文件"),
        (18.2, 22.0, "最后, 部署到服务器即可上线"),
    ],
    "longform/l03-documentary.srt": [
        (0.0, 3.6, "在海拔四千米的高原上"),
        (3.6, 7.6, "有一种动物一生都在迁徙"),
        (7.6, 11.6, "它们追逐水草, 也追逐季节"),
        (11.6, 15.6, "科学家花了整整十年跟踪这群生灵"),
        (15.6, 19.6, "记录它们的路线、繁衍与死亡"),
        (19.6, 23.6, "这或许是对生命最朴素的敬意"),
    ],
    "adversarial_repetition/r01-number-list.srt": [
        (0.0, 3.0, "第一个要点是明确定义问题"),
        (3.0, 6.0, "第二个要点是收集相关数据"),
        (6.0, 9.0, "第三个要点是分析数据规律"),
        (9.0, 12.0, "第四个要点是提出可行方案"),
        (12.0, 15.0, "第五个要点是评估方案风险"),
        (15.0, 18.0, "第六个要点是执行并复盘"),
    ],
    "adversarial_repetition/r02-repetitive-structure.srt": [
        (0.0, 3.2, "我们需要更快的网络"),
        (3.2, 6.4, "我们需要更低的延迟"),
        (6.4, 9.6, "我们需要更强的算力"),
        (9.6, 12.8, "我们需要更好的算法"),
        (12.8, 16.0, "我们需要更可靠的系统"),
    ],
    "adversarial_repetition/r03-filler.srt": [
        (0.0, 3.0, "总而言之, 这个方案有很多优点"),
        (3.0, 6.2, "众所周知, 团队一直在努力"),
        (6.2, 9.4, "值得注意的是, 未来还有很多可能"),
        (9.4, 12.6, "综上所述, 我们需要继续前进"),
    ],
}


def main():
    n = 0
    for rel, cues in CORPUS.items():
        path = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(srt(cues))
        n += 1
    cats = {}
    for rel in CORPUS:
        cats[rel.split("/")[0]] = cats.get(rel.split("/")[0], 0) + 1
    print("wrote %d SRTs to %s" % (n, os.path.relpath(OUT, REPO)))
    print("categories:", cats)


if __name__ == "__main__":
    main()
