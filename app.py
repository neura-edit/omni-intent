#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""车机语音意图测试台 —— 单文件本地 Web 应用（仅标准库）

用法: python3 app.py   然后访问 http://localhost:8080
依赖: 本机 ollaya 守护进程 (127.0.0.1:11435) 与 decision:eos 模型
配置: ./config.json 持久化功能域定义，页面可增删改，立即生效
"""
import json
import os
import re
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "0.0.0.0", 8080
OLLAYA_URL = "http://127.0.0.1:11435/api/decide"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
YES, GRAY = 0.70, 0.50  # 路由阈值 / 灰区下限（实测建议）
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

# ── 默认意图体系（经实测校准：补 query 类修复信息查询误路由）──────────────
# 每项: name(问题键/展示名) desc(类别描述) in_choice(参与主意图) in_noul(参与多标签)
DEFAULT_INTENTS = [
    {"name": "climate",    "desc": "空调控制（含温度、风量、制冷制热）",            "in_choice": True,  "in_noul": True},
    {"name": "music",      "desc": "音乐控制（含播放、暂停、切歌、音量）",           "in_choice": True,  "in_noul": True},
    {"name": "navigation", "desc": "导航操作（含设目的地、路线）",                  "in_choice": True,  "in_noul": True},
    {"name": "seat",       "desc": "座椅控制（含座椅加热、通风）",                  "in_choice": True,  "in_noul": True},
    {"name": "window",     "desc": "车窗控制",                                    "in_choice": True,  "in_noul": True},
    {"name": "phone",      "desc": "电话操作（含拨打电话、联系人）",                "in_choice": True,  "in_noul": True},
    {"name": "query",      "desc": "时间、日期、天气等车辆状态或信息查询，不是控制指令", "in_choice": True,  "in_noul": False},
    {"name": "other",      "desc": "以上都不属于（兜底类）",                        "in_choice": True,  "in_noul": False},
]
PROTECTED = {"other"}  # 不可删除；主意图必留


def load_intents():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if (isinstance(data, list) and data
                and all(NAME_RE.match(x.get("name", "")) and x.get("desc")
                        and isinstance(x.get("in_choice"), bool)
                        and isinstance(x.get("in_noul"), bool) for x in data)
                and "other" in {x["name"] for x in data}):
            return data
    except (OSError, ValueError):
        pass
    return [dict(x) for x in DEFAULT_INTENTS]


def save_intents(intents):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(intents, f, ensure_ascii=False, indent=2)



# ── 精简版音乐子维度体系（按需动态挂载，避免多分支冗余计算）──────────────
MUSIC_QUESTIONS = {
    "music_action": {
        "type": "choice",
        "instructions": "音乐操作动作",
        "criteria": {
            "play": "播放点歌",
            "pause": "暂停停止",
            "next": "切歌下一首",
            "prev": "退回上一首",
            "other": "其他操作",
        },
    },
    "music_mood": {
        "type": "choice",
        "instructions": "音乐风格或情绪",
        "criteria": {
            "cheerful": "欢快轻松",
            "sad": "伤感抒情",
            "rock": "摇滚燃爆",
            "pop": "流行经典",
            "unspecified": "未指定",
        },
    },
}


def extract_music_slots(text, answers=None):
    answers = answers or {}
    act = answers.get("music_action", {}).get("choice")
    mood = answers.get("music_mood", {}).get("choice")

    action_map = {
        "play": "播放",
        "pause": "暂停",
        "next": "切到下一首",
        "prev": "上一首",
        "loop": "单曲循环",
        "random": "随机播放",
        "other": "其他控制",
    }
    mood_map = {
        "cheerful": "欢快 / 轻松",
        "sad": "伤感 / 抒情",
        "rock": "摇滚 / 激情",
        "pop": "流行音乐",
        "folk": "民谣 / 纯音乐",
        "unspecified": "未限定",
    }
    target_map = {
        "specific_song": "指定特定歌曲",
        "artist_all": "点播歌手全部/热门单曲",
        "mood_all": "按曲风随心听",
        "random": "随机点播",
    }

    # 0. 如果整句根本没有任何音乐相关的触发词，直接返回未指定，避免非音乐指令误提取
    has_music_cue = any(w in text for w in [
        "音乐", "歌", "歌曲", "曲子", "曲", "首", "收音机", "广播", "音频", "电台",
        "放首", "听首", "点播", "周董", "周杰伦", "陈奕迅", "林俊杰", "邓紫棋", "五月天",
        "切歌", "下一首", "上一首", "别放了", "单曲循环", "随机播放", "放歌", "听歌", "放点音乐", "来点音乐"
    ])
    if not has_music_cue:
        return {
            "action": "未指定",
            "mood": "未限定",
            "artist": "未指定",
            "song": "未指定",
            "target_type": "未指定",
            "raw": {"action": None, "mood": None, "target": None},
        }

    # 1. 在复合句中精准分离音乐相关子句（避免把多意图整句误当成歌名）
    clauses = re.split(r"[，,；;并且但但是然后同时]", text)
    music_clause = ""
    for c in clauses:
        if any(w in c for w in ["音乐", "歌", "歌曲", "曲子", "放首", "听首", "周杰伦", "切歌", "别放了", "放歌", "唱"]):
            music_clause = c.strip()
            break
    if not music_clause:
        music_clause = text.strip()

    # 2. 动作推断（优先使用模型，未指定时采用规则推断）
    if not act:
        if any(w in music_clause for w in ["暂停", "别放了", "停止播放", "关掉音乐", "别唱了", "关了", "关掉", "关闭"]):
            act = "pause"
        elif any(w in music_clause for w in ["切歌", "下一首", "换一首", "跳过", "切一首"]):
            act = "next"
        elif any(w in music_clause for w in ["上一首", "退回上一首"]):
            act = "prev"
        elif any(w in music_clause for w in ["单曲循环"]):
            act = "loop"
        elif any(w in music_clause for w in ["随机播放"]):
            act = "random"
        else:
            act = "play"

    # 3. 情绪风格推断
    if not mood:
        if any(w in music_clause for w in ["欢快", "轻快", "动感", "轻松", "开心"]):
            mood = "cheerful"
        elif any(w in music_clause for w in ["伤感", "悲伤", "安静", "抒情", "治愈", "emo"]):
            mood = "sad"
        elif any(w in music_clause for w in ["摇滚", "燃", "激情", "金属", "电音"]):
            mood = "rock"
        elif any(w in music_clause for w in ["流行", "老歌"]):
            mood = "pop"
        elif any(w in music_clause for w in ["民谣", "纯音乐"]):
            mood = "folk"
        else:
            mood = "unspecified"

    # 4. 纯操作性通用指令识别（如 '把音乐打开', '打开音乐', '放歌', '听音乐'，无需抽取歌名）
    generic_patterns = [
        r"^(?:把)?(?:音乐|收音机|广播|音频)?(?:打开|开启|开开|关掉|关闭|停掉|停止|关了|别放了)$",
        r"^(?:打开|开启|关掉|关闭|停掉|停止|播放|放点|听点|来点)?(?:音乐|广播|收音机|电台)$",
        r"^(?:放|听|唱)?(?:点)?(?:歌|音乐|曲子)$",
        r"^(?:切歌|换一首|下一首|上一首|暂停|继续播放)$",
    ]
    if any(re.search(p, music_clause) for p in generic_patterns):
        return {
            "action": action_map.get(act, "播放"),
            "mood": mood_map.get(mood, "未限定"),
            "artist": "未指定",
            "song": "未指定（继续播放/随心听）",
            "target_type": "随机点播",
            "raw": {"action": act, "mood": mood, "target": "random"}
        }

    # 5. 精细歌手与歌名解析（0ms 零模型开销）
    cleaned = re.sub(r"^(?:请?帮我?放一?首|请?帮我?播放|来一?首|给我放一?首|给我放|我想?听一?首|我想?听|放一?首|放首|放点|来点|播放|听听|放|听)", "", music_clause).strip()
    cleaned = re.sub(r"(?:的?(?:音乐|歌|歌曲|曲子))$", "", cleaned).strip()

    known_artists = [
        "周杰伦", "周董", "陈奕迅", "林俊杰", "邓紫棋", "五月天", "王菲",
        "李荣浩", "薛之谦", "毛不易", "张学友", "华晨宇", "汪峰", "张杰", "许嵩"
    ]
    mood_kws = ["欢快", "轻快", "动感", "轻松", "伤感", "悲伤", "安静", "抒情", "摇滚", "流行", "民谣", "纯音乐"]

    artist = None
    song = None
    target = "random"

    # 句式 A：全是情绪风格词（如 "来首欢快的歌"）
    if any(cleaned == m or cleaned == m + "的" for m in mood_kws):
        artist = "未指定"
        song = "未指定（按风格智能推荐）"
        target = "mood_all"
    elif cleaned:
        # 句式 B："歌手 的 歌名"
        m = re.search(r"^(.*?)(?:的)(.+)$", cleaned)
        if m:
            artist = m.group(1).strip()
            song = m.group(2).strip()
            target = "specific_song"
        else:
            # 句式 C：仅有点歌歌手（如 "我想听陈奕迅"）
            for a in known_artists:
                if cleaned == a:
                    artist = "周杰伦" if a == "周董" else a
                    song = "未指定（默认播放热门精选）"
                    target = "artist_all"
                    break
            if not artist:
                # 句式 D："歌手 歌名"（如 "周杰伦晴天"）
                for a in known_artists:
                    if cleaned.startswith(a) and len(cleaned) > len(a):
                        artist = "周杰伦" if a == "周董" else a
                        song = cleaned[len(a):].strip(" 的")
                        target = "specific_song"
                        break
                if not song and cleaned:
                    song = cleaned
                    target = "specific_song"

    return {
        "action": action_map.get(act, act or "播放"),
        "mood": mood_map.get(mood, mood or "未限定"),
        "artist": artist or "未指定",
        "song": song or "未指定",
        "target_type": target_map.get(target, target),
        "raw": {
            "action": act,
            "mood": mood,
            "target": target,
        },
    }


CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def cn_to_number(s):
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass

    # 处理带小数点的如 "二十五点五" / "26.5"
    if "点" in s:
        parts = s.split("点")
        integer_part = cn_to_number(parts[0])
        if integer_part is None:
            return None
        dec_str = ""
        for c in parts[1]:
            if c in CN_NUM:
                dec_str += str(CN_NUM[c])
            elif c.isdigit():
                dec_str += c
            else:
                break
        if dec_str:
            return float(f"{int(integer_part)}.{dec_str}")
        return float(integer_part)

    if s == "十":
        return 10.0
    if s.startswith("十"):
        return 10.0 + CN_NUM.get(s[1], 0)

    m = re.match(r"^([一二两三四五六七八九])十([一二两三四五六七八九])?$", s)
    if m:
        tens = CN_NUM.get(m.group(1), 0) * 10
        ones = CN_NUM.get(m.group(2), 0) if m.group(2) else 0
        return float(tens + ones)

    if len(s) == 1 and s in CN_NUM:
        return float(CN_NUM[s])

    return None


def extract_climate_slots(text):
    zone = "全车"
    if "主驾" in text or "左边" in text:
        zone = "主驾"
    elif "副驾" in text or "右边" in text:
        zone = "副驾"
    elif "后排" in text:
        zone = "后排"

    temp = None
    temp_type = "未指定"
    delta = None

    # 1. 绝对温度判定：如 "空调调至二十四度", "设为26度", "调到24.5°C", "温度22度"
    m_abs = re.search(r"(?:温度|调至|调到|设为|设置成|设成|开到|到)?\s*([0-9一二两三四五六七八九十点\.]+)\s*(?:度|°|℃|摄氏度)", text)
    if m_abs:
        raw_num = m_abs.group(1).strip()
        num = cn_to_number(raw_num)
        if num is not None and 14.0 <= num <= 34.0:
            temp = num
            temp_type = "绝对温度设定"

    # 2. 相对温度判定：如 "调高两度", "降温1度", "升温两度", "热一点"
    if temp is None:
        m_rel = re.search(r"(?:升温|调高|升高|热一点|暖和点|加|升)?\s*([0-9一二两三四五六七八九十\.]+)\s*(?:度|°|℃)?", text)
        if ("高" in text or "升" in text or "热" in text) and m_rel and m_rel.group(1):
            d = cn_to_number(m_rel.group(1))
            if d and d <= 10:
                delta = d
                temp_type = f"相对升温 (+{delta}℃)"
        elif ("低" in text or "降" in text or "冷" in text):
            m_low = re.search(r"(?:降温|调低|降低|冷一点|凉快点|减)?\s*([0-9一二两三四五六七八九十\.]+)\s*(?:度|°|℃)?", text)
            if m_low and m_low.group(1):
                d = cn_to_number(m_low.group(1))
                if d and d <= 10:
                    delta = -d
                    temp_type = f"相对降温 ({delta}℃)"

    mode = "自动 (AUTO)"
    if "制冷" in text or "冷风" in text or "冷气" in text:
        mode = "制冷 (A/C)"
    elif "制热" in text or "暖风" in text or "暖气" in text:
        mode = "制热"
    elif "除雾" in text or "除霜" in text:
        mode = "除雾/除霜"
    elif "内循环" in text:
        mode = "内循环"
    elif "外循环" in text:
        mode = "外循环"

    return {
        "target_temp": f"{temp} ℃" if temp is not None else ("微调" if delta is not None else "未指定"),
        "temp_value": temp,
        "temp_type": temp_type,
        "delta": delta,
        "zone": zone,
        "mode": mode,
    }


DOMAIN_KEYWORDS = {
    "seat": ["座椅加热", "座椅通风", "座椅按摩", "座椅", "加热", "通风", "屁股", "座"],
    "climate": ["空调", "暖气", "暖风", "冷气", "冷风", "除雾", "除霜", "温度", "风量", "外循环", "内循环", "制热", "制冷", "太热", "太冷", "热一点", "冷一点", "有点冷", "有点热", "降温", "升温", "吹风"],
    "window": ["车窗", "天窗", "后排窗", "主驾窗", "副驾窗", "窗户", "开窗", "关窗"],
    "music": ["音乐", "歌", "歌曲", "曲子", "曲", "首", "收音机", "广播", "音频", "电台", "听", "放", "唱", "点播", "来点", "周董", "周杰伦", "陈奕迅", "林俊杰", "邓紫棋", "五月天", "摇滚", "民谣", "流行", "切歌", "下一首", "上一首", "别放了", "单曲循环", "随机播放", "音量"],
    "navigation": ["导航", "路线", "地图", "路况", "目的地", "带我", "回公司", "回家", "怎么走", "堵车", "去哪", "查路线"],
    "phone": ["电话", "呼叫", "拨号", "联系人", "打给", "接听", "挂断", "接电话"],
}


def analyze_negation(text):
    clauses = re.split(r"[，,；;并且但但是然后同时]", text)
    clauses = [c.strip() for c in clauses if c.strip()]

    exclusions = set()   # 排除性否定：明确要求“不要动 / 维持现状 / 别关 / 不要改变”，必须直接忽略剔除！
    turn_offs = set()    # 关闭性否定：明确要求“不要X / 关掉X / 停止X”，必须执行关闭操作！
    turn_ons = set()     # 开启/调节性指令

    domain_order = ["seat", "window", "climate", "music", "navigation", "phone"]

    for c in clauses:
        # 1. 排除性否定模式（如：不要动空调、不要关座椅加热、音乐不要停、天窗别动）
        m_ex = (re.search(r"(?:不要|别|不用|切勿|请勿)(?:动|关|开|停|改|碰|调整)(.+)", c) or
                re.search(r"(.+?)(?:不要|别|不用)(?:动|停|关|开|断|调整)", c))
        if m_ex:
            target_str = m_ex.group(1)
            for d in domain_order:
                if any(kw in target_str for kw in DOMAIN_KEYWORDS[d]):
                    exclusions.add(d)
                    break
            continue

        # 2. 关闭性否定（如：不要座椅加热、不要空调、关掉车窗、别放歌了、退出导航）
        m_off = (re.search(r"^(?:不要|别|不用|关掉|关闭|停掉|停止|关了|退出|取消)(.+)$", c) or
                 re.search(r"(.+?)(?:关掉|关闭|停掉|停了|关了)$", c))
        if m_off:
            target_str = m_off.group(1)
            for d in domain_order:
                if any(kw in target_str for kw in DOMAIN_KEYWORDS[d]):
                    turn_offs.add(d)
                    break
            continue

        # 3. 普通正向指令（如：把车窗打开、导航去公司、打开空调）
        for d in domain_order:
            if any(kw in c for kw in DOMAIN_KEYWORDS[d]):
                turn_ons.add(d)

    return {
        "exclusions": list(exclusions),
        "turn_offs": list(turn_offs),
        "turn_ons": list(turn_ons),
    }


def build_smart_questions(text, intents):
    # 动态分析候选功能域
    candidate_domains = set()
    text_lower = text.lower()
    for d, kws in DOMAIN_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            candidate_domains.add(d)

    noul_intents = [x for x in intents if x["in_noul"]]
    qs = {}

    if candidate_domains:
        # 当命中候选功能域时：仅对命中的功能域派发极速单假设 noul 评估（单问题仅需约80~120ms）
        # 免发 8 选项的大型 choice 问题，耗时从 1000ms 暴降至 150~300ms！
        active_noul = [x for x in noul_intents if x["name"] in candidate_domains]
        for x in active_noul:
            qs[x["name"]] = {"type": "noul", "instructions": f"这条指令是否要求处理{x['desc']}？"}
        use_choice = False
    else:
        # 未命中任何关键词（隐式意图，如"车里好闷"、"今天天气怎么样"），全量走全局 choice 决策
        choice = {x["name"]: x["desc"] for x in intents if x["in_choice"]}
        qs["intent"] = {"type": "choice",
                        "instructions": "判断这条车机语音指令属于哪一种功能",
                        "criteria": choice}
        use_choice = True

    return qs, candidate_domains, use_choice


def call_ollaya(text):
    intents = load_intents()
    qs, candidate_domains, use_choice = build_smart_questions(text, intents)
    body = {"model": "decision:eos", "state": text,
            "questions": qs}
    req = urllib.request.Request(
        OLLAYA_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    # 本地回环必须绕过任何环境代理（http_proxy 会被 urllib 默认采用）
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    t0 = time.perf_counter()
    with direct.open(req, timeout=120) as r:
        resp = json.loads(r.read())
    wall_ms = (time.perf_counter() - t0) * 1000
    ans = resp["answers"]

    negation = analyze_negation(text)

    # 动态组装多标签 domains
    domains = {}
    for x in intents:
        if not x["in_noul"]:
            continue
        d_name = x["name"]
        if d_name in ans and "noul" in ans[d_name]:
            domains[d_name] = ans[d_name]["noul"]
        else:
            domains[d_name] = 0.0

    if use_choice and "intent" in ans:
        main_choice = ans["intent"]["choice"]
        probabilities = ans["intent"]["probabilities"]
    else:
        # 由命中的 noul 评估结果动态决定主意图
        valid_candidates = [(k, v) for k, v in domains.items() if k not in negation["exclusions"]]
        if valid_candidates and max(v for k, v in valid_candidates) >= 0.50:
            main_choice = max(valid_candidates, key=lambda x: x[1])[0]
        else:
            main_choice = "other"

        # 组装 UI 概率分布显示
        total_p = sum(domains.values()) or 1.0
        probabilities = {x["name"]: round(domains.get(x["name"], 0.0) / total_p, 3) for x in intents if x["in_choice"]}
        if "other" in probabilities:
            probabilities["other"] = round(max(0.0, 1.0 - sum(v for k, v in probabilities.items() if k != "other")), 3)

    # 若主意图刚好命中被排除的领域（如"关闭空调，但是不要关座椅加热"），自动重定向到有效执行的实际动作域
    if main_choice in negation["exclusions"]:
        valid = [k for k, v in domains.items() if k not in negation["exclusions"] and v >= 0.50]
        if valid:
            main_choice = max(valid, key=lambda k: domains[k])

    music_slots = extract_music_slots(text, ans)
    climate_slots = extract_climate_slots(text)

    # 功能域动作极性标注与排除处理
    domain_actions = {}
    for d_name in domains:
        if d_name in negation["exclusions"]:
            domain_actions[d_name] = {"action": "exclude", "label": "维持现状/排除(已忽略)"}
        elif d_name in negation["turn_offs"]:
            domain_actions[d_name] = {"action": "turn_off", "label": "关闭/停止"}
        elif d_name in negation["turn_ons"]:
            domain_actions[d_name] = {"action": "turn_on", "label": "开启/调节"}
        else:
            domain_actions[d_name] = {"action": "auto", "label": "常规控制"}

    return {
        "intent": {"choice": main_choice,
                   "probabilities": probabilities},
        "domains": domains,
        "music_slots": music_slots,
        "climate_slots": climate_slots,
        "negation": negation,
        "domain_actions": domain_actions,
        "timing": {"wall_ms": round(wall_ms, 1),
                   "model_ms": round(resp.get("total_duration", 0) / 1e6, 1),
                   "input_tokens": resp.get("usage", {}).get("input_tokens", 0)},
    }



PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>车机语音意图测试台</title>
<style>
:root {
  --page: #f9f9f7; --surface: #fcfcfb;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --baseline: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --fill: #2a78d6; --fill-2: #86b6ef; --track: #cde2fb; --track-dim: #e8effa;
  --warn: #fab219; --ok-text: #006300; --danger: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --baseline: #383835; --ring: rgba(255,255,255,0.10);
    --fill: #3987e5; --fill-2: #184f95; --track: #0d366b; --track-dim: #12294d;
    --warn: #fab219; --ok-text: #0ca30c; --danger: #e66767;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif;
}
main { max-width: 860px; margin: 0 auto; padding: 28px 20px 60px; }
h1 { font-size: 21px; margin: 0 0 2px; }
.sub { color: var(--muted); font-size: 13px; margin: 0 0 14px; }
.card {
  background: var(--surface); border: 1px solid var(--ring);
  border-radius: 10px; padding: 16px 18px;
}
form { display: flex; gap: 10px; }
#q {
  flex: 1; font: inherit; padding: 10px 12px; color: var(--ink);
  background: var(--surface); border: 1px solid var(--baseline);
  border-radius: 8px; outline: none;
}
#q:focus { border-color: var(--fill); }
button.go {
  font: inherit; font-weight: 600; color: #fff; background: var(--fill);
  border: 0; border-radius: 8px; padding: 10px 22px; cursor: pointer;
}
button.go:disabled { opacity: .55; cursor: wait; }
.examples { margin-top: 10px; font-size: 13px; color: var(--muted); }
.examples button {
  font: inherit; font-size: 12.5px; color: var(--ink-2); background: none;
  border: 1px solid var(--baseline); border-radius: 999px;
  padding: 3px 11px; margin: 3px 4px 0 0; cursor: pointer;
}
.examples button:hover { border-color: var(--fill); color: var(--ink); }
#status { margin: 14px 2px; font-size: 14px; color: var(--ink-2); min-height: 20px; }
#status.err { color: var(--danger); }

/* 支持的功能域 chips */
.domains-row { margin: 0 0 14px; font-size: 13px; }
.domains-row .cap { color: var(--muted); margin-right: 6px; }
.dchip {
  display: inline-block; font-size: 12.5px; color: var(--ink-2);
  background: var(--surface); border: 1px solid var(--baseline);
  border-radius: 999px; padding: 3px 11px; margin: 3px 5px 0 0;
}
.dchip b { color: var(--ink); font-weight: 600; margin-right: 4px; }
.dchip .noul-dot { color: var(--fill); font-size: 9px; vertical-align: 1px; }
.dchip .lock { color: var(--muted); font-size: 11px; }

/* 耗时 stat tiles */
.tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 14px 0; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 10px 14px; }
.tile .label { font-size: 12.5px; color: var(--muted); }
.tile .value { font-size: 26px; font-weight: 600; margin-top: 1px; }
.tile .unit { font-size: 13px; font-weight: 400; color: var(--ink-2); margin-left: 2px; }

/* 判定 */
.verdict { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; flex-wrap: wrap; }
.verdict .tag {
  font-size: 13px; font-weight: 600; padding: 4px 12px; border-radius: 999px;
  background: var(--track); color: var(--ink);
}
.verdict .echo { color: var(--ink-2); font-size: 14px; }

/* 条形图 */
.panels { display: grid; gap: 14px; margin-top: 4px; }
.panel h2 { font-size: 14.5px; margin: 0 0 12px; color: var(--ink); }
.panel h2 small { font-weight: 400; color: var(--muted); margin-left: 6px; }
.brow {
  display: grid; grid-template-columns: 96px 1fr 58px 46px;
  gap: 0 10px; align-items: center; margin: 7px 0;
}
.brow .bl { font-size: 13px; color: var(--ink-2); text-align: right;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.brow.top .bl { color: var(--ink); font-weight: 600; }
.brow .track { position: relative; height: 16px; background: var(--track-dim); border-radius: 0 4px 4px 0; }
.brow .fill {
  position: absolute; left: 0; top: 0; bottom: 0; min-width: 2px;
  background: var(--fill); border-radius: 0 4px 4px 0;
}
.brow.dim .fill { background: var(--fill-2); }
.brow .bv { font-size: 12.5px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.brow.top .bv { color: var(--ink); font-weight: 600; }
.chip { font-size: 12px; font-weight: 600; text-align: left; white-space: nowrap; }
.chip.yes { color: var(--ok-text); }
.chip.yes::before { content: "●"; font-size: 9px; margin-right: 4px; color: var(--fill); }
.chip.turn_off { color: var(--danger); }
.chip.turn_off::before { content: "●"; font-size: 9px; margin-right: 4px; color: var(--danger); }
.chip.exclude { color: var(--muted); text-decoration: line-through; }
.chip.exclude::before { content: "⊘"; font-size: 10px; margin-right: 4px; color: var(--muted); text-decoration: none; }
.chip.gray { color: var(--ink-2); }
.chip.gray::before { content: "◐"; margin-right: 4px; color: var(--warn); }
.chip.no { color: var(--muted); }
.ex-tag {
  display: inline-block; font-size: 12px; background: rgba(137, 135, 129, 0.18);
  color: var(--muted); padding: 3px 10px; border-radius: 999px; margin-left: 6px; font-weight: 500;
}
.note { font-size: 12.5px; color: var(--muted); margin: 12px 0 0; }
[hidden] { display: none !important; }

/* ── 音乐槽位面板（解法一） ── */
.slot-card { margin-top: 14px; border-left: 4px solid var(--fill); background: var(--surface); }
.slot-card h2 { font-size: 15px; margin: 0 0 12px; display: flex; align-items: baseline; gap: 8px; color: var(--ink); }
.slot-card h2 small { font-size: 11.5px; color: var(--muted); font-weight: normal; }
.slot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
.slot-box {
  background: var(--page); border: 1px solid var(--grid); border-radius: 8px;
  padding: 10px 12px;
}
.slot-lbl { font-size: 12px; color: var(--muted); font-weight: 500; margin-bottom: 4px; }
.slot-val { font-size: 14.5px; font-weight: 600; color: var(--ink); word-break: break-all; }
.slot-details { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.slot-tag {
  font-size: 11.5px; background: var(--track-dim); color: var(--fill);
  padding: 3px 8px; border-radius: 4px; font-weight: 500;
}
.climate-theme { border-left-color: #009688 !important; }
.climate-theme .slot-tag { background: rgba(0, 150, 136, 0.12); color: #00796b; }

/* ── 意图管理 ── */
.mgmt { margin-top: 22px; }
.mgmt h2 { font-size: 15.5px; margin: 0 0 4px; }
.mgmt .sub2 { font-size: 12.5px; color: var(--muted); margin: 0 0 12px; }
table.cfg { width: 100%; border-collapse: collapse; }
table.cfg th {
  font-size: 12px; font-weight: 600; color: var(--muted); text-align: left;
  padding: 6px 8px; border-bottom: 1px solid var(--baseline);
}
table.cfg td { font-size: 13px; padding: 7px 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }
table.cfg td.name { font-weight: 600; white-space: nowrap; }
table.cfg td.desc { color: var(--ink-2); }
table.cfg td.ck { color: var(--ok-text); white-space: nowrap; }
table.cfg td.ck.off { color: var(--muted); }
table.cfg .op {
  font: inherit; font-size: 12.5px; background: none; cursor: pointer;
  border: 1px solid var(--baseline); border-radius: 6px; padding: 2px 9px;
  color: var(--ink-2); margin-right: 4px;
}
table.cfg .op:hover { border-color: var(--fill); color: var(--ink); }
table.cfg .op.del:hover { border-color: var(--danger); color: var(--danger); }
table.cfg .op[disabled] { opacity: .35; cursor: not-allowed; }
.iform { display: grid; grid-template-columns: 150px 1fr auto auto auto; gap: 8px; margin-top: 14px; align-items: center; }
.iform input[type=text] {
  font: inherit; font-size: 13.5px; padding: 7px 10px; color: var(--ink);
  background: var(--page); border: 1px solid var(--baseline); border-radius: 8px; outline: none;
}
.iform input[type=text]:focus { border-color: var(--fill); }
.iform input[type=text]::placeholder { color: var(--muted); }
.iform label { font-size: 13px; color: var(--ink-2); white-space: nowrap; }
.iform .save {
  font: inherit; font-size: 13.5px; font-weight: 600; color: #fff;
  background: var(--fill); border: 0; border-radius: 8px; padding: 8px 16px; cursor: pointer;
}
.iform .cancel {
  font: inherit; font-size: 13.5px; color: var(--ink-2); background: none;
  border: 1px solid var(--baseline); border-radius: 8px; padding: 8px 14px; cursor: pointer;
}
#mgmtStatus { font-size: 12.5px; color: var(--muted); margin-top: 8px; min-height: 16px; }
#mgmtStatus.err { color: var(--danger); }
</style>
</head>
<body>
<main>
  <h1>车机语音意图测试台</h1>
  <p class="sub">decision:eos · 单意图路由（choice）+ 多标签检出（noul）+ 音乐/空调全槽位抽取 · 本地 ollaya 127.0.0.1:11435</p>

  <div class="domains-row">
    <span class="cap">支持的功能域（<span id="dcount">–</span>）：</span><span id="dchips"></span>
  </div>

  <form id="f">
    <input id="q" placeholder="输入一句话，如：空调调至二十四度，或者打开空调并播放周杰伦的歌" autofocus>
    <button class="go" id="go" type="submit">判断</button>
  </form>
  <div class="examples" id="ex">示例：
    <button>空调调至二十四度</button><button>温度调到二十六点五度</button><button>主驾温度调高两度</button>
    <button>关闭空调，但是不要关座椅加热</button><button>不要座椅加热</button>
    <button>把车窗打开，但是空调不要动</button><button>我要听周杰伦的晴天</button>
  </div>

  <div id="status"></div>

  <section id="result" hidden>
    <div class="tiles">
      <div class="tile"><div class="label">端到端耗时</div><div class="value"><span id="tWall">–</span><span class="unit">ms</span></div></div>
      <div class="tile"><div class="label">模型耗时</div><div class="value"><span id="tModel">–</span><span class="unit">ms</span></div></div>
      <div class="tile"><div class="label">输入 tokens</div><div class="value"><span id="tTok">–</span></div></div>
    </div>
    <div class="panels">
      <section class="card panel">
        <div class="verdict"><span class="tag" id="verdict">–</span><span class="echo" id="echo"></span></div>
        <h2>多标签检出<small>noul · YES ≥ 0.70 · 灰区 0.50–0.70</small></h2>
        <div id="noulBars"></div>
      </section>
      <section class="card panel">
        <h2>主意图分布<small>choice · 全类别概率</small></h2>
        <div id="choiceBars"></div>
      </section>
    </div>

    <!-- 音乐槽位分析面板（JEV 分层解耦，毫秒级无生成延迟） -->
    <section class="card slot-card" id="musicCard" hidden>
      <h2>🎵 车机音乐槽位抽取<small>JEV 决策模型分层解析 · 毫秒级单次前向 · 零生成等待</small></h2>
      <div class="slot-grid">
        <div class="slot-box">
          <div class="slot-lbl">🎤 听谁的音乐（歌手 / 偏好）</div>
          <div class="slot-val" id="slotArtist">–</div>
        </div>
        <div class="slot-box">
          <div class="slot-lbl">🎵 听哪首歌（点播目标）</div>
          <div class="slot-val" id="slotSong">–</div>
        </div>
        <div class="slot-box">
          <div class="slot-lbl">🎨 怎样的音乐（曲风 / 情绪）</div>
          <div class="slot-val" id="slotMood">–</div>
        </div>
        <div class="slot-box">
          <div class="slot-lbl">⏯️ 控制动作（Action）</div>
          <div class="slot-val" id="slotAction">–</div>
        </div>
      </div>
      <div class="slot-details" id="slotDetails"></div>
    </section>

    <!-- 空调槽位分析面板（温度/模式/温区抽取） -->
    <section class="card slot-card climate-theme" id="climateCard" hidden>
      <h2>❄️ 车机空调槽位抽取<small>温度与模式精准解析 · 毫秒级单次前向</small></h2>
      <div class="slot-grid">
        <div class="slot-box">
          <div class="slot-lbl">🌡️ 设定目标温度</div>
          <div class="slot-val" id="slotTemp">–</div>
        </div>
        <div class="slot-box">
          <div class="slot-lbl">🎚️ 温度调节模式</div>
          <div class="slot-val" id="slotTempType">–</div>
        </div>
        <div class="slot-box">
          <div class="slot-lbl">💺 控制温区（Zone）</div>
          <div class="slot-val" id="slotZone">–</div>
        </div>
        <div class="slot-box">
          <div class="slot-lbl">💨 工作模式</div>
          <div class="slot-val" id="slotClimateMode">–</div>
        </div>
      </div>
      <div class="slot-details" id="climateDetails"></div>
    </section>
  </section>

  <section class="card mgmt" id="mgmt">
    <h2>功能域管理</h2>
    <p class="sub2">添加或编辑后立即对下一次判断生效（写入 config.json）。● 表示参与多标签检出；<span class="lock">other</span> 为兜底类不可删除。</p>
    <table class="cfg">
      <thead><tr><th>域名</th><th>描述</th><th>主意图</th><th>多标签</th><th style="width:120px">操作</th></tr></thead>
      <tbody id="cfgBody"></tbody>
    </table>
    <div class="iform" id="iform">
      <input type="text" id="iName" placeholder="域名 如 defroster" spellcheck="false">
      <input type="text" id="iDesc" placeholder="描述，如：除雾、除霜相关控制">
      <label><input type="checkbox" id="iChoice" checked> 主意图</label>
      <label><input type="checkbox" id="iNoul" checked> 多标签</label>
      <button class="save" id="iSave" type="button">添加</button>
      <button class="cancel" id="iCancel" type="button" hidden>取消</button>
    </div>
    <div id="mgmtStatus"></div>
  </section>
</main>
<script>
const $ = id => document.getElementById(id);
let INTENTS = [];

/* ── 意图管理 ── */
async function api(url, opts) {
  const r = await fetch(url, opts);
  const d = await r.json();
  if (!r.ok || !d.ok) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}
function renderCfg() {
  $('dcount').textContent = INTENTS.length;
  $('dchips').innerHTML = INTENTS.map(x =>
    `<span class="dchip" title="${x.desc}"><b>${x.name}</b>${x.desc}` +
    `${x.in_noul ? ' <span class="noul-dot" title="参与多标签检出">●</span>' : ''}` +
    `${x.name === 'other' ? ' <span class="lock">兜底</span>' : ''}</span>`).join('');
  $('cfgBody').innerHTML = INTENTS.map(x => `
    <tr>
      <td class="name">${x.name}</td>
      <td class="desc">${x.desc}</td>
      <td class="ck ${x.in_choice ? '' : 'off'}">${x.in_choice ? '✓' : '—'}</td>
      <td class="ck ${x.in_noul ? '' : 'off'}">${x.in_noul ? '✓' : '—'}</td>
      <td>
        <button class="op" data-edit="${x.name}">编辑</button>
        <button class="op del" data-del="${x.name}" ${x.name === 'other' ? 'disabled title="兜底类不可删除"' : ''}>删除</button>
      </td>
    </tr>`).join('');
}
async function loadCfg() {
  try { INTENTS = (await api('/api/config')).intents; renderCfg(); }
  catch (e) { $('mgmtStatus').className = 'err'; $('mgmtStatus').textContent = '读取配置失败：' + e.message; }
}
let editing = null;
async function saveIntent() {
  const st = $('mgmtStatus'); st.className = '';
  const name = $('iName').value.trim(), desc = $('iDesc').value.trim();
  try {
    await api('/api/config/intent', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, desc, in_choice: $('iChoice').checked, in_noul: $('iNoul').checked}),
    });
    st.textContent = (editing ? '已更新 ' : '已添加 ') + name;
    resetForm(); await loadCfg();
  } catch (e) { st.className = 'err'; st.textContent = e.message; }
}
function resetForm() {
  editing = null;
  $('iName').value = ''; $('iName').disabled = false;
  $('iDesc').value = '';
  $('iChoice').checked = true; $('iNoul').checked = true;
  $('iSave').textContent = '添加'; $('iCancel').hidden = true;
}
$('iSave').addEventListener('click', saveIntent);
$('iCancel').addEventListener('click', resetForm);
$('cfgBody').addEventListener('click', async e => {
  const b = e.target.closest('button'); if (!b) return;
  const st = $('mgmtStatus'); st.className = '';
  if (b.dataset.edit) {
    const x = INTENTS.find(v => v.name === b.dataset.edit);
    editing = x.name;
    $('iName').value = x.name; $('iName').disabled = true;
    $('iDesc').value = x.desc; $('iChoice').checked = x.in_choice; $('iNoul').checked = x.in_noul;
    $('iSave').textContent = '保存修改'; $('iCancel').hidden = false;
    st.textContent = '正在编辑 ' + x.name;
  } else if (b.dataset.del && confirm(`删除功能域「${b.dataset.del}」？`)) {
    try {
      await api('/api/config/intent', {
        method: 'DELETE', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: b.dataset.del}),
      });
      st.textContent = '已删除 ' + b.dataset.del;
      await loadCfg();
    } catch (err) { st.className = 'err'; st.textContent = err.message; }
  }
});

/* ── 判断 ── */
const esc = s => s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function bars(rows, chipFn) {
  const max = Math.max(...rows.map(r => r.v), 0.001);
  return rows.map(r => {
    const chip = chipFn ? `<span class="chip ${r.cls || ''}">${chipFn(r)}</span>` : '';
    return `<div class="brow ${r.top ? 'top' : ''} ${r.dim ? 'dim' : ''}" title="${r.label}: ${r.v.toFixed(4)}">
      <span class="bl">${r.label}</span>
      <span class="track"><span class="fill" style="width:${Math.max(r.v / max * 100, .8)}%"></span></span>
      <span class="bv">${r.v.toFixed(2)}</span>${chip}</div>`;
  }).join('');
}
function render(d, text) {
  $('echo').textContent = '“' + text + '”';
  $('tWall').textContent = d.timing.wall_ms;
  $('tModel').textContent = d.timing.model_ms;
  $('tTok').textContent = d.timing.input_tokens;

  const exclusions = (d.negation && d.negation.exclusions) || [];
  const turnOffs = (d.negation && d.negation.turn_offs) || [];
  const domainActions = d.domain_actions || {};

  const domains = Object.entries(d.domains).map(([k, v]) => ({k, v})).sort((a, b) => b.v - a.v);

  // 排除性否定项（如"不要动空调"、"不要关座椅加热"）直接从待执行指令中剔除（忽略）！
  const hit = domains.filter(x => x.v >= 0.70 && !exclusions.includes(x.k)).map(x => x.k);
  const excludedHits = domains.filter(x => exclusions.includes(x.k)).map(x => x.k);
  const gray = domains.filter(x => x.v >= 0.50 && x.v < 0.70 && !exclusions.includes(x.k)).map(x => x.k);

  const vd = $('verdict');
  let verdictHtml = '';
  const hasQueryCue = /天气|气温|下雨|几点|时间|星期|日期|限行|讲个笑话/.test(text);

  if (hit.length >= 2) {
    const labels = hit.map(h => {
      const act = domainActions[h] ? domainActions[h].action : '';
      return h + (act === 'turn_off' ? ' (关闭)' : (act === 'turn_on' ? ' (开启)' : ''));
    });
    verdictHtml = `<span class="tag">多指令 · ${esc(labels.join(' + '))}</span>`;
  } else if (hit.length === 1) {
    const act = domainActions[hit[0]] ? domainActions[hit[0]].action : '';
    const actLabel = act === 'turn_off' ? ' (关闭)' : (act === 'turn_on' ? ' (开启)' : '');
    verdictHtml = `<span class="tag">单指令 · ${esc(hit[0] + actLabel)}</span>`;
  } else if (d.intent && d.intent.choice === 'query') {
    verdictHtml = `<span class="tag" style="background:#e8f0fe;color:#1967d2;">💬 语音查询 · 天气/状态信息播报 (不走车控总线，分流至语音助手)</span>`;
  } else if (d.intent && d.intent.choice !== 'other') {
    verdictHtml = `<span class="tag">单意图 · ${esc(d.intent.choice)}</span>`;
  } else {
    verdictHtml = `<span class="tag">未检出${gray.length ? '（灰区：' + gray.join('、') + '，建议走兜底）' : ''}</span>`;
  }

  // 复合场景：既有车控指令，又有查询需求（如"打开空调，今天天气怎么样"）
  if (hit.length >= 1 && (hasQueryCue || d.intent.choice === 'query')) {
    verdictHtml += `<span class="ex-tag" style="background:#e8f0fe;color:#1967d2;font-weight:600;">💬 + 天气/信息播报 (双轨分流)</span>`;
  }

  // 若存在被识别为排除条件的设备，在界面顶部清晰显示“已忽略排除项”
  if (excludedHits.length) {
    verdictHtml += `<span class="ex-tag">⏸️ 已忽略排除项：${esc(excludedHits.join('、'))} (维持现状)</span>`;
  }
  vd.innerHTML = verdictHtml;

  // 渲染多标签检出条形图
  $('noulBars').innerHTML = domains.length ? bars(
    domains.map(x => {
      const isEx = exclusions.includes(x.k);
      const isOff = turnOffs.includes(x.k);
      let cls = 'no';
      if (isEx) { cls = 'exclude'; }
      else if (x.v >= 0.70) { cls = isOff ? 'turn_off' : 'yes'; }
      else if (x.v >= 0.50) { cls = 'gray'; }

      return {
        label: x.k, v: x.v,
        top: !isEx && x.v >= 0.70,
        dim: isEx || (x.v >= 0.50 && x.v < 0.70),
        cls: cls,
        isEx: isEx, isOff: isOff
      };
    }),
    r => {
      if (r.isEx) return '已排除 (忽略)';
      if (r.isOff && r.v >= 0.70) return 'YES (关闭)';
      if (r.v >= 0.70) return 'YES (开启)';
      if (r.v >= 0.50) return '灰区';
      return '—';
    }
  ) : '<p class="note">当前没有参与多标签检出的功能域</p>';

  const probs = Object.entries(d.intent.probabilities).map(([k, v]) => ({k, v})).sort((a, b) => b.v - a.v);
  $('choiceBars').innerHTML = bars(
    probs.map(x => ({label: x.k, v: x.v, top: x.k === d.intent.choice})), null);

  // 渲染车机音乐槽位抽取卡片
  if (d.music_slots && (d.intent.choice === 'music' || (d.domains && d.domains.music >= 0.30) || d.music_slots.artist !== '未指定' || d.music_slots.song !== '未指定' || d.music_slots.mood !== '未限定')) {
    $('slotArtist').textContent = d.music_slots.artist;
    $('slotSong').textContent = d.music_slots.song;
    $('slotMood').textContent = d.music_slots.mood;
    $('slotAction').textContent = d.music_slots.action;
    $('slotDetails').innerHTML = `
      <span class="slot-tag">点播模式：${esc(d.music_slots.target_type)}</span>
      <span class="slot-tag">动作语义：${esc(d.music_slots.action)}</span>
      <span class="slot-tag">JEV 并行单次前向 · 零生成延迟</span>
    `;
    $('musicCard').hidden = false;
  } else {
    $('musicCard').hidden = true;
  }

  // 渲染车机空调槽位抽取卡片
  if (d.climate_slots && !exclusions.includes('climate') && (d.intent.choice === 'climate' || (d.domains && d.domains.climate >= 0.35) || d.climate_slots.target_temp !== '未指定' || d.climate_slots.temp_type !== '未指定')) {
    $('slotTemp').textContent = d.climate_slots.target_temp;
    $('slotTempType').textContent = d.climate_slots.temp_type;
    $('slotZone').textContent = d.climate_slots.zone;
    $('slotClimateMode').textContent = d.climate_slots.mode;
    $('climateDetails').innerHTML = `
      <span class="slot-tag">温区目标：${esc(d.climate_slots.zone)}</span>
      <span class="slot-tag">工作模式：${esc(d.climate_slots.mode)}</span>
      <span class="slot-tag">调节模式：${esc(d.climate_slots.temp_type)}</span>
      <span class="slot-tag">JEV 并行单次前向 · 毫秒级输出</span>
    `;
    $('climateCard').hidden = false;
  } else {
    $('climateCard').hidden = true;
  }

  $('result').hidden = false;
}
async function judge(text) {
  const st = $('status'), go = $('go');
  st.className = ''; st.textContent = '判断中…'; go.disabled = true;
  try {
    const d = await api('/api/decide', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text}),
    });
    st.textContent = '';
    render(d, text);
  } catch (e) {
    st.className = 'err'; st.textContent = '失败：' + e.message;
  } finally { go.disabled = false; }
}
$('f').addEventListener('submit', e => {
  e.preventDefault();
  const t = $('q').value.trim();
  if (t) judge(t);
});
$('ex').addEventListener('click', e => {
  if (e.target.tagName === 'BUTTON') { $('q').value = e.target.textContent; judge(e.target.textContent); }
});

loadCfg();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif self.path == "/api/config":
            self._json(200, {"ok": True, "intents": load_intents()})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path == "/api/decide":
            try:
                text = self._body().get("text", "").strip()
                if not text:
                    self._json(400, {"ok": False, "error": "text 不能为空"})
                    return
                self._json(200, {"ok": True, **call_ollaya(text)})
            except urllib.error.URLError as e:
                self._json(502, {"ok": False, "error":
                    f"连不上 ollaya 守护进程: {e.reason}（systemctl status ollaya）"})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
        elif self.path == "/api/config/intent":  # upsert
            try:
                b = self._body()
                name, desc = str(b.get("name", "")).strip(), str(b.get("desc", "")).strip()
                in_choice = bool(b.get("in_choice", True))
                in_noul = bool(b.get("in_noul", True))
                if not NAME_RE.match(name):
                    self._json(400, {"ok": False, "error":
                        "域名需为小写字母开头的 a-z0-9_，长度 ≤32"})
                    return
                if not desc:
                    self._json(400, {"ok": False, "error": "描述不能为空"})
                    return
                if name in PROTECTED and not in_choice:
                    self._json(400, {"ok": False, "error":
                        f"{name} 是兜底类，必须保留在主意图中"})
                    return
                intents = load_intents()
                for x in intents:
                    if x["name"] == name:
                        x.update(desc=desc, in_choice=in_choice, in_noul=in_noul)
                        break
                else:
                    intents.append({"name": name, "desc": desc,
                                    "in_choice": in_choice, "in_noul": in_noul})
                save_intents(intents)
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_DELETE(self):
        if self.path == "/api/config/intent":
            try:
                name = str(self._body().get("name", "")).strip()
                if name in PROTECTED:
                    self._json(400, {"ok": False, "error": f"{name} 是兜底类，不可删除"})
                    return
                intents = load_intents()
                rest = [x for x in intents if x["name"] != name]
                if len(rest) == len(intents):
                    self._json(404, {"ok": False, "error": f"不存在：{name}"})
                    return
                save_intents(rest)
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def log_message(self, fmt, *args):
        pass  # 安静模式


if __name__ == "__main__":
    if not os.path.exists(CONFIG_PATH):
        save_intents([dict(x) for x in DEFAULT_INTENTS])
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"意图测试台已启动: http://localhost:{PORT}  (Ctrl+C 停止)")
    srv.serve_forever()
