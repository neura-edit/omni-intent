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
    {"name": "query",      "desc": "时间、日期、天气等信息查询或问答",                "in_choice": True,  "in_noul": True},
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


def is_english_query(text):
    cn_chars = len(re.findall(r"[\u4e00-\u9fa5]", text))
    en_words = len(re.findall(r"[A-Za-z]+", text))
    return en_words > cn_chars


DOMAIN_INSTRUCTIONS_EN = {
    "climate": "Climate or A/C control (temperature, fan, cooling, heating)",
    "music": "Music control (playing songs, pausing, skipping tracks, volume)",
    "navigation": "Navigation or GPS route guidance (setting destination or directions)",
    "seat": "Seat control (seat heating, ventilation, massage)",
    "window": "Window or sunroof control (opening, closing windows)",
    "phone": "Phone call or dialing a contact",
    "query": "Information query (weather, time, date, battery range, traffic)",
    "other": "None of the above"
}

DOMAIN_INSTRUCTIONS_CN = {
    "climate": "空调控制（含温度、风量、制冷制热）",
    "music": "音乐控制（含播放、暂停、切歌、音量）",
    "navigation": "导航操作（含设目的地、路线）",
    "seat": "座椅控制（含座椅加热、通风）",
    "window": "车窗控制（含车窗、天窗）",
    "phone": "电话操作（含拨打电话、呼叫联系人）",
    "query": "时间、日期、天气等信息查询或问答",
    "other": "以上都不属于（兜底类）"
}


# ── 全曲风与双语音乐槽位抽取体系 ───────────────────────────────────────────
GENRE_MAP = {
    "classical": ("古典 / Classical", ["古典", "古典音乐", "交响乐", "管弦乐", "协奏曲", "室内乐", "歌剧", "巴赫", "莫扎特", "贝多芬", "肖邦", "classical", "symphony", "orchestra", "concerto", "opera", "bach", "mozart", "beethoven", "chopin"]),
    "jazz": ("爵士 / Jazz", ["爵士", "爵士乐", "布鲁斯爵士", "波萨诺瓦", "jazz", "bebop", "swing", "bossa nova", "bossa"]),
    "blues": ("蓝调 / Blues", ["布鲁斯", "蓝调", "节奏布鲁斯", "blues", "rhythm and blues"]),
    "rock": ("摇滚 / Rock", ["摇滚", "摇滚乐", "重金属", "硬摇滚", "朋克", "黑胶", "金属", "rock", "hard rock", "alternative rock", "punk", "grunge"]),
    "metal": ("重金属 / Metal", ["金属", "重金属", "死亡金属", "黑金属", "前卫金属", "metal", "heavy metal", "death metal", "black metal", "thrash"]),
    "pop": ("流行 / Pop", ["流行", "流行音乐", "老歌", "经典老歌", "华语流行", "欧美流行", "粤语歌", "粤语老歌", "pop", "kpop", "jpop", "cpop", "chart", "hits"]),
    "edm": ("电音 / EDM", ["电音", "电子音乐", "电子乐", "dj", "夜店", "慢摇", "蹦迪", "edm", "electronic", "house", "techno", "trance", "dubstep", "synthwave"]),
    "hiphop": ("说唱 / Hip-Hop", ["说唱", "嘻哈", "hiphop", "hip hop", "rap", "trap", "freestyle", "flow"]),
    "rnb_soul": ("R&B / Soul", ["r&b", "rnb", "节奏布鲁斯", "灵魂乐", "soul", "motown", "neo soul"]),
    "folk": ("民谣 / Folk", ["民谣", "民歌", "民乐", "乡村音乐", "乡村", "folk", "acoustic", "bluegrass"]),
    "country": ("乡村 / Country", ["乡村音乐", "乡村", "country music", "country"]),
    "piano_inst": ("钢琴 / 器乐 / Instrumental", ["钢琴", "钢琴曲", "吉他", "吉他曲", "小提琴", "萨克斯", "古筝", "二胡", "乐器", "piano", "instrumental", "guitar", "violin", "saxophone", "cello"]),
    "ambient_lofi": ("轻音乐 / Lo-Fi / Ambient", ["轻音乐", "纯音乐", "器乐", "背景音乐", "bgm", "白噪音", "助眠", "冥想", "ambient", "lofi", "lo-fi", "chill", "chillout", "sleep", "meditation", "relaxing"]),
    "gufeng": ("国风 / 古风 / Chinese Style", ["古风", "国风", "中国风", "汉服", "仙侠", "戏腔", "chinese traditional", "gufeng", "chinese style"]),
    "ost": ("影视原声 / OST", ["原声", "原声带", "配乐", "影视原声", "电影原声", "动漫原声", "游戏原声", "ost", "soundtrack", "score", "theme song"]),
    "reggae": ("雷鬼 / Reggae", ["雷鬼", "reggae", "ska", "dub"]),
    "latin": ("拉丁 / Latin", ["拉丁", "萨尔萨", "探戈", "salsa", "tango", "latin", "bachata", "samba", "reggaeton"]),
    "funk_disco": ("放克 / Disco", ["放克", "迪斯科", "disco", "funk", "groove"]),
    "indie": ("独立音乐 / Indie", ["独立音乐", "独立摇滚", "独立流行", "indie", "indie pop", "indie rock"]),
    "children": ("少儿 / 儿歌 / Children", ["儿歌", "童谣", "宝宝巴士", "睡前故事", "少儿", "children", "kids", "nursery rhymes"]),
    "talk": ("曲艺 / 播客 / Podcast", ["相声", "评书", "小品", "脱口秀", "故事", "广播剧", "播客", "podcast", "talk show", "audiobook"])
}

MOOD_MAP = {
    "sad": ("伤感/低落 · Sad/Healing", ["心情很差", "心情不好", "难过", "心烦", "烦躁", "郁闷", "抑郁", "伤感", "悲伤", "失恋", "伤心", "emo", "压抑", "哭", "低落", "痛苦", "难受", "治愈", "sad", "unhappy", "depressed", "heartbroken", "down", "sorrow", "healing", "gloomy"]),
    "cheerful": ("欢快/提神 · Upbeat/Energetic", ["开心", "高兴", "兴奋", "心情好", "愉快", "欢快", "轻快", "动感", "轻松", "嗨", "激情", "燃", "提神", "嗨一点", "happy", "cheerful", "energetic", "upbeat", "excited", "pumped", "party"]),
    "calm": ("舒缓/安静 · Calm/Relaxed", ["安静", "抒情", "舒缓", "放松", "想静静", "静一静", "催眠", "助眠", "睡前", "冥想", "发呆", "温和", "柔和", "calm", "relax", "relaxing", "peaceful", "quiet", "sleepy", "soothing", "chill"])
}

ADJECTIVE_MOODS = [
    "动感", "欢快", "轻快", "轻松", "伤感", "悲伤", "安静", "舒缓", "治愈", "柔和", "温和",
    "激情", "燃", "摇滚", "好听", "热门", "经典", "最新", "老", "新", "催眠", "助眠", "放松",
    "开心", "难过", "低落", "兴奋", "浪漫", "甜蜜", "伤心", "孤独",
    "happy", "sad", "calm", "chill", "relaxing", "energetic", "popular", "classic"
]

GENRE_TERMS = set()
for _, (lbl, kws) in GENRE_MAP.items():
    GENRE_TERMS.add(lbl)
    GENRE_TERMS.update(kws)

KNOWN_ARTISTS_CN = [
    "周杰伦", "周董", "陈奕迅", "林俊杰", "邓紫棋", "五月天", "王菲",
    "李荣浩", "薛之谦", "毛不易", "张学友", "华晨宇", "汪峰", "张杰", "许嵩",
    "许巍", "朴树", "刀郎", "李健", "周深", "孙燕姿", "张韶涵", "梁静茹",
    "莫文蔚", "伍佰", "动力火车", "陶喆", "王力宏", "凤凰传奇", "赵雷"
]

KNOWN_ARTISTS_EN = [
    "Taylor Swift", "Ed Sheeran", "Adele", "Coldplay", "Billie Eilish",
    "Justin Bieber", "Bruno Mars", "The Weeknd", "Drake", "Eminem",
    "Michael Jackson", "Queen", "Maroon 5", "Lady Gaga", "Rihanna",
    "Dua Lipa", "Imagine Dragons", "Beyonce", "Post Malone", "Katy Perry"
]


def extract_music_slots(text, answers=None):
    text_lower = text.lower()
    has_cue = any(w in text_lower for w in [
        "音乐", "歌", "歌曲", "曲子", "曲", "首", "收音机", "广播", "音频", "电台",
        "放首", "听首", "点播", "播放", "播", "放", "听", "唱",
        "切歌", "下一首", "上一首", "别放了", "单曲循环", "随机播放", "放歌", "听歌", "放点音乐", "来点音乐",
        "music", "song", "songs", "track", "tune", "play", "listen", "radio", "volume",
        "pause", "next", "previous", "skip", "shuffle", "repeat"
    ]) or any(a.lower() in text_lower for a in KNOWN_ARTISTS_CN + KNOWN_ARTISTS_EN) or any(g in text_lower for g in GENRE_TERMS)

    if not has_cue:
        return {
            "action": "未指定 / Unspecified",
            "mood": "未限定 / Any Mood",
            "artist": "未指定 / Unspecified",
            "song": "未指定 / Unspecified",
            "target_type": "未指定 / Unspecified",
            "raw": {"action": None, "mood": None, "target": None},
        }

    # 1. 动作推断
    if any(w in text_lower for w in ["暂停", "别放了", "停止播放", "关掉音乐", "别唱了", "关了", "关掉", "关闭", "pause", "stop music", "stop playing"]):
        action = "暂停 / Pause"
    elif any(w in text_lower for w in ["切歌", "下一首", "换一首", "跳过", "切一首", "next song", "next track", "next", "skip"]):
        action = "切到下一首 / Next Track"
    elif any(w in text_lower for w in ["上一首", "退回上一首", "previous song", "previous track", "previous", "prev"]):
        action = "上一首 / Previous Track"
    elif any(w in text_lower for w in ["单曲循环", "loop", "repeat"]):
        action = "单曲循环 / Repeat Track"
    elif any(w in text_lower for w in ["随机播放", "shuffle", "random"]):
        action = "随机播放 / Shuffle"
    else:
        action = "播放 / Play"

    # 2. 情绪与曲风推断
    detected_mood = None
    for m_code, (m_lbl, kws) in MOOD_MAP.items():
        if any(k in text_lower for k in kws):
            detected_mood = m_lbl
            break

    detected_genre = None
    for g_code, (g_lbl, kws) in GENRE_MAP.items():
        if any(k in text_lower for k in kws):
            detected_genre = g_lbl
            break

    if detected_mood and detected_genre:
        mood_display = f"{detected_mood} · {detected_genre}"
    elif detected_mood:
        mood_display = detected_mood
    elif detected_genre:
        mood_display = f"{detected_genre}"
    else:
        mood_display = "未限定 / Any Mood"

    # 3. 抽取音乐分句
    clauses = re.split(r"[,;!?，；！？]|\band\b|\bbut\b|\bthen\b|并且|但是|然后|同时|顺便|而且|接着", text, flags=re.I)
    music_clause = ""
    for c in clauses:
        c_str = c.strip()
        if any(w in c_str.lower() for w in ["音乐", "歌", "歌曲", "曲子", "放", "听", "唱", "点播", "播放", "播", "首", "切歌", "下一首", "上一首", "别放了", "收音机", "电台", "play", "listen", "hear", "song", "music", "track"] + [a.lower() for a in KNOWN_ARTISTS_CN + KNOWN_ARTISTS_EN] + list(GENRE_TERMS)):
            music_clause = c_str
            break
    if not music_clause:
        music_clause = text.strip()

    # 4. 通用操作指令匹配（在音乐子句上匹配，如 '把音乐打开'、'play music'）
    generic_patterns = [
        r"^(?:把)?(?:音乐|收音机|广播|音频)?(?:打开|开启|开开|关掉|关闭|停掉|停止|关了|别放了)$",
        r"^(?:打开|开启|关掉|关闭|停掉|停止|播放|放点|听点|来点)?(?:音乐|广播|收音机|电台)$",
        r"^(?:放|听|唱)?(?:点)?(?:歌|音乐|曲子)$",
        r"^(?:切歌|换一首|下一首|上一首|暂停|继续播放)$",
        r"^(?:turn\s+on|start|play|resume|stop|pause|turn\s+off)?\s*(?:the\s+)?(?:music|radio|songs?|audio|player)$",
        r"^(?:next|previous|skip|pause|resume|shuffle)\s*(?:song|track)?$"
    ]
    if any(re.search(p, music_clause.lower()) for p in generic_patterns):
        return {
            "action": action,
            "mood": mood_display,
            "artist": "未指定 / Unspecified",
            "song": "未指定（继续播放/随心听） / Continue Playback",
            "target_type": "随机点播 / Shuffle",
            "raw": {"action": action, "mood": mood_display, "target": "random"}
        }

    artist = None
    song = None
    target = "random"

    # 英文特定句式解析
    m_en1 = re.search(r"(?:play|listen to|hear)\s+(?:the\s+song\s+)?(.+?)\s+by\s+([A-Za-z0-9\s\.\'-]+)", music_clause, re.I)
    if m_en1:
        song = m_en1.group(1).strip()
        artist = m_en1.group(2).strip()
        target = "specific_song"
    else:
        m_en2 = re.search(r"(?:play|listen to)\s+([A-Za-z0-9\s\.\'-]+?)\'s\s+(.+)", music_clause, re.I)
        if m_en2:
            artist = m_en2.group(1).strip()
            song = m_en2.group(2).strip()
            target = "specific_song"
        else:
            for a in KNOWN_ARTISTS_EN:
                if re.search(r"\b" + re.escape(a) + r"\b", music_clause, re.I):
                    artist = a
                    song = "Popular Hits / 热门精选"
                    target = "artist_all"
                    break

    # 中文语法规则解析
    if not artist and not song:
        pattern = r"^(?:[我你他]?\s*(?:还|又|也|就|再|顺便|接着|然后|先|麻烦|请)?\s*(?:想要|想|要|打算|希望能?|帮我|给我|替我|为我)?\s*(?:播放|点播|放|听|播|唱|来|搜|查)?\s*(?:一?[首曲支]|首歌曲|首歌|首曲子|点|下|个)?\s*)+"
        cleaned = re.sub(pattern, "", music_clause).strip()
        cleaned = re.sub(r"(?:的?(?:音乐|歌|歌曲|曲子))$", "", cleaned).strip()
        cleaned = re.sub(r"^(?:play|listen to|hear)?\s*(?:some|a\s+song|a\s+track|a\s+piece\s+of)?\s*", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"(?:music|songs?|track)?$", "", cleaned, flags=re.I).strip()

        is_pure_genre_or_mood = (cleaned.lower() in [g.lower() for g in GENRE_TERMS]) or (cleaned.lower() in [m.lower() for m in ADJECTIVE_MOODS])

        if is_pure_genre_or_mood or (not cleaned and (detected_genre or detected_mood)):
            tag_desc = []
            if detected_genre: tag_desc.append(detected_genre)
            if detected_mood: tag_desc.append(detected_mood)
            desc_str = " + ".join(tag_desc) if tag_desc else "风格"
            artist = "未指定 / Unspecified"
            song = f"未指定（按 {desc_str} 智能推荐） / Recommendation"
            target = "genre_mood_all"
        elif cleaned:
            m_cn = re.search(r"^(.*?)(?:的)(.+)$", cleaned)
            if m_cn:
                left = m_cn.group(1).strip()
                right = m_cn.group(2).strip()
                if left in ADJECTIVE_MOODS or right in GENRE_TERMS or right in ["歌", "音乐", "歌曲", "曲子"]:
                    artist = "未指定 / Unspecified"
                    song = f"未指定（按{left}风格智能推荐）"
                    target = "genre_mood_all"
                else:
                    artist = left
                    song = right
                    target = "specific_song"
            else:
                for a in KNOWN_ARTISTS_CN:
                    if cleaned == a:
                        artist = "周杰伦" if a == "周董" else a
                        song = "未指定（默认播放热门精选）"
                        target = "artist_all"
                        break
                if not artist:
                    for a in KNOWN_ARTISTS_CN:
                        if cleaned.startswith(a) and len(cleaned) > len(a):
                            artist = "周杰伦" if a == "周董" else a
                            song = cleaned[len(a):].strip(" 的")
                            target = "specific_song"
                            break
                    if not song and cleaned:
                        song = cleaned
                        target = "specific_song"

    target_map = {
        "specific_song": "指定特定单曲 / Specific Song",
        "artist_all": "歌手热门精选 / Popular Songs",
        "genre_mood_all": "风格/情绪智能推荐 / Genre & Mood Mix",
        "random": "随机点播 / Shuffle"
    }

    return {
        "action": action,
        "mood": mood_display,
        "artist": artist or "未指定 / Unspecified",
        "song": song or "未指定 / Unspecified",
        "target_type": target_map.get(target, target),
        "raw": {"action": action, "mood": mood_display, "target": target},
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
    text_lower = text.lower()
    zone = "全车 / All Zones"
    if "主驾" in text or "driver" in text_lower or "left side" in text_lower:
        zone = "主驾 / Driver"
    elif "副驾" in text or "passenger" in text_lower or "right side" in text_lower:
        zone = "副驾 / Passenger"
    elif "后排" in text or "rear" in text_lower or "back seat" in text_lower:
        zone = "后排 / Rear"

    temp = None
    temp_type = "未指定 / Unspecified"
    delta = None

    # 1. 绝对温度判定 (EN + CN)
    m_abs_en = re.search(r"(?:set\s+(?:the\s+)?(?:temp|temperature)\s+to|temp\s+to|make\s+it)\s*([0-9\.]+)\s*(?:degrees|degree|c|celsius|f|°c)?", text_lower)
    m_abs_cn = re.search(r"(?:温度|调至|调到|设为|设置成|设成|开到|到)?\s*([0-9一二两三四五六七八九十点\.]+)\s*(?:度|°|℃|摄氏度)", text)

    if m_abs_en:
        num = float(m_abs_en.group(1))
        if 55.0 <= num <= 90.0:  # 华氏度转摄氏度
            num = round((num - 32) * 5 / 9, 1)
        if 14.0 <= num <= 34.0:
            temp = num
            temp_type = "绝对温度设定 / Target Temp"
    elif m_abs_cn:
        num = cn_to_number(m_abs_cn.group(1).strip())
        if num is not None and 14.0 <= num <= 34.0:
            temp = num
            temp_type = "绝对温度设定 / Target Temp"

    # 2. 相对温度判定 (EN + CN)
    if temp is None:
        if any(w in text_lower for w in ["warmer", "hotter", "heat up", "raise temp", "increase temp"]):
            m_d = re.search(r"by\s*([0-9\.]+)\s*(?:degrees|degree|°)?", text_lower)
            delta = float(m_d.group(1)) if m_d else 2.0
            temp_type = f"相对升温 (+{delta}℃) / Warmer"
        elif any(w in text_lower for w in ["cooler", "colder", "cool down", "lower temp", "decrease temp"]):
            m_d = re.search(r"by\s*([0-9\.]+)\s*(?:degrees|degree|°)?", text_lower)
            delta = -(float(m_d.group(1)) if m_d else 2.0)
            temp_type = f"相对降温 ({delta}℃) / Cooler"
        elif ("高" in text or "升" in text or "热" in text):
            m_rel = re.search(r"(?:升温|调高|升高|热一点|暖和点|加|升)?\s*([0-9一二两三四五六七八九十\.]+)\s*(?:度|°|℃)?", text)
            if m_rel and m_rel.group(1):
                d = cn_to_number(m_rel.group(1))
                if d and d <= 10:
                    delta = d
                    temp_type = f"相对升温 (+{delta}℃) / Warmer"
            else:
                delta = 1.0
                temp_type = f"相对升温 (+{delta}℃) / Warmer"
        elif ("低" in text or "降" in text or "冷" in text):
            m_low = re.search(r"(?:降温|调低|降低|冷一点|凉快点|减)?\s*([0-9一二两三四五六七八九十\.]+)\s*(?:度|°|℃)?", text)
            if m_low and m_low.group(1):
                d = cn_to_number(m_low.group(1))
                if d and d <= 10:
                    delta = -d
                    temp_type = f"相对降温 ({delta}℃) / Cooler"
            else:
                delta = -1.0
                temp_type = f"相对降温 ({delta}℃) / Cooler"

    mode = "自动 (AUTO)"
    if any(w in text_lower for w in ["制冷", "冷风", "冷气", "ac", "a/c", "cooling"]):
        mode = "制冷 / A/C"
    elif any(w in text_lower for w in ["制热", "暖风", "暖气", "heater", "heating"]):
        mode = "制热 / Heater"
    elif any(w in text_lower for w in ["除雾", "除霜", "defrost", "defog"]):
        mode = "除雾/除霜 / Defrost"
    elif any(w in text_lower for w in ["内循环", "recirculation"]):
        mode = "内循环 / Recirculation"
    elif any(w in text_lower for w in ["外循环", "fresh air"]):
        mode = "外循环 / Fresh Air"

    return {
        "target_temp": f"{temp} ℃" if temp is not None else ("微调" if delta is not None else "未指定 / Unspecified"),
        "temp_value": temp,
        "temp_type": temp_type,
        "delta": delta,
        "zone": zone,
        "mode": mode,
    }


def extract_nav_slots(text):
    text_lower = text.lower()
    has_nav_cue = any(w in text_lower for w in [
        "导航", "路线", "地图", "路况", "目的地", "带我", "回公司", "回家", "怎么走", "堵车", "去哪", "查路线",
        "加油站", "充电桩", "前往", "带我去", "送我到", "开车去", "开车到", "导到", "导去",
        "navigate", "navigation", "gps", "route", "destination", "take me to", "drive to", "directions to", "head to"
    ]) or bool(re.search(r"(?:^|[，,；;。！!？?\s])(?:我想|我要|帮我|请)?(?:去|到|回|前往)\s*[\u4e00-\u9fa5]{2,15}", text))

    if not has_nav_cue:
        return {
            "destination": "未指定 / Unspecified",
            "action": "未指定 / Unspecified",
            "preference": "未指定 / Unspecified",
        }

    if any(w in text_lower for w in ["退出导航", "关闭导航", "停掉导航", "取消导航", "不导了", "exit navigation", "cancel navigation", "stop navigation"]):
        action = "退出导航 / Exit Navigation"
    elif any(w in text_lower for w in ["查路线", "看路线", "check route", "show route", "directions to"]):
        action = "查询路线 / Check Route"
    elif any(w in text_lower for w in ["路况如何", "堵不堵", "堵车吗", "how is traffic", "check traffic", "traffic condition"]):
        action = "查询路况 / Check Traffic"
    elif any(w in text_lower for w in ["附近的", "周围的", "nearby", "find gas station", "find charging"]):
        action = "周边/沿途搜索 / Nearby Search"
    else:
        action = "设置目的地导航 / Set Destination"

    pref = "系统推荐 / Default"
    if "不走高速" in text or "avoid highway" in text_lower or "avoid highways" in text_lower or "no highway" in text_lower:
        pref = "不走高速 / Avoid Highways"
    elif "躲避拥堵" in text or "避开拥堵" in text or "avoid traffic" in text_lower or "avoiding traffic" in text_lower:
        pref = "躲避拥堵 / Avoid Congestion"
    elif "高速优先" in text or "prefer highway" in text_lower:
        pref = "高速优先 / Highway First"
    elif "距离最短" in text or "shortest" in text_lower:
        pref = "距离最短 / Shortest Route"
    elif "最快" in text or "fastest" in text_lower:
        pref = "时间最快 / Fastest Route"

    dest = None
    # English dest pattern
    m_en = re.search(r"(?:navigate to|take me to|drive to|directions to|route to|go to|head to)\s+([^,;!?]+)", text, re.I)
    if m_en:
        dest_raw = m_en.group(1).strip()
        dest_clean = re.sub(r"\b(avoiding traffic|avoid traffic|avoiding highways|avoid highways|fastest route|shortest route)\b", "", dest_raw, flags=re.I).strip()
        dest = dest_clean
    else:
        clauses = re.split(r"[,;!?，；！？]|\band\b|\bbut\b|\bthen\b|并且|但|但是|然后|同时", text)
        patterns = [
            r"(?:^|\s)(?:导航|带我|我想|送我|开车|开去|帮我导?到|请帮我导?到|导到|导去)?(?:去|到|至|向|前往)\s*([^，,；;。！!？?]+?)(?:怎么走|的路线|的路况|路线|路况|导航)?$",
            r"(?:^|\s)(?:查一下|查询|看看)?(?:去|到|前往)\s*([^，,；;。！!？?]+?)(?:的路线|的路况|怎么走)?$",
            r"(?:回|去)(公司|家|学校|办公室|机场|车站|酒店|医院|超市)",
        ]
        for c in clauses:
            c = c.strip()
            cleaned_c = re.sub(r"(?:躲避拥堵|不走高速|避开高速|避开拥堵|高速优先|距离最短|走最近的路|推荐路线)", "", c).strip()
            for p in patterns:
                m = re.search(p, cleaned_c)
                if m and m.group(1):
                    cand = m.group(1).strip()
                    cand = re.sub(r"^(?:一下|看下|帮我|查下|一个)?", "", cand).strip()
                    cand = re.sub(r"(?:怎么走|的路线|的路况|路线|路况)$", "", cand).strip()
                    if cand and cand not in ["哪", "哪里", "什么地方", "导航"]:
                        if re.search(r"^\d+(?:\.\d+)?度$|^[一二两三四五六七八九十百]+度$|^[0-9一二两三四五六七八九十]+%?$|^最大$|^最小$", cand):
                            continue
                        if any(w in cand for w in ["空调", "音乐", "车窗", "座椅", "天窗", "音量", "风量"]):
                            continue
                        dest = cand
                        break
            if dest:
                break

    if not dest:
        if "回家" in text or "go home" in text_lower:
            dest = "家 / Home"
        elif "回公司" in text or "go to office" in text_lower:
            dest = "公司 / Office"

    return {
        "destination": dest or "未指定 / Unspecified",
        "action": action,
        "preference": pref,
    }


def extract_phone_slots(text):
    m_num = re.search(r"([0-9]{3,12})", text)
    number = m_num.group(1) if m_num else None

    text_lower = text.lower()
    has_phone_cue = bool(number) or any(w in text_lower for w in [
        "电话", "呼叫", "拨号", "联系人", "打给", "接听", "挂断", "接电话", "拨打", "打电话", "拨通", "重拨", "回拨", "联系", "致电",
        "call", "dial", "phone", "contact", "hang up", "answer call", "pick up", "redial"
    ]) or bool(re.search(r"给.+打", text))
    if not has_phone_cue:
        return {
            "contact": "未指定 / Unspecified",
            "phone_number": "未指定 / Unspecified",
            "action": "未指定 / Unspecified",
        }

    if any(w in text_lower for w in ["挂断", "别接", "挂了", "挂掉", "不接", "hang up", "decline call", "end call"]):
        action = "挂断电话 / Hang Up"
    elif any(w in text_lower for w in ["接听", "接电话", "接通", "接一下", "answer call", "pick up"]):
        action = "接听电话 / Answer Call"
    elif any(w in text_lower for w in ["重拨", "回拨", "打回去", "redial", "call back"]):
        action = "重拨电话 / Redial"
    else:
        action = "拨打电话 / Make Call"

    contact = None
    if action == "拨打电话 / Make Call":
        clauses = re.split(r"[,;!?，；！？]|\band\b|\bbut\b|\bthen\b|并且|但是|然后|同时|顺便|而且|接着", text, flags=re.I)
        for c in clauses:
            c = c.strip()
            if not c:
                continue

            # 英文模式：call John / dial 911 / ring Alice
            m_en = re.search(r"^(?:please\s+)?(?:call|dial|ring)\s+(?:to\s+)?([A-Za-z0-9\s]+?)(?:,\s*please|\s+please)?$", c, re.I)
            if m_en:
                cand = m_en.group(1).strip()
                if cand.lower() not in ["someone", "anybody", "phone", "me", "a call"]:
                    contact = cand
                    break

            if not (number and number in c) and not any(kw in c for kw in ["电话", "呼叫", "拨", "打给", "联系", "联系人", "致电"]) and not re.search(r"给.+打", c):
                continue

            m_b = re.search(r"(?:给|致电)\s*([^，,；;。！!？?\s]+?)\s*(?:打[一一个俩几]?个?电话|打电话|致电|拨打电话|打过去|打一个|拨通|打个|打)?$", c)
            if m_b and m_b.group(1) and m_b.group(1) not in ["谁", "哪个", "电话"]:
                cand = m_b.group(1).strip()
                cand = re.sub(r"^(?:再|顺便|接着|然后|麻烦|请)?(?:帮我|给我|为我|我想|我要)?", "", cand).strip()
                if cand:
                    contact = cand
                    break

            m_a = re.search(r"(?:打电话给|打给|呼叫|拨打?电话?给|联系一下|联系|拨通|拨打)\s*([^，,；;。！!？?\s]+?)(?:的?电话)?$", c)
            if m_a and m_a.group(1) and m_a.group(1) not in ["谁", "哪个", "电话"]:
                cand = m_a.group(1).strip()
                cand = re.sub(r"^(?:再|顺便|接着|然后|麻烦|请)?(?:帮我|给我|为我|我想|我要)?", "", cand).strip()
                if cand:
                    contact = cand
                    break

    if number and (not contact or contact == number):
        contact = f"指定号码 ({number}) / Number ({number})"

    return {
        "contact": contact or "未指定 / Unspecified",
        "phone_number": number or "未指定 / Unspecified",
        "action": action,
    }


def extract_query_slots(text):
    text_lower = text.lower()
    has_query_cue = any(w in text_lower for w in [
        "天气", "气温", "下雨", "降雨", "温度如何", "几点", "时间", "星期", "礼拜", "日期",
        "限行", "尾号", "续航", "电量", "油量", "胎压", "笑话", "百科", "谁", "怎么样", "如何",
        "weather", "temperature outside", "forecast", "rain", "what time", "clock", "date",
        "battery", "range", "tire pressure", "joke", "who is", "what is", "how is", "how far", "tell me"
    ])
    if not has_query_cue:
        return {
            "query_type": "未指定 / Unspecified",
            "query_target": "未指定 / Unspecified",
            "channel": "未指定 / Unspecified",
        }

    q_type = "智能问答 / Q&A"
    target = "通用信息 / General Info"

    if any(w in text_lower for w in ["天气", "气温", "下雨", "降雨", "阴天", "晴天", "刮风", "冷不冷", "热不热", "下雪", "weather", "rain", "forecast", "sunny", "snow"]):
        q_type = "天气与环境查询 / Weather Query"
        target = "天气状况 / 天气趋势 (Weather & Forecast)"
    elif any(w in text_lower for w in ["几点", "时间", "星期", "礼拜", "日期", "哪一年", "几号", "what time", "clock", "today's date", "what day"]):
        q_type = "时间与日期查询 / Time Query"
        target = "当前标准时间 / 日历 (Current Time & Date)"
    elif any(w in text_lower for w in ["限行", "限号", "尾号", "license plate restriction"]):
        q_type = "交通限行查询 / Traffic Restriction"
        target = "机动车尾号限行规则 (Plate Restriction Rules)"
    elif any(w in text_lower for w in ["续航", "还能开", "多少公里", "电量", "油量", "胎压", "车门关了吗", "battery", "range", "tire pressure", "mileage"]):
        q_type = "车辆状态查询 / Vehicle Status"
        target = "三电 / 胎压 / 剩余续航 (Battery, Range & Status)"
    elif any(w in text_lower for w in ["笑话", "讲个故事", "你是谁", "聊天", "joke", "story", "who are you"]):
        q_type = "车载闲聊问答 / In-Car Chat"
        target = "语音助手交互 (Voice Assistant Interaction)"

    return {
        "query_type": q_type,
        "query_target": target,
        "channel": "TTS 语音助手播报 / Voice Assistant TTS",
    }


DOMAIN_KEYWORDS = {
    "seat": [
        "座椅加热", "座椅通风", "座椅按摩", "座椅", "加热", "通风", "屁股", "座",
        "seat heater", "seat heating", "heated seat", "heated seats", "seat ventilation",
        "ventilated seat", "ventilated seats", "seat massage", "seat", "seats"
    ],
    "climate": [
        "空调", "暖气", "暖风", "冷气", "冷风", "除雾", "除霜", "温度", "风量", "外循环", "内循环",
        "制热", "制冷", "太热", "太冷", "热一点", "冷一点", "有点冷", "有点热", "降温", "升温", "吹风",
        "ac", "a/c", "air condition", "air conditioning", "climate", "temperature", "temp",
        "heater", "heating", "cooler", "warmer", "cool down", "warm up", "fan speed", "fan",
        "defrost", "defogger", "defog", "air recirculation", "circulation"
    ],
    "window": [
        "车窗", "天窗", "后排窗", "主驾窗", "副驾窗", "窗户", "开窗", "关窗",
        "window", "windows", "sunroof", "moonroof", "driver window", "passenger window", "open window", "close window"
    ],
    "music": [
        "音乐", "歌", "歌曲", "曲子", "曲", "首", "收音机", "广播", "音频", "电台", "听", "放", "唱",
        "点播", "播放", "播", "来点", "周董", "周杰伦", "陈奕迅", "林俊杰", "邓紫棋", "五月天", "许巍",
        "古典", "爵士", "轻音乐", "纯音乐", "钢琴", "摇滚", "民谣", "古风", "电音", "老歌",
        "切歌", "下一首", "上一首", "别放了", "单曲循环", "随机播放", "放歌", "听歌", "放点音乐", "来点音乐",
        "music", "song", "songs", "track", "tune", "play", "listen", "radio", "fm", "am", "artist",
        "album", "playlist", "volume", "pause", "stop music", "next song", "previous song", "repeat", "shuffle",
        "classical", "jazz", "rock", "pop", "edm", "hip hop", "hiphop", "rap", "r&b", "soul", "folk", "acoustic", "lofi", "ambient"
    ],
    "navigation": [
        "导航", "路线", "地图", "路况", "目的地", "带我", "回公司", "回家", "怎么走", "堵车", "去哪", "查路线",
        "加油站", "充电桩", "前往", "带我去", "送我到", "开车去", "开车到", "导到", "导去",
        "navigate", "navigation", "gps", "route", "map", "traffic", "destination", "take me to",
        "drive to", "directions to", "directions", "go to", "head to", "find route", "gas station", "charging station"
    ],
    "phone": [
        "电话", "呼叫", "拨号", "联系人", "打给", "接听", "挂断", "接电话", "拨打", "打电话", "致电", "联系",
        "call", "dial", "phone", "contact", "hang up", "answer call", "pick up", "make a call", "ring"
    ],
    "query": [
        "天气", "气温", "下雨", "降雨", "温度如何", "几点", "时间", "星期", "礼拜", "日期",
        "限行", "尾号", "续航", "电量", "油量", "胎压", "笑话", "百科", "谁", "吗", "怎么样", "如何",
        "weather", "temperature outside", "rain", "rainy", "forecast", "what time", "clock", "date",
        "battery", "range", "tire pressure", "joke", "who is", "what is", "how is", "how far", "tell me"
    ],
}


def analyze_negation(text):
    clauses = re.split(r"[,;!?，；！？]|\band\b|\bbut\b|\bthen\b|\bwhile\b|\bas well as\b|\balso\b|并且|但是|然后|同时|顺便|而且|接着", text, flags=re.I)
    clauses = [c.strip() for c in clauses if c.strip()]

    exclusions = set()   # 排除性否定：明确要求“不要动 / 维持现状 / 别关 / 不要改变”，必须直接忽略剔除！
    turn_offs = set()    # 关闭性否定：明确要求“不要X / 关掉X / 停止X”，必须执行关闭操作！
    turn_ons = set()     # 开启/调节性指令

    domain_order = ["seat", "window", "climate", "music", "navigation", "phone", "query"]

    for c in clauses:
        c_lower = c.lower()
        # 1. 排除性否定模式
        m_ex_cn = (re.search(r"(?:不要|别|不用|切勿|请勿)(?:动|关|开|停|改|碰|调整)(.+)", c) or
                   re.search(r"(.+?)(?:不要|别|不用)(?:动|停|关|开|断|调整)", c))
        m_ex_en = (re.search(r"(?:don\'t|do not|never|leave|keep)\s+(?:touch|change|alter|modify|turn off|close)\s+(.+)", c_lower) or
                   re.search(r"(?:except|excluding|but not)\s+(.+)", c_lower))
        if m_ex_cn or m_ex_en:
            target_str = (m_ex_cn.group(1) if m_ex_cn else m_ex_en.group(1)).lower()
            for d in domain_order:
                if any(kw in target_str for kw in DOMAIN_KEYWORDS[d]):
                    exclusions.add(d)
                    break
            continue

        # 2. 关闭性否定
        m_off_cn = (re.search(r"^(?:不要|别|不用|关掉|关闭|停掉|停止|关了|退出|取消)(.+)$", c) or
                    re.search(r"(.+?)(?:关掉|关闭|停掉|停了|关了)$", c))
        m_off_en = re.search(r"^(?:turn off|switch off|shut down|disable|stop|cancel|exit|quit|pause)\s+(.+)$", c_lower)
        if m_off_cn or m_off_en:
            target_str = (m_off_cn.group(1) if m_off_cn else m_off_en.group(1)).lower()
            for d in domain_order:
                if any(kw in target_str for kw in DOMAIN_KEYWORDS[d]):
                    turn_offs.add(d)
                    break
            continue

        # 3. 普通正向指令
        for d in domain_order:
            if any(kw in c_lower for kw in DOMAIN_KEYWORDS[d]):
                turn_ons.add(d)

    return {
        "exclusions": list(exclusions),
        "turn_offs": list(turn_offs),
        "turn_ons": list(turn_ons),
    }


def build_smart_questions(text, intents):
    candidate_domains = set()
    text_lower = text.lower()
    for d, kws in DOMAIN_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            candidate_domains.add(d)

    if re.search(r"(?:^|[，,；;。！!？?\s])(?:我想|我要|帮我|请)?(?:去|到|回|前往)\s*[\u4e00-\u9fa5]{2,15}", text_lower):
        if not re.search(r"(?:调到|升到|降到|吹到|开到)\s*[0-9一二两三四五六七八九十]+度?", text_lower):
            candidate_domains.add("navigation")

    if re.search(r"\b(navigate to|take me to|drive to|directions to|route to|go to|head to)\b", text_lower):
        candidate_domains.add("navigation")

    if re.search(r"给.+打", text_lower) or re.search(r"\b(call|dial|ring)\s+[A-Za-z0-9]+", text_lower):
        candidate_domains.add("phone")

    if re.search(r"\b(play|listen to)\s+[A-Za-z0-9]+", text_lower):
        candidate_domains.add("music")

    noul_intents = [x for x in intents if x["in_noul"]]
    qs = {}
    is_en = is_english_query(text)

    if candidate_domains:
        active_noul = [x for x in noul_intents if x["name"] in candidate_domains]
        for x in active_noul:
            if is_en:
                desc = DOMAIN_INSTRUCTIONS_EN.get(x["name"], x["desc"])
                qs[x["name"]] = {"type": "noul", "instructions": f"Does this command request {desc}?"}
            else:
                desc = DOMAIN_INSTRUCTIONS_CN.get(x["name"], x["desc"])
                qs[x["name"]] = {"type": "noul", "instructions": f"这条指令是否要求处理{desc}？"}
        use_choice = False
    else:
        if is_en:
            choice = {x["name"]: DOMAIN_INSTRUCTIONS_EN.get(x["name"], x["desc"]) for x in intents if x["in_choice"]}
            qs["intent"] = {"type": "choice",
                            "instructions": "Determine which vehicle feature this voice command belongs to",
                            "criteria": choice}
        else:
            choice = {x["name"]: DOMAIN_INSTRUCTIONS_CN.get(x["name"], x["desc"]) for x in intents if x["in_choice"]}
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
        valid_candidates = [(k, v) for k, v in domains.items() if k not in negation["exclusions"]]
        if valid_candidates and max(v for k, v in valid_candidates) >= 0.50:
            main_choice = max(valid_candidates, key=lambda x: x[1])[0]
        else:
            main_choice = "other"

        total_p = sum(domains.values()) or 1.0
        probabilities = {x["name"]: round(domains.get(x["name"], 0.0) / total_p, 3) for x in intents if x["in_choice"]}
        if "other" in probabilities:
            probabilities["other"] = round(max(0.0, 1.0 - sum(v for k, v in probabilities.items() if k != "other")), 3)

    if main_choice in negation["exclusions"]:
        valid = [k for k, v in domains.items() if k not in negation["exclusions"] and v >= 0.50]
        if valid:
            main_choice = max(valid, key=lambda k: domains[k])

    music_slots = extract_music_slots(text, ans)
    climate_slots = extract_climate_slots(text)
    nav_slots = extract_nav_slots(text)
    phone_slots = extract_phone_slots(text)
    query_slots = extract_query_slots(text)

    domain_actions = {}
    for d_name in domains:
        if d_name in negation["exclusions"]:
            domain_actions[d_name] = {"action": "exclude", "label": "维持现状/排除 (Excluded/Ignore)"}
        elif d_name in negation["turn_offs"]:
            domain_actions[d_name] = {"action": "turn_off", "label": "关闭/停止 (Turn Off)"}
        elif d_name in negation["turn_ons"]:
            domain_actions[d_name] = {"action": "turn_on", "label": "开启/调节 (Turn On)"}
        else:
            domain_actions[d_name] = {"action": "auto", "label": "常规控制 (Control)"}

    return {
        "intent": {"choice": main_choice,
                   "probabilities": probabilities},
        "domains": domains,
        "music_slots": music_slots,
        "climate_slots": climate_slots,
        "nav_slots": nav_slots,
        "phone_slots": phone_slots,
        "query_slots": query_slots,
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
<title>车机语音意图测试台 · Bilingual Edition</title>
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
main { max-width: 1240px; margin: 0 auto; padding: 26px 24px 60px; }

.header-row {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 2px;
}
h1 { font-size: 21px; margin: 0 0 2px; }
.sub { color: var(--muted); font-size: 13px; margin: 0 0 14px; }
.lang-btn {
  font: inherit; font-size: 13px; font-weight: 500; color: var(--ink);
  background: var(--surface); border: 1px solid var(--baseline);
  border-radius: 999px; padding: 6px 14px; cursor: pointer; white-space: nowrap;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04); transition: all 0.15s ease;
}
.lang-btn:hover { border-color: var(--fill); background: var(--track-dim); color: var(--fill); }

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

/* 左右双栏布局 (Workspace Grid) */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 16px;
  align-items: start;
}
@media (max-width: 960px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
.col-left, .col-right {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.col-right .slot-card {
  margin-top: 0;
}
.empty-slot-hint {
  text-align: center;
  padding: 42px 20px;
  background: var(--surface);
  border: 1px dashed var(--baseline);
  border-radius: 10px;
}
.empty-slot-hint .hint-icon {
  font-size: 32px;
  margin-bottom: 8px;
}
.empty-slot-hint .hint-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}
.empty-slot-hint .hint-desc {
  font-size: 13px;
  color: var(--muted);
}

.panel h2 { font-size: 14.5px; margin: 0 0 12px; color: var(--ink); }
.panel h2 small { font-weight: 400; color: var(--muted); margin-left: 6px; }
.brow {
  display: grid; grid-template-columns: 96px 1fr 58px 50px;
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

/* ── 槽位面板 ── */
.slot-card { border-left: 4px solid var(--fill); background: var(--surface); }
.slot-card h2 { font-size: 15px; margin: 0 0 12px; display: flex; align-items: baseline; gap: 8px; color: var(--ink); }
.slot-card h2 small { font-size: 11.5px; color: var(--muted); font-weight: normal; }
.slot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }
.slot-box {
  background: var(--page); border: 1px solid var(--grid); border-radius: 8px;
  padding: 8px 11px;
}
.slot-lbl { font-size: 11.5px; color: var(--muted); font-weight: 500; margin-bottom: 3px; }
.slot-val { font-size: 14px; font-weight: 600; color: var(--ink); word-break: break-all; }
.slot-details { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.slot-tag {
  font-size: 11.5px; background: var(--track-dim); color: var(--fill);
  padding: 3px 8px; border-radius: 4px; font-weight: 500;
}
.climate-theme { border-left-color: #009688 !important; }
.climate-theme .slot-tag { background: rgba(0, 150, 136, 0.12); color: #00796b; }
.nav-theme { border-left-color: #ff9800 !important; }
.nav-theme .slot-tag { background: rgba(255, 152, 0, 0.12); color: #e65100; }
.phone-theme { border-left-color: #4caf50 !important; }
.phone-theme .slot-tag { background: rgba(76, 175, 80, 0.12); color: #2e7d32; }
.query-theme { border-left-color: #9c27b0 !important; }
.query-theme .slot-tag { background: rgba(156, 39, 176, 0.12); color: #6a1b9a; }

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
  <div class="header-row">
    <div>
      <h1 id="pageTitle">车机语音意图测试台</h1>
      <p class="sub" id="pageSub">decision:eos · 单意图路由（choice）+ 多标签检出（noul）+ 21种全曲风音乐/空调/导航/电话/查询槽位抽取 · 本地 ollaya 127.0.0.1:11435</p>
    </div>
    <button class="lang-btn" id="langBtn" type="button">🌐 Switch to English</button>
  </div>

  <div class="domains-row">
    <span class="cap" id="dCap">支持的功能域（<span id="dcount">–</span>）：</span><span id="dchips"></span>
  </div>

  <form id="f">
    <input id="q" placeholder="输入一句话，如：空调调至二十四度，或者打开空调并播放周杰伦的歌" autofocus>
    <button class="go" id="go" type="submit">判断</button>
  </form>
  <div class="examples" id="ex"></div>

  <div id="status"></div>

  <section id="result" hidden>
    <div class="tiles">
      <div class="tile"><div class="label" id="lblWall">端到端耗时 / Latency</div><div class="value"><span id="tWall">–</span><span class="unit">ms</span></div></div>
      <div class="tile"><div class="label" id="lblModel">模型耗时 / Model Time</div><div class="value"><span id="tModel">–</span><span class="unit">ms</span></div></div>
      <div class="tile"><div class="label" id="lblTok">输入 tokens / Tokens</div><div class="value"><span id="tTok">–</span></div></div>
    </div>
    <div class="workspace-grid">
      <!-- 左栏：意图分类与概率分布 -->
      <div class="col-left">
        <section class="card panel">
          <div class="verdict"><span class="tag" id="verdict">–</span><span class="echo" id="echo"></span></div>
          <h2 id="noulTitle">多标签检出 / Multi-Label<small>noul · YES ≥ 0.70 · 灰区 0.50–0.70</small></h2>
          <div id="noulBars"></div>
        </section>
        <section class="card panel">
          <h2 id="choiceTitle">主意图分布 / Top Intent<small>choice · 全类别概率分布</small></h2>
          <div id="choiceBars"></div>
        </section>
      </div>

      <!-- 右栏：结构化槽位与分流结果 -->
      <div class="col-right">
        <!-- 纯控制或无特定槽位提示 -->
        <div class="card empty-slot-hint" id="emptySlotHint" hidden>
          <div class="hint-icon">⚡</div>
          <div class="hint-title" id="emptyTitle">常规功能控制</div>
          <div class="hint-desc" id="emptyDesc">当前指令已直接分发至车控总线，无需提取额外槽位参数。</div>
        </div>

        <!-- 音乐槽位分析面板（21种全曲风 + 双语解析） -->
        <section class="card slot-card" id="musicCard" hidden>
          <h2>🎵 车机音乐槽位抽取 / Music Slots<small>21种全曲风覆盖 · 歌手与歌名解析 · 零生成等待</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl">🎤 歌手偏好 / Artist</div>
              <div class="slot-val" id="slotArtist">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🎵 听哪首歌 / Song</div>
              <div class="slot-val" id="slotSong">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🎨 曲风·情绪 / Genre & Mood</div>
              <div class="slot-val" id="slotMood">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">⏯️ 控制动作 / Action</div>
              <div class="slot-val" id="slotAction">–</div>
            </div>
          </div>
          <div class="slot-details" id="slotDetails"></div>
        </section>

        <!-- 空调槽位分析面板（双语温度/模式/温区抽取） -->
        <section class="card slot-card climate-theme" id="climateCard" hidden>
          <h2>❄️ 车机空调槽位抽取 / Climate Slots<small>温度与模式精准解析 · 毫秒级单次前向</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl">🌡️ 设定目标温度 / Target Temp</div>
              <div class="slot-val" id="slotTemp">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🎚️ 调节方式 / Temp Adjustment</div>
              <div class="slot-val" id="slotTempType">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">💺 控制温区 / Target Zone</div>
              <div class="slot-val" id="slotZone">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">💨 工作模式 / Climate Mode</div>
              <div class="slot-val" id="slotClimateMode">–</div>
            </div>
          </div>
          <div class="slot-details" id="climateDetails"></div>
        </section>

        <!-- 导航槽位分析面板 -->
        <section class="card slot-card nav-theme" id="navCard" hidden>
          <h2>🧭 车机导航槽位抽取 / Navigation Slots<small>目的地与路径偏好解析 · 毫秒级单次前向</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl">📍 导航目的地 / Destination</div>
              <div class="slot-val" id="slotNavDest">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🚦 导航动作 / Action</div>
              <div class="slot-val" id="slotNavAction">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🛣️ 路线偏好 / Preference</div>
              <div class="slot-val" id="slotNavPref">–</div>
            </div>
          </div>
          <div class="slot-details" id="navDetails"></div>
        </section>

        <!-- 电话槽位分析面板 -->
        <section class="card slot-card phone-theme" id="phoneCard" hidden>
          <h2>📞 车机电话槽位抽取 / Phone Slots<small>联系人与号码识别 · 毫秒级单次前向</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl">👤 呼叫联系人 / Contact</div>
              <div class="slot-val" id="slotPhoneContact">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🔢 目标电话号码 / Phone Number</div>
              <div class="slot-val" id="slotPhoneNumber">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">📲 呼叫动作 / Phone Action</div>
              <div class="slot-val" id="slotPhoneAction">–</div>
            </div>
          </div>
          <div class="slot-details" id="phoneDetails"></div>
        </section>

        <!-- 信息查询分流面板 -->
        <section class="card slot-card query-theme" id="queryCard" hidden>
          <h2>💬 信息查询与问答分流 / Query & Assistant<small>天气/时间/车况智能分流 · 语音助手联动</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl">📋 查询类型 / Query Type</div>
              <div class="slot-val" id="slotQueryType">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">🎯 查询目标 / Query Target</div>
              <div class="slot-val" id="slotQueryTarget">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl">📢 响应通道 / Response Channel</div>
              <div class="slot-val" id="slotQueryChannel">–</div>
            </div>
          </div>
          <div class="slot-details" id="queryDetails"></div>
        </section>
      </div>
    </div>
  </section>

  <section class="card mgmt" id="mgmt">
    <h2 id="mgmtTitle">功能域管理 / Domain Config</h2>
    <p class="sub2" id="mgmtSub">添加或编辑后立即对下一次判断生效（写入 config.json）。● 表示参与多标签检出；<span class="lock">other</span> 为兜底类不可删除。</p>
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
let CURRENT_LANG = 'zh';

const I18N = {
  zh: {
    title: '车机语音意图测试台',
    sub: 'decision:eos · 单意图路由（choice）+ 多标签检出（noul）+ 21种全曲风音乐/空调/导航/电话/查询槽位抽取 · 本地 ollaya 127.0.0.1:11435',
    langBtn: '🌐 Switch to English',
    placeholder: '输入一句话，如：空调调至二十四度，或者打开空调并播放周杰伦的歌',
    go: '判断',
    exLabel: '示例：',
    examples: [
      '空调调至二十四度',
      '关闭空调，但是不要关座椅加热',
      '把车窗打开，把音乐打开，空调调到二十度',
      '导航去上海虹桥火车站，躲避拥堵',
      '给张三打电话',
      '我心情很差，想听一首古典音乐',
      '今天天气怎么样'
    ],
    emptyTitle: '常规功能控制',
    emptyDesc: '当前指令已直接分发至车控总线，无需提取额外槽位参数。',
    judging: '判断中…',
  },
  en: {
    title: 'In-Cabin Voice Intent & Slot Workbench',
    sub: 'decision:eos · Single Intent (choice) + Multi-Label (noul) + 21 Music Genres / Climate / Nav / Phone / Query Slots · Local ollaya 127.0.0.1:11435',
    langBtn: '🌐 切换为中文',
    placeholder: 'Enter a command, e.g.: call John, play some jazz music, and set temperature to 22 degrees',
    go: 'Analyze',
    exLabel: 'Examples: ',
    examples: [
      'set temperature to 22 degrees',
      'turn off the AC, but do not touch heated seats',
      'call John, play some jazz music, and set temperature to 22 degrees',
      'navigate to SFO Airport avoiding traffic',
      'play Shape of You by Ed Sheeran',
      'play Adele\'s Hello',
      'what is the weather today'
    ],
    emptyTitle: 'Standard Device Control',
    emptyDesc: 'Command dispatched directly to vehicle CAN bus without extra slot parameters.',
    judging: 'Analyzing…',
  }
};

function setLanguage(lang) {
  CURRENT_LANG = lang;
  const t = I18N[lang];
  $('pageTitle').textContent = t.title;
  $('pageSub').textContent = t.sub;
  $('langBtn').textContent = t.langBtn;
  $('q').placeholder = t.placeholder;
  $('go').textContent = t.go;
  $('emptyTitle').textContent = t.emptyTitle;
  $('emptyDesc').textContent = t.emptyDesc;

  $('ex').innerHTML = t.exLabel + t.examples.map(ex => `<button>${esc(ex)}</button>`).join('');
}

$('langBtn').addEventListener('click', () => {
  setLanguage(CURRENT_LANG === 'zh' ? 'en' : 'zh');
});

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

/* ── 判断与渲染 ── */
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
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

  const hit = domains.filter(x => x.v >= 0.70 && !exclusions.includes(x.k)).map(x => x.k);
  const excludedHits = domains.filter(x => exclusions.includes(x.k)).map(x => x.k);
  const gray = domains.filter(x => x.v >= 0.50 && x.v < 0.70 && !exclusions.includes(x.k)).map(x => x.k);

  const vd = $('verdict');
  let verdictHtml = '';
  const hasQueryCue = /天气|气温|下雨|几点|时间|星期|日期|限行|讲个笑话|weather|rain|time|battery|joke/.test(text.toLowerCase());

  if (hit.length >= 2) {
    const labels = hit.map(h => {
      const act = domainActions[h] ? domainActions[h].action : '';
      return h + (act === 'turn_off' ? (CURRENT_LANG === 'en' ? ' (off)' : ' (关闭)') : (act === 'turn_on' ? (CURRENT_LANG === 'en' ? ' (on)' : ' (开启)') : ''));
    });
    verdictHtml = `<span class="tag">${CURRENT_LANG === 'en' ? 'Multi-Intent' : '多指令'} · ${esc(labels.join(' + '))}</span>`;
  } else if (hit.length === 1) {
    const act = domainActions[hit[0]] ? domainActions[hit[0]].action : '';
    const actLabel = act === 'turn_off' ? (CURRENT_LANG === 'en' ? ' (off)' : ' (关闭)') : (act === 'turn_on' ? (CURRENT_LANG === 'en' ? ' (on)' : ' (开启)') : '');
    verdictHtml = `<span class="tag">${CURRENT_LANG === 'en' ? 'Single Intent' : '单指令'} · ${esc(hit[0] + actLabel)}</span>`;
  } else if (d.intent && d.intent.choice === 'query') {
    verdictHtml = `<span class="tag" style="background:#e8f0fe;color:#1967d2;">💬 ${CURRENT_LANG === 'en' ? 'Voice Query · Info/Weather TTS Dispatch' : '语音查询 · 天气/状态信息播报 (分流至语音助手)'}</span>`;
  } else if (d.intent && d.intent.choice !== 'other') {
    verdictHtml = `<span class="tag">${CURRENT_LANG === 'en' ? 'Single Intent' : '单意图'} · ${esc(d.intent.choice)}</span>`;
  } else {
    verdictHtml = `<span class="tag">${CURRENT_LANG === 'en' ? 'Uncertain / Fallback' : '未检出'}${gray.length ? ' (' + gray.join(', ') + ')' : ''}</span>`;
  }

  if (hit.length >= 1 && (hasQueryCue || d.intent.choice === 'query')) {
    verdictHtml += `<span class="ex-tag" style="background:#e8f0fe;color:#1967d2;font-weight:600;">💬 + ${CURRENT_LANG === 'en' ? 'TTS Info Broadcast (Dual-Track)' : '天气/信息播报 (双轨分流)'}</span>`;
  }

  if (excludedHits.length) {
    verdictHtml += `<span class="ex-tag">⏸️ ${CURRENT_LANG === 'en' ? 'Excluded: ' : '已忽略排除项：'}${esc(excludedHits.join(', '))}</span>`;
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
      if (r.isEx) return CURRENT_LANG === 'en' ? 'Excluded' : '已排除 (忽略)';
      if (r.isOff && r.v >= 0.70) return CURRENT_LANG === 'en' ? 'YES (OFF)' : 'YES (关闭)';
      if (r.v >= 0.70) return CURRENT_LANG === 'en' ? 'YES (ON)' : 'YES (开启)';
      if (r.v >= 0.50) return CURRENT_LANG === 'en' ? 'Gray Zone' : '灰区';
      return '—';
    }
  ) : '<p class="note">当前没有参与多标签检出的功能域</p>';

  const probs = Object.entries(d.intent.probabilities).map(([k, v]) => ({k, v})).sort((a, b) => b.v - a.v);
  $('choiceBars').innerHTML = bars(
    probs.map(x => ({label: x.k, v: x.v, top: x.k === d.intent.choice})), null);

  // 渲染车机音乐槽位抽取卡片
  if (d.music_slots && (d.intent.choice === 'music' || (d.domains && d.domains.music >= 0.30) || d.music_slots.artist !== '未指定' || d.music_slots.artist !== '未指定 / Unspecified' || d.music_slots.song !== '未指定 / Unspecified' || d.music_slots.mood !== '未限定 / Any Mood')) {
    $('slotArtist').textContent = d.music_slots.artist;
    $('slotSong').textContent = d.music_slots.song;
    $('slotMood').textContent = d.music_slots.mood;
    $('slotAction').textContent = d.music_slots.action;
    $('slotDetails').innerHTML = `
      <span class="slot-tag">点播模式：${esc(d.music_slots.target_type)}</span>
      <span class="slot-tag">动作语义：${esc(d.music_slots.action)}</span>
      <span class="slot-tag">21 种全曲风 · 毫秒级零生成等待</span>
    `;
    $('musicCard').hidden = false;
  } else {
    $('musicCard').hidden = true;
  }

  // 渲染车机空调槽位抽取卡片
  if (d.climate_slots && !exclusions.includes('climate') && (d.intent.choice === 'climate' || (d.domains && d.domains.climate >= 0.35) || d.climate_slots.target_temp !== '未指定 / Unspecified' || d.climate_slots.temp_type !== '未指定 / Unspecified')) {
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

  // 渲染车机导航槽位抽取卡片
  if (d.nav_slots && !exclusions.includes('navigation') && (d.intent.choice === 'navigation' || (d.domains && d.domains.navigation >= 0.35) || d.nav_slots.destination !== '未指定 / Unspecified')) {
    $('slotNavDest').textContent = d.nav_slots.destination;
    $('slotNavAction').textContent = d.nav_slots.action;
    $('slotNavPref').textContent = d.nav_slots.preference;
    $('navDetails').innerHTML = `
      <span class="slot-tag">目标地点：${esc(d.nav_slots.destination)}</span>
      <span class="slot-tag">规划偏好：${esc(d.nav_slots.preference)}</span>
      <span class="slot-tag">动作语义：${esc(d.nav_slots.action)}</span>
      <span class="slot-tag">JEV 并行单次前向 · 零生成等待</span>
    `;
    $('navCard').hidden = false;
  } else {
    $('navCard').hidden = true;
  }

  // 渲染车机电话槽位抽取卡片
  if (d.phone_slots && !exclusions.includes('phone') && (d.intent.choice === 'phone' || (d.domains && d.domains.phone >= 0.35) || d.phone_slots.contact !== '未指定 / Unspecified' || d.phone_slots.phone_number !== '未指定 / Unspecified')) {
    $('slotPhoneContact').textContent = d.phone_slots.contact;
    $('slotPhoneNumber').textContent = d.phone_slots.phone_number;
    $('slotPhoneAction').textContent = d.phone_slots.action;
    $('phoneDetails').innerHTML = `
      <span class="slot-tag">呼叫对象：${esc(d.phone_slots.contact)}</span>
      <span class="slot-tag">拨号号码：${esc(d.phone_slots.phone_number)}</span>
      <span class="slot-tag">电话动作：${esc(d.phone_slots.action)}</span>
      <span class="slot-tag">JEV 并行单次前向 · 零生成等待</span>
    `;
    $('phoneCard').hidden = false;
  } else {
    $('phoneCard').hidden = true;
  }

  // 渲染信息查询与问答分流卡片
  if (d.query_slots && (d.intent.choice === 'query' || (d.domains && d.domains.query >= 0.35) || hasQueryCue)) {
    $('slotQueryType').textContent = d.query_slots.query_type;
    $('slotQueryTarget').textContent = d.query_slots.query_target;
    $('slotQueryChannel').textContent = d.query_slots.channel;
    $('queryDetails').innerHTML = `
      <span class="slot-tag">问答类别：${esc(d.query_slots.query_type)}</span>
      <span class="slot-tag">查询目标：${esc(d.query_slots.query_target)}</span>
      <span class="slot-tag">响应方式：TTS 语音助手播报</span>
    `;
    $('queryCard').hidden = false;
  } else {
    $('queryCard').hidden = true;
  }

  const anySlotCard = !$('musicCard').hidden || !$('climateCard').hidden || !$('navCard').hidden || !$('phoneCard').hidden || !$('queryCard').hidden;
  $('emptySlotHint').hidden = anySlotCard;

  $('result').hidden = false;
}
async function judge(text) {
  const st = $('status'), go = $('go');
  st.className = ''; st.textContent = I18N[CURRENT_LANG].judging; go.disabled = true;
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

setLanguage('zh');
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
