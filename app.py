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

ALL_GENRES_ORDERED = []
for code, (lbl, kws) in GENRE_MAP.items():
    for kw in kws:
        ALL_GENRES_ORDERED.append((kw, lbl))
ALL_GENRES_ORDERED.sort(key=lambda x: len(x[0]), reverse=True)

ALL_MOODS_ORDERED = []
for code, (lbl, kws) in MOOD_MAP.items():
    for kw in kws:
        ALL_MOODS_ORDERED.append((kw, lbl))
ALL_MOODS_ORDERED.sort(key=lambda x: len(x[0]), reverse=True)

CARRIER_TOKENS = [
    "我们", "咱们", "大家", "他们", "你们", "车里人", "车上人", "全车人", "车里", "车上",
    "我", "你", "他", "她", "它",
    "想要", "想", "要", "打算", "准备", "喜欢", "爱听", "希望能", "希望", "需要", "烦请", "麻烦", "请", "可以", "能",
    "帮我们", "帮咱们", "帮我", "给我们", "给咱们", "给我", "替我们", "替我", "为我们", "为我",
    "还", "又", "也", "就", "再", "顺便", "接着", "然后", "先", "现在", "立刻", "马上",
    "播放", "点播", "播送", "放", "听", "播", "唱", "来", "搜", "查", "换", "切", "听听", "放放", "播播",
    "一首", "两首", "几首", "首", "曲", "支", "首歌曲", "首歌", "首曲子", "点", "下", "个", "一些", "一点", "些",
    "的", "音乐", "歌", "歌曲", "曲子", "风格", "曲风", "类型", "旋律", "调子",
    "吧", "啊", "呀", "啦", "呢", "嘛", "一下", "一会", "会儿",
    "play", "listen to", "listen", "hear", "song", "songs", "music", "track", "tracks",
    "some", "a", "an", "the", "to", "piece of", "piece", "please", "can you", "can", "you", "we", "want to", "want",
    "i", "would like", "would", "like", "let's", "lets", "give us", "give me", "put on"
]
CARRIER_TOKENS.sort(key=len, reverse=True)


def match_pure_genre_or_mood(clause):
    c = clause.strip().lower()
    found_genre = None
    found_mood = None

    rem = c
    for kw, lbl in ALL_GENRES_ORDERED:
        if kw.lower() in rem:
            found_genre = lbl
            rem = rem.replace(kw.lower(), "", 1)
            break

    for kw, lbl in ALL_MOODS_ORDERED:
        if kw.lower() in rem:
            found_mood = lbl
            rem = rem.replace(kw.lower(), "", 1)
            break

    if not found_genre and not found_mood:
        return False, None, None

    for tok in CARRIER_TOKENS:
        rem = rem.replace(tok.lower(), "")

    rem = re.sub(r"[\s,;.!?:;，。！？；：、~`\'\"/\\\(\)\[\]\{\}]+", "", rem).strip()
    if len(rem) == 0:
        return True, found_genre, found_mood
    return False, None, None


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

    # 5. 纯曲风/情绪优先判定（如 '我想听放克'、'我们要听放克'、'放点爵士'、'来首古典音乐'、'play funk'）
    pure_ok, pure_genre, pure_mood = match_pure_genre_or_mood(music_clause)
    if pure_ok:
        tag_desc = []
        if pure_genre:
            tag_desc.append(pure_genre)
        elif detected_genre:
            tag_desc.append(detected_genre)

        if pure_mood:
            tag_desc.append(pure_mood)
        elif detected_mood and (not pure_genre or detected_mood != pure_genre):
            tag_desc.append(detected_mood)

        desc_str = " + ".join(tag_desc) if tag_desc else "风格"
        return {
            "action": action,
            "mood": mood_display,
            "artist": "未指定 / Unspecified",
            "song": f"未指定（按 {desc_str} 智能推荐） / Recommendation",
            "target_type": "风格/情绪智能推荐 / Genre & Mood Mix",
            "raw": {"action": action, "mood": mood_display, "target": "genre_mood_all"},
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

    # 中文语法规则解析（单次前向匹配，支持单复数主语与礼貌前缀，避免贪婪吞噬）
    if not artist and not song:
        pattern = r"^(?:(?:我(?:们)?|咱们|大家|他们|你们|车[里内上]|全车人|你|他(?:们)?|她(?:们)?)?\s*(?:还|又|也|就|再|顺便|接着|然后|先|麻烦|请)?\s*(?:想要|想|要|打算|希望能?|准备|喜欢|爱听)?\s*(?:帮我(?:们)?|给我(?:们)?|替我(?:们)?|为我(?:们)?|来)?\s*(?:播放|点播|放|听|播|唱|搜|查|切|换)?\s*(?:一?[首曲支]|两首|几首|首歌曲|首歌|首曲子|点|下|个|一些|一点)?\s*)"
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
                left = re.sub(pattern, "", left).strip()
                if left in ADJECTIVE_MOODS or right in GENRE_TERMS or right in ["歌", "音乐", "歌曲", "曲子"]:
                    artist = "未指定 / Unspecified"
                    song = f"未指定（按 {left} 智能推荐） / Recommendation"
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
                cand = re.sub(r"^(?:再|顺便|接着|然后|先|麻烦|请)?\s*(?:帮我(?:们)?|给我(?:们)?|为我(?:们)?|替我(?:们)?|我(?:们)?|咱们|大家|他们|你们|想要|想|要|打算)?\s*", "", cand).strip()
                if cand:
                    contact = cand
                    break

            m_a = re.search(r"(?:打电话给|打给|呼叫|拨打?电话?给|联系一下|联系|拨通|拨打)\s*([^，,；;。！!？?\s]+?)(?:的?电话)?$", c)
            if m_a and m_a.group(1) and m_a.group(1) not in ["谁", "哪个", "电话"]:
                cand = m_a.group(1).strip()
                cand = re.sub(r"^(?:再|顺便|接着|然后|先|麻烦|请)?\s*(?:帮我(?:们)?|给我(?:们)?|为我(?:们)?|替我(?:们)?|我(?:们)?|咱们|大家|他们|你们|想要|想|要|打算)?\s*", "", cand).strip()
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
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>N/E · NEURA EDIT | In-Cabin Voice Intelligence Playground</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=VT323&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root {
  --font-display: 'VT323', ui-monospace, 'JetBrains Mono', monospace;
  --font-body: 'Source Serif 4', 'Source Serif Pro', 'Iowan Old Style', Georgia, "PingFang SC", serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'Consolas', monospace;

  --bg: #fafaf5;
  --bg-surface: #f3f1e8;
  --bg-surface-hover: #ece9dc;
  --ink: #1a1a1a;
  --ink-soft: #4a4a4a;
  --ink-mute: #7a7a78;
  --rule: #1a1a1a;
  --rule-soft: rgba(26, 26, 26, 0.16);
  --paper-rule: rgba(26, 26, 26, 0.08);

  --blueprint: #3553ff;
  --blueprint-tint: rgba(53, 83, 255, 0.08);
  --blueprint-tint-strong: rgba(53, 83, 255, 0.18);
  --blueprint-hover: #233fc9;

  --status-complete: #3553ff;
  --status-in-progress: #4a4a4a;
  --warn: #b8870f;
  --danger: #cf3030;
  --success: #198754;

  --shadow-hard: 3px 3px 0 var(--ink);
  --shadow-hard-lg: 5px 5px 0 var(--ink);
  --shadow-blueprint: 3px 3px 0 var(--blueprint);
}

[data-theme="dark"] {
  --bg: #0a0d1a;
  --bg-surface: #131830;
  --bg-surface-hover: #1b2244;
  --ink: #e8e6dc;
  --ink-soft: #a8a6a0;
  --ink-mute: #7a7878;
  --rule: #e8e6dc;
  --rule-soft: rgba(232, 230, 220, 0.18);
  --paper-rule: rgba(232, 230, 220, 0.08);

  --blueprint: #6b8eff;
  --blueprint-tint: rgba(107, 142, 255, 0.12);
  --blueprint-tint-strong: rgba(107, 142, 255, 0.22);
  --blueprint-hover: #8aa5ff;

  --status-complete: #6b8eff;
  --status-in-progress: #c8c6c0;
  --warn: #d4a83d;
  --danger: #ff5252;
  --success: #20c997;

  --shadow-hard: 3px 3px 0 #000;
  --shadow-hard-lg: 5px 5px 0 #000;
  --shadow-blueprint: 3px 3px 0 var(--blueprint);
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0; padding: 0;
}

html {
  scroll-behavior: smooth;
  scroll-padding-top: 80px;
}

body {
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.62;
  color: var(--ink);
  background-color: var(--bg);
  background-image: radial-gradient(var(--paper-rule) 1px, transparent 1px);
  background-size: 16px 16px;
  background-attachment: fixed;
  -webkit-font-smoothing: antialiased;
  transition: background-color 0.2s, color 0.2s;
}

/* ── Technical Nav Bar ── */
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--bg);
  border-bottom: 1px solid var(--rule-soft);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.nav-inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.brand-group {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: var(--ink);
}
.brand-logo-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-titles {
  display: flex;
  flex-direction: column;
}
.brand-name {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--blueprint);
  line-height: 1.15;
}
.brand-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-mute);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-btn {
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: var(--bg);
  color: var(--ink);
  border: 1px solid var(--rule-soft);
  padding: 6px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.nav-btn:hover {
  border-color: var(--blueprint);
  color: var(--blueprint);
  background: var(--blueprint-tint);
}
.nav-btn.primary {
  background: var(--blueprint);
  color: #fff;
  border-color: var(--blueprint);
  font-weight: 600;
}
.nav-btn.primary:hover {
  background: var(--blueprint-hover);
  color: #fff;
}

/* ── Hero / Masthead Section ── */
.manual-masthead {
  border-bottom: 1px solid var(--rule-soft);
  padding: 48px 0 36px;
  background: linear-gradient(180deg, var(--bg-surface) 0%, var(--bg) 100%);
}
.container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 24px;
}

.masthead-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 420px);
  gap: 40px;
  align-items: center;
}
@media (max-width: 960px) {
  .masthead-grid {
    grid-template-columns: 1fr;
    gap: 30px;
  }
}

.manual-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-mute);
}
.manual-meta-row .highlight {
  color: var(--blueprint);
  font-weight: 600;
}

.manual-title {
  display: block;
  font-family: var(--font-display);
  font-size: clamp(2.8rem, 6vw, 5.2rem);
  line-height: 0.92;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--blueprint);
  margin-bottom: 18px;
}

.manual-tagline {
  font-family: var(--font-body);
  font-size: clamp(1.02rem, 1.4vw, 1.18rem);
  line-height: 1.6;
  color: var(--ink);
  margin-bottom: 14px;
}

.manual-attribution {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  color: var(--ink-mute);
  margin-bottom: 24px;
}
.manual-attribution b {
  color: var(--ink);
}

.specs-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 28px;
}
.spec-chip {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  padding: 4px 10px;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  color: var(--ink-soft);
}
.spec-chip b {
  color: var(--blueprint);
}

.masthead-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.cta-btn {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 12px 24px;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: var(--bg);
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--shadow-hard);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.cta-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: var(--shadow-hard-lg);
  background: var(--blueprint);
  border-color: var(--blueprint);
  color: #fff;
}
.cta-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 var(--ink);
}
.cta-btn.secondary {
  background: var(--bg);
  color: var(--ink);
  border: 1px solid var(--rule-soft);
  box-shadow: none;
}
.cta-btn.secondary:hover {
  border-color: var(--blueprint);
  color: var(--blueprint);
  background: var(--blueprint-tint);
  transform: none;
}

/* Masthead Figure Plate */
.fig-plate {
  border: 1px solid var(--rule-soft);
  background: var(--bg-surface);
  box-shadow: var(--shadow-hard);
  overflow: hidden;
}
.fig-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  border-bottom: 1px solid var(--rule-soft);
  background: var(--bg);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  color: var(--ink-mute);
}
.fig-tag {
  font-weight: 700;
  color: var(--blueprint);
}
.fig-terminal {
  padding: 18px 16px;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  line-height: 1.7;
}
.t-dim { color: var(--ink-mute); }
.t-blue { color: var(--blueprint); font-weight: 600; }
.term-divider {
  color: var(--rule-soft);
  margin: 10px 0;
  user-select: none;
}
.term-pipeline {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  margin-top: 14px;
  text-align: center;
}
.p-step {
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  padding: 6px 4px;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  color: var(--ink-soft);
}
.p-step.active {
  border-color: var(--blueprint);
  color: var(--blueprint);
  background: var(--blueprint-tint);
  font-weight: 700;
}

/* ── Interactive Console Main Section ── */
main.container {
  padding-top: 40px;
  padding-bottom: 70px;
}

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--rule-soft);
  padding-bottom: 12px;
  margin-bottom: 24px;
}
.console-title {
  font-family: var(--font-display);
  font-size: 2.2rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink);
  line-height: 1;
}
.console-meta {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  color: var(--ink-mute);
}

/* Command Query Input Form */
.query-box {
  background: var(--bg-surface);
  border: 1px solid var(--rule-soft);
  padding: 20px;
  box-shadow: var(--shadow-hard);
  margin-bottom: 20px;
}
form.cmd-form {
  display: flex;
  gap: 12px;
}
.cmd-prompt {
  display: flex;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 700;
  color: var(--blueprint);
  user-select: none;
}
#q {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  padding: 12px 16px;
  color: var(--ink);
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  outline: none;
  transition: border-color 0.15s ease;
}
#q:focus {
  border-color: var(--blueprint);
  box-shadow: 0 0 0 1px var(--blueprint);
}
button.go {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #fff;
  background: var(--blueprint);
  border: 1px solid var(--blueprint);
  padding: 12px 28px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}
button.go:hover {
  background: var(--blueprint-hover);
  border-color: var(--blueprint-hover);
}
button.go:disabled {
  opacity: 0.55;
  cursor: wait;
}

.examples-wrap {
  margin-top: 14px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 0.78rem;
}
.ex-label {
  color: var(--ink-mute);
  margin-right: 4px;
}
.examples-wrap button {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  color: var(--ink-soft);
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.12s ease;
}
.examples-wrap button:hover {
  border-color: var(--blueprint);
  color: var(--blueprint);
  background: var(--blueprint-tint);
}

.domains-wrap {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed var(--rule-soft);
  font-family: var(--font-mono);
  font-size: 0.76rem;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.domains-wrap .cap {
  color: var(--ink-mute);
}
.dchip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  padding: 2px 8px;
  color: var(--ink-soft);
}
.dchip b {
  color: var(--ink);
}
.dchip .noul-dot {
  color: var(--blueprint);
}

#status {
  margin: 14px 0;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--ink-mute);
  min-height: 20px;
}
#status.err {
  color: var(--danger);
  font-weight: 600;
}

/* Telemetry Stat Tiles */
.tiles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin: 20px 0;
}
@media (max-width: 680px) {
  .tiles {
    grid-template-columns: 1fr;
  }
}
.tile {
  background: var(--bg-surface);
  border: 1px solid var(--rule-soft);
  padding: 14px 18px;
  box-shadow: 2px 2px 0 var(--ink);
}
.tile .label {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-mute);
  margin-bottom: 4px;
}
.tile .value {
  font-family: var(--font-mono);
  font-size: 1.9rem;
  font-weight: 700;
  color: var(--blueprint);
  line-height: 1;
}
.tile .unit {
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--ink-soft);
  margin-left: 4px;
}

/* Verdict Banner */
.verdict-banner {
  background: var(--bg-surface);
  border: 1px solid var(--rule-soft);
  border-left: 4px solid var(--blueprint);
  padding: 12px 18px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.verdict-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.verdict-tag {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 4px 12px;
  background: var(--blueprint);
  color: #fff;
}
.verdict-tag.query {
  background: #6a1b9a;
}
.verdict-tag.uncertain {
  background: var(--ink-mute);
}
.echo-query {
  font-family: var(--font-body);
  font-style: italic;
  font-size: 0.95rem;
  color: var(--ink-soft);
}
.ex-tag {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  padding: 3px 8px;
  background: var(--blueprint-tint);
  border: 1px solid var(--blueprint);
  color: var(--blueprint);
}

/* Two-column Workspace Layout */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 20px;
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
  gap: 18px;
}

/* Technical Panels & Cards */
.panel {
  background: var(--bg-surface);
  border: 1px solid var(--rule-soft);
  padding: 18px 20px;
  box-shadow: var(--shadow-hard);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--rule-soft);
  padding-bottom: 8px;
  margin-bottom: 14px;
}
.panel h2 {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink);
  margin: 0;
}
.panel h2 small {
  font-weight: 400;
  color: var(--ink-mute);
  font-size: 0.72rem;
  margin-left: 8px;
  text-transform: none;
}

/* Probability Bars */
.brow {
  display: grid;
  grid-template-columns: 110px 1fr 58px 64px;
  gap: 0 10px;
  align-items: center;
  margin: 8px 0;
  font-family: var(--font-mono);
}
.brow .bl {
  font-size: 0.78rem;
  color: var(--ink-soft);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.brow.top .bl {
  color: var(--ink);
  font-weight: 700;
}
.brow .track {
  position: relative;
  height: 14px;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
}
.brow .fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  min-width: 2px;
  background: var(--blueprint);
}
.brow.dim .fill {
  background: var(--ink-mute);
}
.brow .bv {
  font-size: 0.76rem;
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}
.brow.top .bv {
  color: var(--blueprint);
  font-weight: 700;
}
.chip {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  white-space: nowrap;
}
.chip.yes { color: var(--success); }
.chip.yes::before { content: "● "; }
.chip.turn_off { color: var(--danger); }
.chip.turn_off::before { content: "● "; }
.chip.exclude { color: var(--ink-mute); text-decoration: line-through; }
.chip.exclude::before { content: "⊘ "; text-decoration: none; }
.chip.gray { color: var(--warn); }
.chip.gray::before { content: "◐ "; }
.chip.no { color: var(--ink-mute); }

/* Slot Breakdown Cards */
.slot-card {
  background: var(--bg-surface);
  border: 1px solid var(--rule-soft);
  border-left: 4px solid var(--blueprint);
  padding: 18px 20px;
  box-shadow: var(--shadow-hard);
}
.slot-card.climate-theme { border-left-color: #009688; }
.slot-card.nav-theme { border-left-color: #f57c00; }
.slot-card.phone-theme { border-left-color: #2e7d32; }
.slot-card.query-theme { border-left-color: #7b1fa2; }

.slot-card h2 {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink);
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--rule-soft);
  padding-bottom: 8px;
}
.slot-card h2 small {
  font-size: 0.72rem;
  color: var(--ink-mute);
  font-weight: 400;
  text-transform: none;
}

.slot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
}
.slot-box {
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  padding: 10px 12px;
}
.slot-lbl {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-mute);
  margin-bottom: 4px;
}
.slot-val {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--ink);
  word-break: break-all;
}
.slot-details {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.slot-tag {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  color: var(--ink-soft);
  padding: 3px 8px;
}

.empty-slot-hint {
  text-align: center;
  padding: 40px 20px;
  background: var(--bg-surface);
  border: 1px dashed var(--rule-soft);
  box-shadow: none;
}
.empty-slot-hint .hint-icon {
  font-size: 28px;
  margin-bottom: 8px;
  color: var(--blueprint);
}
.empty-slot-hint .hint-title {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 4px;
}
.empty-slot-hint .hint-desc {
  font-size: 0.85rem;
  color: var(--ink-mute);
}

/* Domain Management Section */
.mgmt {
  margin-top: 40px;
  background: var(--bg-surface);
  border: 1px solid var(--rule-soft);
  padding: 22px 24px;
  box-shadow: var(--shadow-hard);
}
.mgmt h2 {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.mgmt .sub2 {
  font-size: 0.82rem;
  color: var(--ink-mute);
  margin-bottom: 16px;
}
table.cfg {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
}
table.cfg th {
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-mute);
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--rule);
}
table.cfg td {
  font-size: 0.82rem;
  padding: 9px 10px;
  border-bottom: 1px solid var(--rule-soft);
  vertical-align: middle;
}
table.cfg td.name {
  font-weight: 700;
  color: var(--blueprint);
}
table.cfg td.desc {
  font-family: var(--font-body);
  color: var(--ink-soft);
}
table.cfg td.ck {
  color: var(--success);
  font-weight: 700;
}
table.cfg td.ck.off {
  color: var(--ink-mute);
  font-weight: 400;
}
table.cfg .op {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  padding: 3px 8px;
  cursor: pointer;
  color: var(--ink);
  margin-right: 4px;
}
table.cfg .op:hover {
  border-color: var(--blueprint);
  color: var(--blueprint);
}
table.cfg .op.del:hover {
  border-color: var(--danger);
  color: var(--danger);
}
table.cfg .op[disabled] {
  opacity: 0.35;
  cursor: not-allowed;
}

.iform {
  display: grid;
  grid-template-columns: 160px 1fr auto auto auto;
  gap: 10px;
  margin-top: 18px;
  align-items: center;
}
@media (max-width: 780px) {
  .iform {
    grid-template-columns: 1fr;
  }
}
.iform input[type=text] {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  padding: 8px 12px;
  color: var(--ink);
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  outline: none;
}
.iform input[type=text]:focus {
  border-color: var(--blueprint);
}
.iform label {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.iform .save {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #fff;
  background: var(--blueprint);
  border: 1px solid var(--blueprint);
  padding: 8px 18px;
  cursor: pointer;
}
.iform .cancel {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background: var(--bg);
  border: 1px solid var(--rule-soft);
  padding: 8px 14px;
  cursor: pointer;
}
#mgmtStatus {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--ink-mute);
  margin-top: 10px;
  min-height: 16px;
}
#mgmtStatus.err { color: var(--danger); }

/* Technical Footer */
.footer {
  border-top: 1px solid var(--rule-soft);
  background: var(--bg);
  padding: 24px 0;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--ink-mute);
}
.footer-inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.footer-right {
  display: flex;
  gap: 16px;
}
.footer-link {
  color: var(--ink-mute);
  text-decoration: none;
}
.footer-link:hover {
  color: var(--blueprint);
}

[hidden] { display: none !important; }
</style>
</head>
<body>

<!-- Navigation Bar -->
<header class="navbar">
  <div class="nav-inner">
    <a href="#" class="brand-group">
      <div class="brand-logo-wrap">
        <svg class="brand-logo" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="1.5" y="1.5" width="29" height="29" stroke="currentColor" stroke-width="1.2" fill="var(--bg)"/>
          <line x1="1.5" y1="5.5" x2="5.5" y2="1.5" stroke="var(--blueprint)" stroke-width="1.2"/>
          <line x1="30.5" y1="26.5" x2="26.5" y2="30.5" stroke="var(--blueprint)" stroke-width="1.2"/>
          <text x="16" y="21" font-family="'JetBrains Mono', monospace" font-size="11" font-weight="800" fill="var(--blueprint)" text-anchor="middle" letter-spacing="-0.5">N/E</text>
        </svg>
      </div>
      <div class="brand-titles">
        <span class="brand-name">NEURA EDIT</span>
        <span class="brand-sub">COCKPIT VOICE LAB</span>
      </div>
    </a>
    <div class="nav-actions">
      <button class="nav-btn" id="themeBtn" type="button" title="Toggle Light/Dark Theme">◐ <span id="themeLabel">THEME</span></button>
      <button class="nav-btn primary" id="langBtn" type="button">🌐 <span id="langLabel">ENGLISH</span></button>
    </div>
  </div>
</header>

<!-- Hero / Masthead Section -->
<section class="manual-masthead">
  <div class="container">
    <div class="manual-meta-row">
      <span>[ORG: <b class="highlight">N/E // NEURA EDIT</b>] · AUTOMOTIVE VOICE AI</span>
      <span>SPEC: <b class="highlight">2026.09-REV</b> · DUAL-TRACK NLU</span>
    </div>
    <div class="masthead-grid">
      <div class="masthead-left">
        <h1 class="manual-title" id="heroTitle">IN-CABIN VOICE INTELLIGENCE</h1>
        <p class="manual-tagline" id="heroTagline">
          欢迎体验 NEURA EDIT (N/E) 车载全双工多意图识别与槽位提取试验台。专为车载智能座舱设计，以确定性、超低延迟（~140ms）实现涵盖 21 种音乐曲风、空调多温区调节、导航路径规划、电话呼叫及车况问答的联合路由与精准槽位抽取，原生具备 CAN 车控总线否定词排除能力与零生成等待。
        </p>
        <div class="manual-attribution" id="heroAttr">
          Architected & Engineered by <b>N/E · NEURA EDIT</b>
        </div>
        <div class="specs-strip">
          <span class="spec-chip">⚡ <b>~140ms</b> LATENCY</span>
          <span class="spec-chip">🎯 <b>DUAL-TRACK</b> MULTI-INTENT</span>
          <span class="spec-chip">🎵 <b>21 GENRES</b> ZERO-WAIT</span>
          <span class="spec-chip">🛡️ <b>CAN BUS</b> NEGATION SHIELD</span>
        </div>
        <div class="masthead-cta">
          <a href="#console" class="cta-btn" id="heroCtaGo">⚡ 进入控制台</a>
          <button type="button" class="cta-btn secondary" id="heroCtaDemo">📋 运行多指令示例</button>
          <a href="#mgmt" class="cta-btn secondary" id="heroCtaCfg">⚙️ 功能域配置</a>
        </div>
      </div>
      <div class="masthead-figure">
        <div class="fig-plate">
          <div class="fig-header">
            <span class="fig-tag">FIG. 001</span>
            <span class="fig-status">● LIVE PIPELINE ARCHITECTURE</span>
          </div>
          <div class="fig-terminal">
            <div><span class="t-dim">[SYS_BOOT]</span> <span class="t-blue">NEURA-EDIT COCKPIT AGENT</span></div>
            <div><span class="t-dim">[MODEL]</span> DECISION:EOS (127.0.0.1:11435)</div>
            <div><span class="t-dim">[EXECUTION]</span> SINGLE FORWARD PASS (JEV)</div>
            <div><span class="t-dim">[NEGATION]</span> DUAL EXCLUSION OVERRIDE</div>
            <div class="term-divider">----------------------------------------</div>
            <div class="term-pipeline">
              <div class="p-step">AUDIO IN</div>
              <div class="p-step active">DECISION</div>
              <div class="p-step active">SLOTS</div>
              <div class="p-step">CAN BUS</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Interactive Console -->
<main class="container" id="console">
  <div class="console-header">
    <div class="console-title" id="consoleTitle">VOICE COMMAND CONSOLE</div>
    <div class="console-meta" id="consoleMeta">[STATUS: READY] // PORT 8080</div>
  </div>

  <div class="query-box">
    <form class="cmd-form" id="f">
      <div class="cmd-prompt">&gt;</div>
      <input id="q" placeholder="输入一句话，如：空调调至二十四度，或者打开空调并播放周杰伦的歌" autofocus autocomplete="off" spellcheck="false">
      <button class="go" id="go" type="submit">判定</button>
    </form>
    <div class="examples-wrap" id="ex"></div>
    <div class="domains-wrap">
      <span class="cap" id="dCap">支持的功能域（<span id="dcount">–</span>）：</span>
      <span id="dchips"></span>
    </div>
  </div>

  <div id="status"></div>

  <section id="result" hidden>
    <div class="tiles">
      <div class="tile">
        <div class="label" id="lblWall">端到端耗时</div>
        <div class="value"><span id="tWall">–</span><span class="unit">ms</span></div>
      </div>
      <div class="tile">
        <div class="label" id="lblModel">模型计算耗时</div>
        <div class="value"><span id="tModel">–</span><span class="unit">ms</span></div>
      </div>
      <div class="tile" title="模型单次前向评估的总输入 Tokens">
        <div class="label" id="lblTok">输入 Tokens</div>
        <div class="value"><span id="tTok">–</span><span class="unit" id="tokNote" style="font-size:11px;color:var(--ink-mute);font-weight:normal;margin-left:4px;">(含指令模板)</span></div>
      </div>
    </div>

    <div class="verdict-banner">
      <div class="verdict-tags" id="verdict"></div>
      <div class="echo-query" id="echo"></div>
    </div>

    <div class="workspace-grid">
      <!-- Left Column: Intent Distribution & Multi-Label -->
      <div class="col-left">
        <section class="panel">
          <div class="panel-header">
            <h2 id="noulTitle">多标签检出<small id="noulSub">noul · YES ≥ 0.70 · 灰区 0.50–0.70</small></h2>
          </div>
          <div id="noulBars"></div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <h2 id="choiceTitle">主意图概率分布<small id="choiceSub">choice · 全类别归一化概率</small></h2>
          </div>
          <div id="choiceBars"></div>
        </section>
      </div>

      <!-- Right Column: Extracted Slots Cards -->
      <div class="col-right">
        <!-- Direct CAN Bus Execution Hint -->
        <div class="panel empty-slot-hint" id="emptySlotHint" hidden>
          <div class="hint-icon">⚡</div>
          <div class="hint-title" id="emptyTitle">车控总线直接执行</div>
          <div class="hint-desc" id="emptyDesc">当前指令已直接分发至车控 CAN 总线，无需额外提取槽位参数。</div>
        </div>

        <!-- Music Slots Card -->
        <section class="slot-card" id="musicCard" hidden>
          <h2><span id="cardTitleMusic">车机音乐槽位抽取</span><small id="cardSubMusic">21 种全曲风覆盖 · 零生成等待</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotArtist">歌手偏好</div>
              <div class="slot-val" id="slotArtist">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotSong">点播目标</div>
              <div class="slot-val" id="slotSong">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotMood">曲风 · 情绪</div>
              <div class="slot-val" id="slotMood">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotAction">控制动作</div>
              <div class="slot-val" id="slotAction">–</div>
            </div>
          </div>
          <div class="slot-details" id="slotDetails"></div>
        </section>

        <!-- Climate Slots Card -->
        <section class="slot-card climate-theme" id="climateCard" hidden>
          <h2><span id="cardTitleClimate">车机空调槽位抽取</span><small id="cardSubClimate">多温区与工作模式解析 · 零生成等待</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotTemp">设定目标温度</div>
              <div class="slot-val" id="slotTemp">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotTempType">调节方式</div>
              <div class="slot-val" id="slotTempType">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotZone">控制温区</div>
              <div class="slot-val" id="slotZone">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotClimateMode">工作模式</div>
              <div class="slot-val" id="slotClimateMode">–</div>
            </div>
          </div>
          <div class="slot-details" id="climateDetails"></div>
        </section>

        <!-- Navigation Slots Card -->
        <section class="slot-card nav-theme" id="navCard" hidden>
          <h2><span id="cardTitleNav">车机导航槽位抽取</span><small id="cardSubNav">目的地与路径偏好解析 · 零生成等待</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotNavDest">目的地</div>
              <div class="slot-val" id="slotNavDest">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotNavAction">导航动作</div>
              <div class="slot-val" id="slotNavAction">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotNavPref">路线偏好</div>
              <div class="slot-val" id="slotNavPref">–</div>
            </div>
          </div>
          <div class="slot-details" id="navDetails"></div>
        </section>

        <!-- Phone Slots Card -->
        <section class="slot-card phone-theme" id="phoneCard" hidden>
          <h2><span id="cardTitlePhone">车机电话槽位抽取</span><small id="cardSubPhone">联系人与号码识别 · 零生成等待</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotPhoneContact">呼叫联系人</div>
              <div class="slot-val" id="slotPhoneContact">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotPhoneNumber">目标电话号码</div>
              <div class="slot-val" id="slotPhoneNumber">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotPhoneAction">通话动作</div>
              <div class="slot-val" id="slotPhoneAction">–</div>
            </div>
          </div>
          <div class="slot-details" id="phoneDetails"></div>
        </section>

        <!-- Query & Assistant Dispatch Card -->
        <section class="slot-card query-theme" id="queryCard" hidden>
          <h2><span id="cardTitleQuery">信息查询与问答分流</span><small id="cardSubQuery">天气/时间/车况语音助手联动</small></h2>
          <div class="slot-grid">
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotQueryType">查询类型</div>
              <div class="slot-val" id="slotQueryType">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotQueryTarget">查询目标</div>
              <div class="slot-val" id="slotQueryTarget">–</div>
            </div>
            <div class="slot-box">
              <div class="slot-lbl" id="lblSlotQueryChannel">响应通道</div>
              <div class="slot-val" id="slotQueryChannel">–</div>
            </div>
          </div>
          <div class="slot-details" id="queryDetails"></div>
        </section>
      </div>
    </div>
  </section>

  <!-- Domain Management Section -->
  <section class="mgmt" id="mgmt">
    <h2 id="mgmtTitle">功能域管理与配置中心</h2>
    <p class="sub2" id="mgmtSub">添加或编辑后立即对下一次判断生效（写入 config.json）。● 表示参与多标签检出；other 为兜底类不可删除。</p>
    <table class="cfg">
      <thead><tr><th id="thName">域名</th><th id="thDesc">类别描述</th><th id="thChoice">主意图</th><th id="thNoul">多标签</th><th id="thOps" style="width:140px">操作</th></tr></thead>
      <tbody id="cfgBody"></tbody>
    </table>
    <div class="iform" id="iform">
      <input type="text" id="iName" placeholder="域名 如 defroster" spellcheck="false">
      <input type="text" id="iDesc" placeholder="描述，如：除雾、除霜相关控制">
      <label><input type="checkbox" id="iChoice" checked> <span id="lblChoice">主意图</span></label>
      <label><input type="checkbox" id="iNoul" checked> <span id="lblNoul">多标签</span></label>
      <button class="save" id="iSave" type="button">添加</button>
      <button class="cancel" id="iCancel" type="button" hidden>取消</button>
    </div>
    <div id="mgmtStatus"></div>
  </section>
</main>

<footer class="footer">
  <div class="footer-inner">
    <div>
      <b>NEURA EDIT (N/E)</b> · In-Cabin Voice Intelligence Playground
    </div>
    <div class="footer-right">
      <span class="footer-link">ENGINEERED FROM FIRST PRINCIPLES</span>
      <span class="footer-link">127.0.0.1:11435</span>
    </div>
  </div>
</footer>

<script>
const $ = id => document.getElementById(id);
let INTENTS = [];
let CURRENT_LANG = localStorage.getItem('ne_lang') || 'zh';
let CURRENT_THEME = localStorage.getItem('ne_theme') || 'light';

document.documentElement.setAttribute('data-theme', CURRENT_THEME);

const I18N = {
  zh: {
    heroTitle: '车机语音智能试验台',
    heroTagline: '欢迎体验由 NEURA EDIT (N/E) 打造的车载全双工多意图识别与槽位提取试验台。专为车载智能座舱设计，以确定性、超低延迟（~140ms）实现涵盖 21 种音乐曲风、空调多温区调节、导航路径规划、电话呼叫及车况问答的联合路由与精准槽位抽取，原生具备 CAN 车控总线否定词排除能力与零生成等待。',
    heroAttr: '系统设计与工程构建：<b>N/E · NEURA EDIT</b>',
    heroCtaGo: '⚡ 进入控制台',
    heroCtaDemo: '📋 运行多指令示例',
    heroCtaCfg: '⚙️ 功能域配置',
    consoleTitle: '车机语音指令控制台',
    consoleMeta: '[状态: 正常连接] // 本地端口 8080',
    placeholder: '输入车机语音指令，如：空调调至二十四度，或者打开空调并播放周杰伦的歌',
    go: '开始判定',
    exLabel: '推荐示例：',
    examples: [
      '空调调至二十四度',
      '关闭空调，但是不要关座椅加热',
      '把车窗打开，把音乐打开，空调调到二十度',
      '我们要听放克',
      '我想给张三打电话，我还想听一首林俊杰的伟大的渺小，再帮我导航去公司',
      '导航去上海虹桥火车站，躲避拥堵',
      '今天天气怎么样'
    ],
    dCap: '支持的功能域（',
    lblWall: '端到端耗时',
    lblModel: '模型计算耗时',
    lblTok: '输入 Tokens',
    tokNote: '(含指令模板)',
    emptyTitle: '车控总线直接执行',
    emptyDesc: '当前指令已直接分发至车控 CAN 总线，无需额外提取槽位参数。',
    judging: '正在通过 decision:eos 神经计算判定中…',
    noulTitle: '多标签检出',
    noulSub: 'noul · YES ≥ 0.70 · 灰区 0.50–0.70',
    choiceTitle: '主意图概率分布',
    choiceSub: 'choice · 全类别归一化概率',
    cardTitleMusic: '车机音乐槽位抽取',
    cardSubMusic: '21 种全曲风覆盖 · 歌手与歌名解析 · 零生成等待',
    lblSlotArtist: '歌手偏好',
    lblSlotSong: '点播目标',
    lblSlotMood: '曲风与情绪',
    lblSlotAction: '控制动作',
    cardTitleClimate: '车机空调槽位抽取',
    cardSubClimate: '多温区与工作模式解析 · 零生成等待',
    lblSlotTemp: '设定目标温度',
    lblSlotTempType: '调节方式',
    lblSlotZone: '控制温区',
    lblSlotClimateMode: '工作模式',
    cardTitleNav: '车机导航槽位抽取',
    cardSubNav: '目的地与路线偏好解析 · 零生成等待',
    lblSlotNavDest: '导航目的地',
    lblSlotNavAction: '导航动作',
    lblSlotNavPref: '路线规划偏好',
    cardTitlePhone: '车机电话槽位抽取',
    cardSubPhone: '联系人与号码识别 · 零生成等待',
    lblSlotPhoneContact: '呼叫联系人',
    lblSlotPhoneNumber: '目标电话号码',
    lblSlotPhoneAction: '通话动作',
    cardTitleQuery: '信息查询与问答分流',
    cardSubQuery: '天气/时间/车况语音助手联动',
    lblSlotQueryType: '查询类型',
    lblSlotQueryTarget: '查询目标',
    lblSlotQueryChannel: '响应通道',
    mgmtTitle: '功能域管理与配置中心',
    mgmtSub: '添加或编辑后立即对下一次判断生效（写入 config.json）。● 表示参与多标签检出；other 为兜底类不可删除。',
    thName: '域名',
    thDesc: '类别描述',
    thChoice: '主意图',
    thNoul: '多标签',
    thOps: '操作',
    iNamePlaceholder: '域名 如 defroster',
    iDescPlaceholder: '描述，如：除雾、除霜相关控制',
    lblChoice: '主意图',
    lblNoul: '多标签',
    iSaveAdd: '添加',
    iSaveEdit: '保存修改',
    iCancel: '取消',
    btnEdit: '编辑',
    btnDel: '删除',
    delConfirm: '确认删除功能域「{name}」？',
    langLabel: 'ENGLISH',
    themeLabel: CURRENT_THEME === 'dark' ? '浅色' : '深色'
  },
  en: {
    heroTitle: 'IN-CABIN VOICE INTELLIGENCE',
    heroTagline: 'Welcome to the NEURA EDIT (N/E) In-Cabin Voice Intelligence Playground. Built from first principles for modern connected vehicles, this system demonstrates deterministic, ultra-low latency (~140ms) joint intent routing and multi-slot extraction across 21 musical genres, climate regulation, waypoint navigation, telephony, and vehicle status queries—all with zero generation latency and CAN-bus negation detection.',
    heroAttr: 'Architected & Engineered by <b>N/E · NEURA EDIT</b>',
    heroCtaGo: '⚡ Launch Playground',
    heroCtaDemo: '📋 Run Multi-Command Demo',
    heroCtaCfg: '⚙️ Domain Config',
    consoleTitle: 'VOICE COMMAND CONSOLE',
    consoleMeta: '[STATUS: ONLINE] // LOCALHOST:8080',
    placeholder: 'Enter in-cabin voice query, e.g.: call John, play some jazz music, and set temperature to 22 degrees',
    go: 'Analyze',
    exLabel: 'Preset Queries: ',
    examples: [
      'set temperature to 22 degrees',
      'turn off the AC, but do not touch heated seats',
      'call John, play some jazz music, and set temperature to 22 degrees',
      'we want to listen to jazz',
      'navigate to SFO Airport avoiding traffic',
      'play Shape of You by Ed Sheeran',
      'what is the weather today'
    ],
    dCap: 'Active Domains (',
    lblWall: 'End-to-End Latency',
    lblModel: 'Model Compute Time',
    lblTok: 'Input Tokens',
    tokNote: '(incl. prompt template)',
    emptyTitle: 'Direct Vehicle Bus Control',
    emptyDesc: 'Command dispatched directly to vehicle CAN bus without additional slot extraction.',
    judging: 'Evaluating forward pass with decision:eos…',
    noulTitle: 'Multi-Label Detection',
    noulSub: 'noul · YES ≥ 0.70 · Gray Zone 0.50–0.70',
    choiceTitle: 'Top Intent Distribution',
    choiceSub: 'choice · Normalized Category Probabilities',
    cardTitleMusic: 'Music Slot Extraction',
    cardSubMusic: '21 Acoustic Genres Covered · Artist & Song Parsing · Zero Delay',
    lblSlotArtist: 'Artist Preference',
    lblSlotSong: 'Target Song / Track',
    lblSlotMood: 'Genre & Mood',
    lblSlotAction: 'Playback Action',
    cardTitleClimate: 'Climate Control Slots',
    cardSubClimate: 'Multi-Zone & Climate Mode Parsing · Zero Generation Delay',
    lblSlotTemp: 'Target Temperature',
    lblSlotTempType: 'Adjustment Mode',
    lblSlotZone: 'Target Cabin Zone',
    lblSlotClimateMode: 'Operating Mode',
    cardTitleNav: 'Navigation Slots',
    cardSubNav: 'Destination & Route Preference Parsing · Zero Delay',
    lblSlotNavDest: 'Destination',
    lblSlotNavAction: 'Navigation Action',
    lblSlotNavPref: 'Routing Preference',
    cardTitlePhone: 'Telephony Slots',
    cardSubPhone: 'Contact & Phone Number Detection · Zero Delay',
    lblSlotPhoneContact: 'Call Recipient',
    lblSlotPhoneNumber: 'Phone Number',
    lblSlotPhoneAction: 'Telephony Action',
    cardTitleQuery: 'Query & Assistant Dispatch',
    cardSubQuery: 'Weather / Time / Vehicle Status Assistant Linkage',
    lblSlotQueryType: 'Query Category',
    lblSlotQueryTarget: 'Query Target',
    lblSlotQueryChannel: 'Response Channel',
    mgmtTitle: 'Domain Registry & Configuration',
    mgmtSub: 'Active domains in decision:eos. Saved immediately to config.json. ● indicates participation in multi-label detection.',
    thName: 'Domain',
    thDesc: 'Description',
    thChoice: 'Choice',
    thNoul: 'Multi-Label',
    thOps: 'Actions',
    iNamePlaceholder: 'Domain (e.g. defroster)',
    iDescPlaceholder: 'Description, e.g.: window defroster & defogger',
    lblChoice: 'Choice',
    lblNoul: 'Multi-Label',
    iSaveAdd: 'Add Domain',
    iSaveEdit: 'Save Changes',
    iCancel: 'Cancel',
    btnEdit: 'Edit',
    btnDel: 'Delete',
    delConfirm: 'Delete domain "{name}"?',
    langLabel: '中文',
    themeLabel: CURRENT_THEME === 'dark' ? 'LIGHT' : 'DARK'
  }
};

const DOMAIN_I18N = {
  climate: { zh: '空调控制（含温度、风量、制冷制热）', en: 'Climate control (temp, fan speed, A/C & heater)' },
  music: { zh: '音乐控制（含播放、暂停、切歌、音量与曲风）', en: 'Music playback (play, pause, track, volume & genres)' },
  navigation: { zh: '导航操作（含设目的地、路线、路况）', en: 'Navigation (destination, routing & traffic)' },
  seat: { zh: '座椅控制（含座椅加热、通风）', en: 'Seat comfort (seat heating & ventilation)' },
  window: { zh: '车窗控制（含车窗、天窗）', en: 'Window & sunroof control' },
  phone: { zh: '电话操作（含拨打电话、呼叫联系人）', en: 'Phone calls (dial, contacts & redial)' },
  query: { zh: '时间、日期、天气等信息查询或问答', en: 'Information & assistant queries (weather, time, vehicle)' },
  other: { zh: '以上都不属于（兜底类）', en: 'Out-of-domain / Fallback category' }
};

function localizeSlotValue(val, lang) {
  if (!val || val === '–' || val === '-') return '–';
  val = String(val).trim();

  const DICT = {
    '播放 / Play': { zh: '播放', en: 'Play' },
    '暂停 / Pause': { zh: '暂停', en: 'Pause' },
    '切到下一首 / Next Track': { zh: '切到下一首', en: 'Next Track' },
    '上一首 / Previous Track': { zh: '上一首', en: 'Previous Track' },
    '单曲循环 / Repeat Track': { zh: '单曲循环', en: 'Repeat Track' },
    '随机播放 / Shuffle': { zh: '随机播放', en: 'Shuffle' },
    '未指定 / Unspecified': { zh: '未指定', en: 'Unspecified' },
    '未限定 / Any Mood': { zh: '未限定', en: 'Any Mood' },
    '指定特定单曲 / Specific Song': { zh: '指定特定单曲', en: 'Specific Song' },
    '歌手热门精选 / Popular Songs': { zh: '歌手热门精选', en: 'Popular Songs' },
    '风格/情绪智能推荐 / Genre & Mood Mix': { zh: '风格/情绪智能推荐', en: 'Genre & Mood Mix' },
    '随机点播 / Shuffle': { zh: '随机点播', en: 'Shuffle' },
    '未指定（继续播放/随心听） / Continue Playback': { zh: '未指定（继续播放/随心听）', en: 'Continue Playback' },
    'Popular Hits / 热门精选': { zh: '热门精选', en: 'Popular Hits' },
    '未指定（默认播放热门精选）': { zh: '未指定（默认播放热门精选）', en: 'Unspecified (Top Hits)' },
    '绝对温度设定 / Target Temp': { zh: '设定目标温度', en: 'Target Temperature' },
    '相对温度微调 / Relative Delta': { zh: '相对温度微调', en: 'Relative Delta' },
    '全车 / All Zones': { zh: '全车', en: 'All Zones' },
    '主驾 / Driver': { zh: '主驾', en: 'Driver' },
    '副驾 / Passenger': { zh: '副驾', en: 'Passenger' },
    '后排 / Rear': { zh: '后排', en: 'Rear' },
    '自动 (AUTO)': { zh: '自动 (AUTO)', en: 'Automatic (AUTO)' },
    '制冷 (A/C)': { zh: '制冷 (A/C)', en: 'Cooling (A/C)' },
    '制热 (HEATER)': { zh: '制热 (HEATER)', en: 'Heating (HEATER)' },
    '除雾/除霜 / Defrost': { zh: '除雾/除霜', en: 'Defrost' },
    '内循环 / Recirculation': { zh: '内循环', en: 'Recirculation' },
    '外循环 / Fresh Air': { zh: '外循环', en: 'Fresh Air' },
    '设置目的地导航 / Set Destination': { zh: '设置目的地导航', en: 'Set Destination' },
    '退出导航 / Exit Navigation': { zh: '退出导航', en: 'Exit Navigation' },
    '查询路线 / Check Route': { zh: '查询路线', en: 'Check Route' },
    '查询路况 / Check Traffic': { zh: '查询路况', en: 'Check Traffic' },
    '周边/沿途搜索 / Nearby Search': { zh: '周边/沿途搜索', en: 'Nearby Search' },
    '系统推荐 / Default': { zh: '系统推荐', en: 'Default' },
    '躲避拥堵 / Avoid Congestion': { zh: '躲避拥堵', en: 'Avoid Congestion' },
    '不走高速 / Avoid Highways': { zh: '不走高速', en: 'Avoid Highways' },
    '高速优先 / Highway First': { zh: '高速优先', en: 'Highway First' },
    '距离最短 / Shortest Route': { zh: '距离最短', en: 'Shortest Route' },
    '时间最快 / Fastest Route': { zh: '时间最快', en: 'Fastest Route' },
    '公司 / Office': { zh: '公司', en: 'Office' },
    '家 / Home': { zh: '家', en: 'Home' },
    '拨打电话 / Make Call': { zh: '拨打电话', en: 'Make Call' },
    '挂断电话 / Hang Up': { zh: '挂断电话', en: 'Hang Up' },
    '接听电话 / Answer Call': { zh: '接听电话', en: 'Answer Call' },
    '重拨电话 / Redial': { zh: '重拨电话', en: 'Redial' }
  };

  if (DICT[val]) {
    return DICT[val][lang];
  }

  if (val.includes('智能推荐')) {
    if (lang === 'en') {
      let g = val.replace(/^未指定（按\s*/, '').replace(/\s*智能推荐）.*$/, '');
      if (g.includes('/')) {
        const parts = g.split('+').map(p => {
          const slash = p.split('/');
          return slash[1] ? slash[1].trim() : slash[0].trim();
        });
        g = parts.join(' + ');
      }
      return `Unspecified (Recommended by ${g})`;
    } else {
      return val.replace(/\s*\/\s*Recommendation.*$/, '');
    }
  }

  if (val.includes(' / ')) {
    const parts = val.split(' / ');
    return lang === 'en' ? parts[parts.length - 1].trim() : parts[0].trim();
  }

  return val;
}

function setLanguage(lang) {
  CURRENT_LANG = lang;
  localStorage.setItem('ne_lang', lang);
  const t = I18N[lang];

  $('heroTitle').textContent = t.heroTitle;
  $('heroTagline').innerHTML = t.heroTagline;
  $('heroAttr').innerHTML = t.heroAttr;
  $('heroCtaGo').textContent = t.heroCtaGo;
  $('heroCtaDemo').textContent = t.heroCtaDemo;
  $('heroCtaCfg').textContent = t.heroCtaCfg;
  $('consoleTitle').textContent = t.consoleTitle;
  $('consoleMeta').textContent = t.consoleMeta;
  $('q').placeholder = t.placeholder;
  $('go').textContent = t.go;
  $('dCap').innerHTML = `${t.dCap}<span id="dcount">${INTENTS.length}</span>）：`;
  $('lblWall').textContent = t.lblWall;
  $('lblModel').textContent = t.lblModel;
  $('lblTok').textContent = t.lblTok;
  $('tokNote').textContent = t.tokNote;
  $('emptyTitle').textContent = t.emptyTitle;
  $('emptyDesc').textContent = t.emptyDesc;
  $('noulTitle').textContent = t.noulTitle;
  $('noulSub').textContent = t.noulSub;
  $('choiceTitle').textContent = t.choiceTitle;
  $('choiceSub').textContent = t.choiceSub;
  $('cardTitleMusic').textContent = t.cardTitleMusic;
  $('cardSubMusic').textContent = t.cardSubMusic;
  $('lblSlotArtist').textContent = t.lblSlotArtist;
  $('lblSlotSong').textContent = t.lblSlotSong;
  $('lblSlotMood').textContent = t.lblSlotMood;
  $('lblSlotAction').textContent = t.lblSlotAction;
  $('cardTitleClimate').textContent = t.cardTitleClimate;
  $('cardSubClimate').textContent = t.cardSubClimate;
  $('lblSlotTemp').textContent = t.lblSlotTemp;
  $('lblSlotTempType').textContent = t.lblSlotTempType;
  $('lblSlotZone').textContent = t.lblSlotZone;
  $('lblSlotClimateMode').textContent = t.lblSlotClimateMode;
  $('cardTitleNav').textContent = t.cardTitleNav;
  $('cardSubNav').textContent = t.cardSubNav;
  $('lblSlotNavDest').textContent = t.lblSlotNavDest;
  $('lblSlotNavAction').textContent = t.lblSlotNavAction;
  $('lblSlotNavPref').textContent = t.lblSlotNavPref;
  $('cardTitlePhone').textContent = t.cardTitlePhone;
  $('cardSubPhone').textContent = t.cardSubPhone;
  $('lblSlotPhoneContact').textContent = t.lblSlotPhoneContact;
  $('lblSlotPhoneNumber').textContent = t.lblSlotPhoneNumber;
  $('lblSlotPhoneAction').textContent = t.lblSlotPhoneAction;
  $('cardTitleQuery').textContent = t.cardTitleQuery;
  $('cardSubQuery').textContent = t.cardSubQuery;
  $('lblSlotQueryType').textContent = t.lblSlotQueryType;
  $('lblSlotQueryTarget').textContent = t.lblSlotQueryTarget;
  $('lblSlotQueryChannel').textContent = t.lblSlotQueryChannel;
  $('mgmtTitle').textContent = t.mgmtTitle;
  $('mgmtSub').textContent = t.mgmtSub;
  $('thName').textContent = t.thName;
  $('thDesc').textContent = t.thDesc;
  $('thChoice').textContent = t.thChoice;
  $('thNoul').textContent = t.thNoul;
  $('thOps').textContent = t.thOps;
  $('iName').placeholder = t.iNamePlaceholder;
  $('iDesc').placeholder = t.iDescPlaceholder;
  $('lblChoice').textContent = t.lblChoice;
  $('lblNoul').textContent = t.lblNoul;
  $('iSave').textContent = t.iSaveAdd;
  $('iCancel').textContent = t.iCancel;
  $('langLabel').textContent = t.langLabel;
  $('themeLabel').textContent = CURRENT_THEME === 'dark' ? (lang === 'zh' ? '浅色' : 'LIGHT') : (lang === 'zh' ? '深色' : 'DARK');

  $('ex').innerHTML = `<span class="ex-label">${t.exLabel}</span>` + t.examples.map(ex => `<button type="button">${esc(ex)}</button>`).join('');

  renderCfg();
  if (window.LAST_RESULT && window.LAST_TEXT) {
    render(window.LAST_RESULT, window.LAST_TEXT);
  }
}

function toggleTheme() {
  CURRENT_THEME = CURRENT_THEME === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', CURRENT_THEME);
  localStorage.setItem('ne_theme', CURRENT_THEME);
  const t = I18N[CURRENT_LANG];
  $('themeLabel').textContent = CURRENT_THEME === 'dark' ? (CURRENT_LANG === 'zh' ? '浅色' : 'LIGHT') : (CURRENT_LANG === 'zh' ? '深色' : 'DARK');
}

$('themeBtn').addEventListener('click', toggleTheme);
$('langBtn').addEventListener('click', () => {
  setLanguage(CURRENT_LANG === 'zh' ? 'en' : 'zh');
});

$('heroCtaDemo').addEventListener('click', () => {
  const demoQuery = CURRENT_LANG === 'en'
    ? 'call John, play some jazz music, and set temperature to 22 degrees'
    : '我想给张三打电话，我还想听一首林俊杰的伟大的渺小，再帮我导航去公司';
  $('q').value = demoQuery;
  $('console').scrollIntoView({ behavior: 'smooth' });
  judge(demoQuery);
});

/* ── Domain Config Management ── */
async function api(url, opts) {
  const r = await fetch(url, opts);
  const d = await r.json();
  if (!r.ok || !d.ok) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}

function getDomainDesc(name, rawDesc) {
  if (DOMAIN_I18N[name]) {
    return DOMAIN_I18N[name][CURRENT_LANG];
  }
  return rawDesc;
}

function renderCfg() {
  const t = I18N[CURRENT_LANG];
  $('dcount').textContent = INTENTS.length;
  $('dchips').innerHTML = INTENTS.map(x => {
    const desc = getDomainDesc(x.name, x.desc);
    return `<span class="dchip" title="${esc(desc)}"><b>${esc(x.name)}</b>${esc(desc)}` +
      `${x.in_noul ? ' <span class="noul-dot" title="Multi-Label">●</span>' : ''}` +
      `${x.name === 'other' ? ' <span style="opacity:0.6">[DEFAULT]</span>' : ''}</span>`;
  }).join('');

  $('cfgBody').innerHTML = INTENTS.map(x => {
    const desc = getDomainDesc(x.name, x.desc);
    return `
    <tr>
      <td class="name">${esc(x.name)}</td>
      <td class="desc">${esc(desc)}</td>
      <td class="ck ${x.in_choice ? '' : 'off'}">${x.in_choice ? '✓' : '—'}</td>
      <td class="ck ${x.in_noul ? '' : 'off'}">${x.in_noul ? '✓' : '—'}</td>
      <td>
        <button class="op" data-edit="${esc(x.name)}">${t.btnEdit}</button>
        <button class="op del" data-del="${esc(x.name)}" ${x.name === 'other' ? 'disabled title="Protected category"' : ''}>${t.btnDel}</button>
      </td>
    </tr>`;
  }).join('');
}

async function loadCfg() {
  try { INTENTS = (await api('/api/config')).intents; renderCfg(); }
  catch (e) { $('mgmtStatus').className = 'err'; $('mgmtStatus').textContent = 'Error loading config: ' + e.message; }
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
    st.textContent = (editing ? (CURRENT_LANG === 'zh' ? '已更新 ' : 'Updated ') : (CURRENT_LANG === 'zh' ? '已添加 ' : 'Added ')) + name;
    resetForm(); await loadCfg();
  } catch (e) { st.className = 'err'; st.textContent = e.message; }
}
function resetForm() {
  editing = null;
  $('iName').value = ''; $('iName').disabled = false;
  $('iDesc').value = '';
  $('iChoice').checked = true; $('iNoul').checked = true;
  $('iSave').textContent = I18N[CURRENT_LANG].iSaveAdd; $('iCancel').hidden = true;
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
    $('iSave').textContent = I18N[CURRENT_LANG].iSaveEdit; $('iCancel').hidden = false;
    st.textContent = (CURRENT_LANG === 'zh' ? '正在编辑 ' : 'Editing ') + x.name;
  } else if (b.dataset.del) {
    const msg = I18N[CURRENT_LANG].delConfirm.replace('{name}', b.dataset.del);
    if (confirm(msg)) {
      try {
        await api('/api/config/intent', {
          method: 'DELETE', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({name: b.dataset.del}),
        });
        st.textContent = (CURRENT_LANG === 'zh' ? '已删除 ' : 'Deleted ') + b.dataset.del;
        await loadCfg();
      } catch (err) { st.className = 'err'; st.textContent = err.message; }
    }
  }
});

/* ── Bar Chart Rendering ── */
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function bars(rows, chipFn) {
  const max = Math.max(...rows.map(r => r.v), 0.001);
  return rows.map(r => {
    const chip = chipFn ? `<span class="chip ${r.cls || ''}">${chipFn(r)}</span>` : '';
    return `<div class="brow ${r.top ? 'top' : ''} ${r.dim ? 'dim' : ''}" title="${esc(r.label)}: ${r.v.toFixed(4)}">
      <span class="bl">${esc(r.label)}</span>
      <span class="track"><span class="fill" style="width:${Math.max(r.v / max * 100, .8)}%"></span></span>
      <span class="bv">${r.v.toFixed(2)}</span>${chip}</div>`;
  }).join('');
}

/* ── Result Presentation ── */
function render(d, text) {
  window.LAST_RESULT = d;
  window.LAST_TEXT = text;

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
      return h + (act === 'turn_off' ? (CURRENT_LANG === 'en' ? ' (OFF)' : ' (关闭)') : (act === 'turn_on' ? (CURRENT_LANG === 'en' ? ' (ON)' : ' (开启)') : ''));
    });
    verdictHtml = `<span class="verdict-tag">${CURRENT_LANG === 'en' ? 'MULTI-INTENT' : '多指令并发'} · ${esc(labels.join(' + '))}</span>`;
  } else if (hit.length === 1) {
    const act = domainActions[hit[0]] ? domainActions[hit[0]].action : '';
    const actLabel = act === 'turn_off' ? (CURRENT_LANG === 'en' ? ' (OFF)' : ' (关闭)') : (act === 'turn_on' ? (CURRENT_LANG === 'en' ? ' (ON)' : ' (开启)') : '');
    verdictHtml = `<span class="verdict-tag">${CURRENT_LANG === 'en' ? 'SINGLE INTENT' : '单指令'} · ${esc(hit[0] + actLabel)}</span>`;
  } else if (d.intent && d.intent.choice === 'query') {
    verdictHtml = `<span class="verdict-tag query">💬 ${CURRENT_LANG === 'en' ? 'VOICE ASSISTANT · INFO BROADCAST' : '语音问答分流 · 助手信息播报'}</span>`;
  } else if (d.intent && d.intent.choice !== 'other') {
    verdictHtml = `<span class="verdict-tag">${CURRENT_LANG === 'en' ? 'TOP INTENT' : '主意图'} · ${esc(d.intent.choice)}</span>`;
  } else {
    verdictHtml = `<span class="verdict-tag uncertain">${CURRENT_LANG === 'en' ? 'FALLBACK / UNCERTAIN' : '兜底 / 未明确'}${gray.length ? ' (' + gray.join(', ') + ')' : ''}</span>`;
  }

  if (hit.length >= 1 && (hasQueryCue || d.intent.choice === 'query')) {
    verdictHtml += `<span class="ex-tag">💬 ${CURRENT_LANG === 'en' ? 'TTS Info Broadcast (Dual-Track)' : '双轨分流：语音助手播报'}</span>`;
  }

  if (excludedHits.length) {
    verdictHtml += `<span class="ex-tag" style="border-color:var(--danger);color:var(--danger);">⏸️ ${CURRENT_LANG === 'en' ? 'CAN Negation Excluded: ' : 'CAN 否定排除项：'}${esc(excludedHits.join(', '))}</span>`;
  }
  vd.innerHTML = verdictHtml;

  // Render Multi-label Probability Bars
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
      if (r.isEx) return CURRENT_LANG === 'en' ? 'EXCLUDED' : '已排除';
      if (r.isOff && r.v >= 0.70) return CURRENT_LANG === 'en' ? 'YES (OFF)' : 'YES (关)';
      if (r.v >= 0.70) return CURRENT_LANG === 'en' ? 'YES (ON)' : 'YES (开)';
      if (r.v >= 0.50) return CURRENT_LANG === 'en' ? 'GRAY' : '灰区';
      return '—';
    }
  ) : '<p style="color:var(--ink-mute);font-family:var(--font-mono);font-size:12px;">No active domains</p>';

  const probs = Object.entries(d.intent.probabilities).map(([k, v]) => ({k, v})).sort((a, b) => b.v - a.v);
  $('choiceBars').innerHTML = bars(
    probs.map(x => ({label: x.k, v: x.v, top: x.k === d.intent.choice})), null);

  // Render Music Slots
  if (d.music_slots && (d.intent.choice === 'music' || (d.domains && d.domains.music >= 0.30) || d.music_slots.artist !== '未指定 / Unspecified' || d.music_slots.song !== '未指定 / Unspecified' || d.music_slots.mood !== '未限定 / Any Mood')) {
    $('slotArtist').textContent = localizeSlotValue(d.music_slots.artist, CURRENT_LANG);
    $('slotSong').textContent = localizeSlotValue(d.music_slots.song, CURRENT_LANG);
    $('slotMood').textContent = localizeSlotValue(d.music_slots.mood, CURRENT_LANG);
    $('slotAction').textContent = localizeSlotValue(d.music_slots.action, CURRENT_LANG);
    $('slotDetails').innerHTML = `
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Target Mode: ' : '点播模式：'}${esc(localizeSlotValue(d.music_slots.target_type, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Action: ' : '控制动作：'}${esc(localizeSlotValue(d.music_slots.action, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? '21 Acoustic Genres Covered' : '21 种全曲风覆盖 · 零生成等待'}</span>
    `;
    $('musicCard').hidden = false;
  } else {
    $('musicCard').hidden = true;
  }

  // Render Climate Slots
  if (d.climate_slots && !exclusions.includes('climate') && (d.intent.choice === 'climate' || (d.domains && d.domains.climate >= 0.35) || d.climate_slots.target_temp !== '未指定 / Unspecified' || d.climate_slots.temp_type !== '未指定 / Unspecified')) {
    $('slotTemp').textContent = localizeSlotValue(d.climate_slots.target_temp, CURRENT_LANG);
    $('slotTempType').textContent = localizeSlotValue(d.climate_slots.temp_type, CURRENT_LANG);
    $('slotZone').textContent = localizeSlotValue(d.climate_slots.zone, CURRENT_LANG);
    $('slotClimateMode').textContent = localizeSlotValue(d.climate_slots.mode, CURRENT_LANG);
    $('climateDetails').innerHTML = `
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Cabin Zone: ' : '温区目标：'}${esc(localizeSlotValue(d.climate_slots.zone, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Mode: ' : '工作模式：'}${esc(localizeSlotValue(d.climate_slots.mode, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Adjustment: ' : '调节方式：'}${esc(localizeSlotValue(d.climate_slots.temp_type, CURRENT_LANG))}</span>
    `;
    $('climateCard').hidden = false;
  } else {
    $('climateCard').hidden = true;
  }

  // Render Navigation Slots
  if (d.nav_slots && !exclusions.includes('navigation') && (d.intent.choice === 'navigation' || (d.domains && d.domains.navigation >= 0.35) || d.nav_slots.destination !== '未指定 / Unspecified')) {
    $('slotNavDest').textContent = localizeSlotValue(d.nav_slots.destination, CURRENT_LANG);
    $('slotNavAction').textContent = localizeSlotValue(d.nav_slots.action, CURRENT_LANG);
    $('slotNavPref').textContent = localizeSlotValue(d.nav_slots.preference, CURRENT_LANG);
    $('navDetails').innerHTML = `
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Destination: ' : '目标地点：'}${esc(localizeSlotValue(d.nav_slots.destination, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Preference: ' : '规划偏好：'}${esc(localizeSlotValue(d.nav_slots.preference, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Action: ' : '导航动作：'}${esc(localizeSlotValue(d.nav_slots.action, CURRENT_LANG))}</span>
    `;
    $('navCard').hidden = false;
  } else {
    $('navCard').hidden = true;
  }

  // Render Telephony Slots
  if (d.phone_slots && !exclusions.includes('phone') && (d.intent.choice === 'phone' || (d.domains && d.domains.phone >= 0.35) || d.phone_slots.contact !== '未指定 / Unspecified' || d.phone_slots.phone_number !== '未指定 / Unspecified')) {
    $('slotPhoneContact').textContent = localizeSlotValue(d.phone_slots.contact, CURRENT_LANG);
    $('slotPhoneNumber').textContent = localizeSlotValue(d.phone_slots.phone_number, CURRENT_LANG);
    $('slotPhoneAction').textContent = localizeSlotValue(d.phone_slots.action, CURRENT_LANG);
    $('phoneDetails').innerHTML = `
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Recipient: ' : '呼叫对象：'}${esc(localizeSlotValue(d.phone_slots.contact, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Number: ' : '拨号号码：'}${esc(localizeSlotValue(d.phone_slots.phone_number, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Action: ' : '通话动作：'}${esc(localizeSlotValue(d.phone_slots.action, CURRENT_LANG))}</span>
    `;
    $('phoneCard').hidden = false;
  } else {
    $('phoneCard').hidden = true;
  }

  // Render Query Assistant Slots
  if (d.query_slots && (d.intent.choice === 'query' || (d.domains && d.domains.query >= 0.35) || hasQueryCue)) {
    $('slotQueryType').textContent = localizeSlotValue(d.query_slots.query_type, CURRENT_LANG);
    $('slotQueryTarget').textContent = localizeSlotValue(d.query_slots.query_target, CURRENT_LANG);
    $('slotQueryChannel').textContent = localizeSlotValue(d.query_slots.channel, CURRENT_LANG);
    $('queryDetails').innerHTML = `
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Category: ' : '问答类别：'}${esc(localizeSlotValue(d.query_slots.query_type, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Target: ' : '查询目标：'}${esc(localizeSlotValue(d.query_slots.query_target, CURRENT_LANG))}</span>
      <span class="slot-tag">${CURRENT_LANG === 'en' ? 'Channel: TTS Assistant' : '响应方式：语音助手播报'}</span>
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
    st.className = 'err'; st.textContent = (CURRENT_LANG === 'en' ? 'Evaluation Failed: ' : '失败：') + e.message;
  } finally { go.disabled = false; }
}

$('f').addEventListener('submit', e => {
  e.preventDefault();
  const t = $('q').value.trim();
  if (t) judge(t);
});

$('ex').addEventListener('click', e => {
  if (e.target.tagName === 'BUTTON') {
    $('q').value = e.target.textContent;
    judge(e.target.textContent);
  }
});

setLanguage(CURRENT_LANG);
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
