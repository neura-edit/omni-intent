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



# ── 音乐决策子问题体系（JEV 单次前向并行求解，毫秒级无生成延迟）──────────────
MUSIC_QUESTIONS = {
    "music_action": {
        "type": "choice",
        "instructions": "用户想要对音乐执行什么操作动作？",
        "criteria": {
            "play": "播放、点播、听音乐、来一首",
            "pause": "暂停、停止播放、别放了、关掉音乐",
            "next": "切歌、下一首、换一首、跳过",
            "prev": "上一首、退回上一首",
            "loop": "单曲循环",
            "random": "随机播放",
            "other": "其他操作",
        },
    },
    "music_mood": {
        "type": "choice",
        "instructions": "用户想听什么风格、流派或情绪的音乐？",
        "criteria": {
            "cheerful": "欢快、轻快、动感、轻松、开心、适合开车",
            "sad": "伤感、悲伤、安静、抒情、治愈、emo",
            "rock": "摇滚、燃、激情、金属、电音",
            "pop": "流行、经典老歌、现代流行",
            "folk": "民谣、纯音乐、民乐、乡村",
            "unspecified": "未指定特定情绪或风格",
        },
    },
    "music_artist": {
        "type": "choice",
        "instructions": "指令中是否指定了特定歌手或艺术家？",
        "criteria": {
            "jay_chou": "周杰伦（周董）",
            "eason_chan": "陈奕迅",
            "jj_lin": "林俊杰",
            "g_e_m": "邓紫棋",
            "mayday": "五月天",
            "other_artist": "提到了其他具体歌手",
            "none": "未指定歌手",
        },
    },
    "music_target": {
        "type": "choice",
        "instructions": "用户的具体点歌目标是什么形式？",
        "criteria": {
            "specific_song": "指名点播具体的某首歌（如晴天、青花瓷、稻香等）",
            "artist_all": "点播某个歌手的歌，未指定具体歌名（如'听周杰伦的音乐'）",
            "mood_all": "点播某种情绪风格的歌，未指定歌手歌名（如'放首欢快的歌'）",
            "random": "随便播放，无特定目标",
        },
    },
}


def extract_music_slots(text, answers):
    act = answers.get("music_action", {}).get("choice", "play")
    mood = answers.get("music_mood", {}).get("choice", "unspecified")
    artist_choice = answers.get("music_artist", {}).get("choice", "none")
    target = answers.get("music_target", {}).get("choice", "random")

    mood_map = {
        "cheerful": "欢快 / 轻松",
        "sad": "伤感 / 抒情",
        "rock": "摇滚 / 激情",
        "pop": "流行音乐",
        "folk": "民谣 / 纯音乐",
        "unspecified": "未限定",
    }
    action_map = {
        "play": "播放",
        "pause": "暂停",
        "next": "切到下一首",
        "prev": "上一首",
        "loop": "单曲循环",
        "random": "随机播放",
        "other": "其他控制",
    }
    target_map = {
        "specific_song": "指定特定歌曲",
        "artist_all": "点播歌手全部/热门单曲",
        "mood_all": "按曲风随心听",
        "random": "随机点播",
    }
    artist_map = {
        "jay_chou": "周杰伦",
        "eason_chan": "陈奕迅",
        "jj_lin": "林俊杰",
        "g_e_m": "邓紫棋",
        "mayday": "五月天",
    }

    artist = artist_map.get(artist_choice)
    song = None

    # 配合轻量句式正则做精确槽位切分（0ms 极速耗时）
    cleaned = re.sub(r"^(?:我想?听|请?帮我?放一?首|请?帮我?播放|来一?首|来点|播放|放点|听听|给我放|放首)", "", text).strip()
    cleaned = re.sub(r"(?:的?(?:音乐|歌|歌曲|曲子))$", "", cleaned).strip()

    if target == "specific_song":
        m = re.search(r"^(.*?)(?:的)(.+)$", cleaned)
        if m:
            cand_artist = m.group(1).strip()
            cand_song = m.group(2).strip()
            if not artist:
                artist = cand_artist
            song = cand_song
        else:
            if artist and cleaned.startswith(artist):
                song = cleaned[len(artist):].strip(" 的")
            elif artist and "周董" in cleaned:
                song = cleaned.replace("周董", "").strip(" 的")
            else:
                song = cleaned
    elif target == "artist_all":
        song = "未指定（默认播放歌手热门精选）"
        if not artist and cleaned:
            artist = cleaned.strip("的")
    elif target == "mood_all":
        song = "未指定（按风格智能推荐）"
    else:
        song = "未指定"

    return {
        "action": action_map.get(act, act),
        "mood": mood_map.get(mood, mood),
        "artist": artist or "未指定",
        "song": song or "未指定",
        "target_type": target_map.get(target, target),
        "raw": {
            "action": act,
            "mood": mood,
            "artist_choice": artist_choice,
            "target": target,
        },
    }


def build_questions(intents):
    choice = {x["name"]: x["desc"] for x in intents if x["in_choice"]}
    noul = [x for x in intents if x["in_noul"]]
    qs = {"intent": {"type": "choice",
                     "instructions": "判断这条车机语音指令属于哪一种功能",
                     "criteria": choice}}
    for x in noul:
        qs[x["name"]] = {"type": "noul",
                         "instructions": f"这条指令是否要求处理{x['desc']}？"}
    return qs


def call_ollaya(text):
    intents = load_intents()
    qs = build_questions(intents)
    # 并行加入音乐维度细粒度决策问题
    qs.update(MUSIC_QUESTIONS)
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
    domains = {x["name"]: ans[x["name"]]["noul"] for x in intents if x["in_noul"]}
    music_slots = extract_music_slots(text, ans)
    return {
        "intent": {"choice": ans["intent"]["choice"],
                   "probabilities": ans["intent"]["probabilities"]},
        "domains": domains,
        "music_slots": music_slots,
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
.chip.gray { color: var(--ink-2); }
.chip.gray::before { content: "◐"; margin-right: 4px; color: var(--warn); }
.chip.no { color: var(--muted); }
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
  <p class="sub">decision:eos · 单意图路由（choice）+ 多标签检出（noul）+ 音乐槽位多维决策 · 本地 ollaya 127.0.0.1:11435</p>

  <div class="domains-row">
    <span class="cap">支持的功能域（<span id="dcount">–</span>）：</span><span id="dchips"></span>
  </div>

  <form id="f">
    <input id="q" placeholder="输入一句话，如：我要听周杰伦的音乐，或者放一首轻快的晴天" autofocus>
    <button class="go" id="go" type="submit">判断</button>
  </form>
  <div class="examples" id="ex">示例：
    <button>我要听周杰伦的音乐</button><button>放一首周杰伦欢快的晴天</button><button>来点伤感的流行歌曲</button>
    <button>打开空调，然后播放周杰伦的歌</button><button>先暂停音乐，再导航去最近的加油站</button>
    <button>关闭空调，但是不要关座椅加热</button>
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

  const domains = Object.entries(d.domains).map(([k, v]) => ({k, v})).sort((a, b) => b.v - a.v);
  const hit = domains.filter(x => x.v >= 0.70).map(x => x.k);
  const gray = domains.filter(x => x.v >= 0.50 && x.v < 0.70).map(x => x.k);
  const vd = $('verdict');
  if (hit.length >= 2) { vd.textContent = `多指令 · ${hit.join(' + ')}`; }
  else if (hit.length === 1) { vd.textContent = `单指令 · ${hit[0]}`; }
  else { vd.textContent = `未检出${gray.length ? '（灰区：' + gray.join('、') + '，建议走兜底）' : ''}`; }

  $('noulBars').innerHTML = domains.length ? bars(
    domains.map(x => ({
      label: x.k, v: x.v,
      top: x.v >= 0.70, dim: x.v >= 0.50 && x.v < 0.70,
      cls: x.v >= 0.70 ? 'yes' : (x.v >= 0.50 ? 'gray' : 'no'),
    })),
    r => r.v >= 0.70 ? 'YES' : (r.v >= 0.50 ? '灰区' : '—')
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
