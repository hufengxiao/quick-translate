"""词根分析模块 — 分析英语单词的前缀、词根、后缀

Provides morphological analysis of English words by identifying:
- Prefixes (e.g., un-, re-, pre-)
- Roots (e.g., struct, duct, port)
- Suffixes (e.g., -tion, -ment, -able)
"""

import re
from typing import Dict, List, Optional, Tuple


# ── 前缀数据库 ──
PREFIXES: Dict[str, str] = {
    # 否定/反义
    "un": "不，非，相反",
    "in": "不，非（用于辅音前）",
    "im": "不，非（用于 b/m/p 前）",
    "il": "不，非（用于 l 前）",
    "ir": "不，非（用于 r 前）",
    "non": "非，不",
    "dis": "不，否定，分离",
    "mis": "错误地",
    "anti": "反对，对抗",
    "counter": "反对，相反",
    # 位置/方向
    "inter": "之间，相互",
    "intra": "内部",
    "intro": "向内",
    "extra": "外部，超出",
    "super": "在上，超过",
    "supra": "在上，超",
    "sub": "在下，低于",
    "under": "在下，不足",
    "over": "过度，在上",
    "trans": "跨越，变换",
    " circum": "周围",
    "circum": "周围",
    "ambi": "两侧，周围",
    # 时间/顺序
    "pre": "之前",
    "ante": "之前",
    "fore": "前，预先",
    "post": "之后",
    "re": "再次，回",
    "retro": "向后，回顾",
    # 数量
    "uni": "一",
    "mono": "一，单",
    "bi": "二，双",
    "di": "二，双",
    "tri": "三",
    "multi": "多",
    "poly": "多",
    # 关系/程度
    "co": "共同",
    "com": "共同（用于 b/m/p 前）",
    "con": "共同",
    "col": "共同（用于 l 前）",
    "cor": "共同（用于 r 前）",
    "syn": "共同，一起",
    "sym": "共同，一起（用于 b/m/p 前）",
    "auto": "自动，自身",
    "self": "自身",
    "homo": "相同",
    "hetero": "不同",
    "iso": "等，同",
    "neo": "新的",
    "paleo": "古老的",
    "proto": "最初的，原始",
    "pseudo": "假的，伪",
    # 其他常用
    "en": "使成为",
    "em": "使成为（用于 b/m/p 前）",
    "be": "使成为，加以",
    "ex": "前，出",
    "out": "超过，外",
    "up": "向上",
    "down": "向下",
    "mid": "中间",
    "cross": "交叉",
    "pan": "全，泛",
    "micro": "微小",
    "macro": "大，宏观",
    "mega": "巨大",
    "hyper": "过度，超",
    "hypo": "不足，低于",
    "tele": "远距离",
    "semi": "半",
    "quasi": "准，类似",
    "ultra": "超，极端",
    "infra": "低于，下",
    "mal": "坏，不良",
    "bene": "好",
    "eu": "好，优",
}


# ── 后缀数据库 ──
SUFFIXES: Dict[str, Dict[str, str]] = {
    # 名词后缀
    "tion": {"pos": "n.", "meaning": "行为，状态，结果"},
    "sion": {"pos": "n.", "meaning": "行为，状态，结果"},
    "ment": {"pos": "n.", "meaning": "行为，结果，手段"},
    "ness": {"pos": "n.", "meaning": "性质，状态"},
    "ity": {"pos": "n.", "meaning": "性质，状态"},
    "ance": {"pos": "n.", "meaning": "行为，状态"},
    "ence": {"pos": "n.", "meaning": "行为，状态"},
    "er": {"pos": "n.", "meaning": "做…的人/物"},
    "or": {"pos": "n.", "meaning": "做…的人/物"},
    "ist": {"pos": "n.", "meaning": "从事…的人"},
    "ism": {"pos": "n.", "meaning": "主义，学说，行为"},
    "ant": {"pos": "n./adj.", "meaning": "做…的人；有…性质的"},
    "ent": {"pos": "n./adj.", "meaning": "做…的人；有…性质的"},
    "ee": {"pos": "n.", "meaning": "受…的人"},
    "eer": {"pos": "n.", "meaning": "从事…的人"},
    "hood": {"pos": "n.", "meaning": "身份，状态"},
    "ship": {"pos": "n.", "meaning": "身份，状态，技能"},
    "dom": {"pos": "n.", "meaning": "领域，状态"},
    "ure": {"pos": "n.", "meaning": "行为，结果"},
    "age": {"pos": "n.", "meaning": "行为，状态，集合"},
    "al": {"pos": "n.", "meaning": "行为，过程"},
    "ence": {"pos": "n.", "meaning": "性质，状态"},
    "ling": {"pos": "n.", "meaning": "小的，与…有关的人"},
    "let": {"pos": "n.", "meaning": "小的"},
    "ette": {"pos": "n.", "meaning": "小的，女性"},
    "ful": {"pos": "n.", "meaning": "充满…的量"},
    "ery": {"pos": "n.", "meaning": "场所，行为，状态"},
    "ary": {"pos": "n.", "meaning": "与…相关的人/物"},
    "ory": {"pos": "n.", "meaning": "与…相关的人/物/场所"},
    "cy": {"pos": "n.", "meaning": "状态，性质"},
    "ry": {"pos": "n.", "meaning": "行为，状态，集合"},
    "ics": {"pos": "n.", "meaning": "学科，活动"},
    "ology": {"pos": "n.", "meaning": "学科，研究"},
    # 形容词后缀
    "able": {"pos": "adj.", "meaning": "能…的，可…的"},
    "ible": {"pos": "adj.", "meaning": "能…的，可…的"},
    "ful": {"pos": "adj.", "meaning": "充满…的"},
    "less": {"pos": "adj.", "meaning": "没有…的"},
    "ous": {"pos": "adj.", "meaning": "有…性质的"},
    "ious": {"pos": "adj.", "meaning": "有…性质的"},
    "ive": {"pos": "adj.", "meaning": "有…倾向的"},
    "ative": {"pos": "adj.", "meaning": "有…倾向的"},
    "al": {"pos": "adj.", "meaning": "与…有关的"},
    "ial": {"pos": "adj.", "meaning": "与…有关的"},
    "ic": {"pos": "adj.", "meaning": "与…有关的"},
    "ical": {"pos": "adj.", "meaning": "与…有关的"},
    "ary": {"pos": "adj.", "meaning": "与…有关的"},
    "ory": {"pos": "adj.", "meaning": "与…有关的"},
    "y": {"pos": "adj.", "meaning": "有…特征的"},
    "ish": {"pos": "adj.", "meaning": "像…的，有点…的"},
    "like": {"pos": "adj.", "meaning": "像…的"},
    "esque": {"pos": "adj.", "meaning": "…风格的"},
    "ern": {"pos": "adj.", "meaning": "方向的"},
    "ward": {"pos": "adj./adv.", "meaning": "朝…方向的"},
    "an": {"pos": "adj.", "meaning": "与…有关的"},
    "ian": {"pos": "adj.", "meaning": "与…有关的"},
    "ant": {"pos": "adj.", "meaning": "有…性质的"},
    "ent": {"pos": "adj.", "meaning": "有…性质的"},
    # 动词后缀
    "ize": {"pos": "v.", "meaning": "使…化"},
    "ise": {"pos": "v.", "meaning": "使…化（英式）"},
    "ify": {"pos": "v.", "meaning": "使…化"},
    "fy": {"pos": "v.", "meaning": "使…化"},
    "en": {"pos": "v.", "meaning": "使变得"},
    "ate": {"pos": "v.", "meaning": "使…"},
    # 副词后缀
    "ly": {"pos": "adv.", "meaning": "以…方式"},
    "ward": {"pos": "adv.", "meaning": "朝…方向"},
    "wards": {"pos": "adv.", "meaning": "朝…方向"},
    "wise": {"pos": "adv.", "meaning": "以…方式"},
}


# ── 常见词根 ──
ROOTS: Dict[str, str] = {
    # 拉丁/希腊词根
    "act": "做，行动",
    "ag": "做，驱动",
    "alter": "改变，其他",
    "annu": "年",
    "aqu": "水",
    "aud": "听",
    "bell": "战争",
    "brev": "短",
    "cap": "拿，抓",
    "capt": "拿，抓",
    "ced": "走，让步",
    "ceed": "走",
    "cess": "走",
    "cide": "杀，切",
    "circ": "圆，环",
    "claim": "叫，喊",
    "clar": "清楚",
    "clud": "关闭",
    "clus": "关闭",
    "cord": "心",
    "corp": "体",
    "cred": "相信",
    "cur": "跑，流",
    "curs": "跑",
    "dict": "说",
    "doc": "教",
    "duc": "引导",
    "duct": "引导",
    "equ": "平等",
    "fac": "做",
    "fact": "做",
    "fer": "携带，带来",
    "fin": "结束，界限",
    "flect": "弯曲",
    "flex": "弯曲",
    "flu": "流",
    "form": "形状",
    "fort": "强",
    "frag": "破",
    "fract": "破",
    "fus": "流，倾倒",
    "gen": "产生，种类",
    "grad": "步，级",
    "graph": "写，画",
    "gress": "走",
    "ject": "投，扔",
    "jud": "判断",
    "junct": "连接",
    "lect": "选，读",
    "leg": "法，读",
    "liber": "自由",
    "loc": "地方",
    "log": "词，说，学科",
    "loqu": "说",
    "mand": "命令",
    "manu": "手",
    "med": "治疗，中间",
    "mem": "记忆",
    "merg": "浸没",
    "migr": "迁移",
    "min": "小",
    "mir": "惊奇，看",
    "miss": "送，发",
    "mit": "送，发",
    "mov": "动",
    "mot": "动",
    "mut": "改变",
    "nat": "出生",
    "nav": "船",
    "nect": "连接",
    "nomin": "名",
    "norm": "标准",
    "not": "标记",
    "nov": "新",
    "numer": "数",
    "oper": "工作",
    "opt": "选择",
    "ord": "顺序",
    "organ": "工具，器官",
    "pact": "约定",
    "pass": "感情，通过",
    "path": "感情，疾病",
    "ped": "脚",
    "pel": "推，驱",
    "pend": "悬挂，支付",
    "plic": "折叠",
    "pon": "放",
    "pos": "放",
    "port": "携带",
    "pot": "能力",
    "press": "压",
    "prim": "第一",
    "prob": "测试，证明",
    "proper": "自己的",
    "puls": "推",
    "pur": "纯净",
    "put": "思考",
    "quir": "寻求",
    "quisit": "寻求",
    "rect": "正，直",
    "rupt": "破",
    "sacr": "神圣",
    "scend": "攀爬",
    "sci": "知道",
    "scrib": "写",
    "script": "写",
    "sec": "跟随",
    "sect": "切",
    "sed": "坐",
    "sent": "感觉",
    "sens": "感觉",
    "sequ": "跟随",
    "serv": "保持，服务",
    "sid": "坐",
    "sign": "标记",
    "sist": "站立",
    "sol": "单独，太阳",
    "solv": "松开",
    "son": "声音",
    "spec": "看",
    "spect": "看",
    "spir": "呼吸",
    "st": "站立",
    "sta": "站立",
    "stat": "站立",
    "stit": "建立",
    "struct": "建造",
    "sum": "拿，取",
    "tact": "接触",
    "tain": "保持",
    "techn": "技术",
    "tele": "远",
    "temp": "时间",
    "tend": "伸展",
    "tens": "伸展",
    "terr": "土地",
    "test": "测试，证明",
    "text": "编织",
    "theo": "神",
    "therm": "热",
    "tor": "扭",
    "tort": "扭",
    "tract": "拉，拖",
    "trib": "给予",
    "turb": "搅乱",
    "umbr": "影子",
    "uni": "一",
    "urb": "城市",
    "vac": "空",
    "vad": "走",
    "val": "强，价值",
    "ven": "来",
    "vent": "来",
    "ver": "真实",
    "verb": "词",
    "vers": "转",
    "vert": "转",
    "vi": "路",
    "via": "路",
    "vis": "看",
    "vit": "生命",
    "viv": "生命",
    "voc": "声音，叫",
    "vol": "意志，卷",
    "volv": "卷",
}


def analyze_word(word: str) -> Dict[str, object]:
    """分析英语单词的前缀、词根、后缀。

    Args:
        word: 要分析的英语单词

    Returns:
        dict with keys:
        - word: 原始单词
        - prefix: {str, meaning} or None
        - root: {str, meaning} or None
        - suffix: {str, meaning, pos} or None
        - parts: list of {type, str, meaning[, pos]}
    """
    if not word or not word.isalpha():
        return {"word": word, "prefix": None, "root": None, "suffix": None, "parts": []}

    w = word.lower().strip()
    parts = []
    prefix_info = None
    suffix_info = None
    root_info = None

    # Step 1: Match suffix (longest match first)
    matched_suffix_len = 0
    for suf in sorted(SUFFIXES.keys(), key=len, reverse=True):
        if w.endswith(suf) and len(suf) > matched_suffix_len and len(w) - len(suf) >= 2:
            suffix_info = {
                "str": "-" + suf,
                "meaning": SUFFIXES[suf]["meaning"],
                "pos": SUFFIXES[suf].get("pos", ""),
            }
            matched_suffix_len = len(suf)
            break

    # Step 2: Match prefix (longest match first)
    stem_after_suffix = w[:len(w) - matched_suffix_len] if matched_suffix_len else w
    matched_prefix_len = 0
    for pfx in sorted(PREFIXES.keys(), key=len, reverse=True):
        if stem_after_suffix.startswith(pfx) and len(pfx) >= 2 and len(stem_after_suffix) - len(pfx) >= 2:
            # Avoid matching 're' when it's part of a root like 'receive'
            # Only match if removing prefix leaves a reasonable stem
            prefix_info = {
                "str": pfx + "-",
                "meaning": PREFIXES[pfx],
            }
            matched_prefix_len = len(pfx)
            break

    # Step 3: Find root in remaining stem
    stem = w
    if matched_prefix_len:
        stem = stem[matched_prefix_len:]
    if matched_suffix_len:
        stem = stem[:len(stem)]

    # The "stem" is what remains after removing prefix and suffix
    remaining = w
    if matched_prefix_len:
        remaining = remaining[matched_prefix_len:]
    if matched_suffix_len:
        remaining = remaining[:len(remaining) - matched_suffix_len]

    # Try to find a root in the remaining stem
    # First try exact substring match, then try if root starts with stem
    # (handles cases where suffix consumed part of root, e.g., construction = con+struct+tion)
    if len(remaining) >= 3:
        best_root = None
        best_root_len = 0
        for rt in sorted(ROOTS.keys(), key=len, reverse=True):
            if len(rt) >= 3:
                if rt in remaining:
                    # Exact substring match — prefer longest
                    if len(rt) > best_root_len:
                        best_root = rt
                        best_root_len = len(rt)
                elif remaining in rt and len(remaining) >= 3:
                    # Stem is prefix of root (suffix consumed part of root)
                    if len(rt) > best_root_len:
                        best_root = rt
                        best_root_len = len(rt)
        if best_root:
            root_info = {
                "str": best_root,
                "meaning": ROOTS[best_root],
            }

    # Build parts list
    if prefix_info:
        parts.append({"type": "prefix", **prefix_info})
    if root_info:
        parts.append({"type": "root", **root_info})
    if suffix_info:
        parts.append({"type": "suffix", **suffix_info})

    return {
        "word": word,
        "prefix": prefix_info,
        "root": root_info,
        "suffix": suffix_info,
        "parts": parts,
    }


def format_analysis(word: str) -> str:
    """格式化词根分析结果为可读文本。

    Returns:
        例如: "unhappiness: un-(不) + happi + -ness(性质，状态)"
        如果无分析结果，返回空字符串。
    """
    result = analyze_word(word)
    parts = result["parts"]
    if not parts:
        return ""

    segments = []
    w = word.lower()
    consumed = 0

    for part in parts:
        ptype = part["type"]
        raw = part["str"]

        if ptype == "prefix":
            pfx = raw.rstrip("-")
            segments.append(f"{raw}({part['meaning']})")
            consumed = len(pfx)
        elif ptype == "root":
            segments.append(f"{raw}({part['meaning']})")
        elif ptype == "suffix":
            suf = raw.lstrip("-")
            segments.append(f"{raw}({part['meaning']})")

    return " → ".join(segments)
