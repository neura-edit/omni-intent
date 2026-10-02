#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEURA EDIT · OmniIntent 100 In-Cabin Benchmark Dataset Generator
Covers 7 domains, multi-intent concurrency, negation avoidance, and 3 languages (ZH, ZHTW, EN).
"""
import json

test_cases = [
    # ── Category 1: Climate (15 cases) ──
    {"id": 1, "query": "把空调调到二十四度", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 2, "query": "车里有点冷，把暖气打开", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 3, "query": "把温度调低两度", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 4, "query": "打开前挡风玻璃除雾", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 5, "query": "主驾驶空调风量调到最大", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 6, "query": "把空调关掉，有点吹得头疼", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate", "turn_off": ["climate"]},
    {"id": 7, "query": "開啟副駕駛空調，設定為二十二度", "lang": "zhtw", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 8, "query": "將車內溫度調高三度", "lang": "zhtw", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 9, "query": "後排空調風速減小一檔", "lang": "zhtw", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 10, "query": "Set cabin temperature to 21 degrees Celsius", "lang": "en", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 11, "query": "Turn on maximum defroster for the windshield", "lang": "en", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 12, "query": "Shut down the air conditioner", "lang": "en", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate", "turn_off": ["climate"]},
    {"id": 13, "query": "空调切换为内循环模式", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 14, "query": "把后排出风口关闭", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 15, "query": "太热了，制冷开到最强", "lang": "zh", "category": "climate", "expected_domains": ["climate"], "expected_choice": "climate"},

    # ── Category 2: Music & Audio (15 cases) ──
    {"id": 16, "query": "播放周杰伦的晴天", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 17, "query": "放一首八三夭的外婆的告别式这首歌", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 18, "query": "我们要听放克风格的音乐", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 19, "query": "切到下一首歌曲", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 20, "query": "暂停播放音乐", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music", "turn_off": ["music"]},
    {"id": 21, "query": "来点欢快提神的车载音乐", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 22, "query": "播放陳奕迅的富士山下", "lang": "zhtw", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 23, "query": "播放古典交響樂放鬆一下", "lang": "zhtw", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 24, "query": "單曲循環當前播放的這首歌", "lang": "zhtw", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 25, "query": "Play some classic rock tracks", "lang": "en", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 26, "query": "Play My Heart Will Go On by Celine Dion", "lang": "en", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 27, "query": "Skip to the next track please", "lang": "en", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 28, "query": "调大音乐音量到百分之六十", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 29, "query": "我想听爵士乐电台", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},
    {"id": 30, "query": "随机播放我收藏的流行歌单", "lang": "zh", "category": "music", "expected_domains": ["music"], "expected_choice": "music"},

    # ── Category 3: Navigation (15 cases) ──
    {"id": 31, "query": "导航去上海虹桥火车站，躲避拥堵", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 32, "query": "带我回公司，选择距离最短路线", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 33, "query": "导航回家，不走高速", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 34, "query": "退出当前的导航路线", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation", "turn_off": ["navigation"]},
    {"id": 35, "query": "搜索沿途最近的特来电充电站", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 36, "query": "看下前面路段堵不堵车", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 37, "query": "導航前往香港國際機場", "lang": "zhtw", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 38, "query": "帶我去台北車站，高速優先", "lang": "zhtw", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 39, "query": "查詢附近哪裡有加油站", "lang": "zhtw", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 40, "query": "Navigate to downtown Seattle avoiding toll roads", "lang": "en", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 41, "query": "Find the fastest route to JFK airport", "lang": "en", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 42, "query": "Cancel current navigation route", "lang": "en", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation", "turn_off": ["navigation"]},
    {"id": 43, "query": "导航去西藏布达拉宫", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 44, "query": "重新规划一条避开收费站的路线", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},
    {"id": 45, "query": "查找附近的五星级酒店", "lang": "zh", "category": "navigation", "expected_domains": ["navigation"], "expected_choice": "navigation"},

    # ── Category 4: Seat Comfort (8 cases) ──
    {"id": 46, "query": "把主驾座椅加热开到二档", "lang": "zh", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat"},
    {"id": 47, "query": "副驾驶座椅通风打开", "lang": "zh", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat"},
    {"id": 48, "query": "把后排座椅加热全部关掉", "lang": "zh", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat", "turn_off": ["seat"]},
    {"id": 49, "query": "開啟駕駛座腰部按摩功能", "lang": "zhtw", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat"},
    {"id": 50, "query": "關閉副駕駛座椅加熱", "lang": "zhtw", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat", "turn_off": ["seat"]},
    {"id": 51, "query": "Turn on driver seat heating to level 3", "lang": "en", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat"},
    {"id": 52, "query": "Enable passenger seat ventilation", "lang": "en", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat"},
    {"id": 53, "query": "把主驾驶座椅靠背往后调一点", "lang": "zh", "category": "seat", "expected_domains": ["seat"], "expected_choice": "seat"},

    # ── Category 5: Windows & Sunroof (8 cases) ──
    {"id": 54, "query": "把左前车窗降下一半透透气", "lang": "zh", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 55, "query": "把车窗全部关上", "lang": "zh", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 56, "query": "天窗打开留一条缝", "lang": "zh", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 57, "query": "把天窗遮阳帘关上，太阳太晒了", "lang": "zh", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 58, "query": "將所有車窗升起並關閉天窗", "lang": "zhtw", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 59, "query": "Roll down the front windows halfway", "lang": "en", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 60, "query": "Close the sunroof and sunshade", "lang": "en", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},
    {"id": 61, "query": "副驾车窗降到底", "lang": "zh", "category": "window", "expected_domains": ["window"], "expected_choice": "window"},

    # ── Category 6: Phone & Contacts (8 cases) ──
    {"id": 62, "query": "给张三打个电话", "lang": "zh", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},
    {"id": 63, "query": "拨打电话给老婆", "lang": "zh", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},
    {"id": 64, "query": "呼叫电话号码 13800138000", "lang": "zh", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},
    {"id": 65, "query": "把当前的通话挂断", "lang": "zh", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone", "turn_off": ["phone"]},
    {"id": 66, "query": "打電話給李四經理", "lang": "zhtw", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},
    {"id": 67, "query": "Call my wife on mobile", "lang": "en", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},
    {"id": 68, "query": "Redial the last outgoing number", "lang": "en", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},
    {"id": 69, "query": "给爸爸回拨电话", "lang": "zh", "category": "phone", "expected_domains": ["phone"], "expected_choice": "phone"},

    # ── Category 7: Query & Assistant (8 cases) ──
    {"id": 70, "query": "今天北京天气怎么样，会下雨吗", "lang": "zh", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 71, "query": "现在几点了", "lang": "zh", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 72, "query": "今天尾号限行几号", "lang": "zh", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 73, "query": "车辆剩余电量还能跑多少公里", "lang": "zh", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 74, "query": "查詢明天香港的天氣預報", "lang": "zhtw", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 75, "query": "What is the weather forecast for Seattle today", "lang": "en", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 76, "query": "What is the current battery range of this vehicle", "lang": "en", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},
    {"id": 77, "query": "今天星期几，农历初几", "lang": "zh", "category": "query", "expected_domains": ["query"], "expected_choice": "query"},

    # ── Category 8: Multi-Intent Concurrency (15 cases) ──
    {"id": 78, "query": "打开空调，放一首八三夭的外婆的告别式，再导航去香港", "lang": "zh", "category": "multi_intent", "expected_domains": ["climate", "music", "navigation"], "expected_choice": "climate"},
    {"id": 79, "query": "车里有点闷，把空调调到22度，然后放一首周杰伦的晴天", "lang": "zh", "category": "multi_intent", "expected_domains": ["climate", "music"], "expected_choice": "climate"},
    {"id": 80, "query": "把车窗打开，把音乐打开，空调调到二十度", "lang": "zh", "category": "multi_intent", "expected_domains": ["window", "music", "climate"], "expected_choice": "climate"},
    {"id": 81, "query": "把左前车窗降下一半，座椅加热开到二档", "lang": "zh", "category": "multi_intent", "expected_domains": ["window", "seat"], "expected_choice": "seat"},
    {"id": 82, "query": "导航去公司，顺便播放一些轻音乐", "lang": "zh", "category": "multi_intent", "expected_domains": ["navigation", "music"], "expected_choice": "navigation"},
    {"id": 83, "query": "给老婆打电话，并且把导航设为回家", "lang": "zh", "category": "multi_intent", "expected_domains": ["phone", "navigation"], "expected_choice": "phone"},
    {"id": 84, "query": "把空调调到二十三度，同时开启主驾座椅通风", "lang": "zh", "category": "multi_intent", "expected_domains": ["climate", "seat"], "expected_choice": "climate"},
    {"id": 85, "query": "打開空調至二十四度，播放陳奕迅的歌，並導航到高鐵站", "lang": "zhtw", "category": "multi_intent", "expected_domains": ["climate", "music", "navigation"], "expected_choice": "climate"},
    {"id": 86, "query": "車窗降下一半，開啟座椅加熱", "lang": "zhtw", "category": "multi_intent", "expected_domains": ["window", "seat"], "expected_choice": "seat"},
    {"id": 87, "query": "打電話給張三，同時把導航退出來", "lang": "zhtw", "category": "multi_intent", "expected_domains": ["phone", "navigation"], "expected_choice": "phone"},
    {"id": 88, "query": "Turn on the AC, play a song by Celine Dion, and navigate to Seattle", "lang": "en", "category": "multi_intent", "expected_domains": ["climate", "music", "navigation"], "expected_choice": "climate"},
    {"id": 89, "query": "Set climate to 20 degrees and play some rock music", "lang": "en", "category": "multi_intent", "expected_domains": ["climate", "music"], "expected_choice": "climate"},
    {"id": 90, "query": "Roll down the driver window and turn on seat heating", "lang": "en", "category": "multi_intent", "expected_domains": ["window", "seat"], "expected_choice": "seat"},
    {"id": 91, "query": "把音乐声音关掉，查看一下前面的路况", "lang": "zh", "category": "multi_intent", "expected_domains": ["music", "navigation"], "expected_choice": "navigation", "turn_off": ["music"]},
    {"id": 92, "query": "关闭车窗，打开空调制冷模式", "lang": "zh", "category": "multi_intent", "expected_domains": ["window", "climate"], "expected_choice": "climate"},

    # ── Category 9: Negation & Conflict Avoidance (8 cases) ──
    {"id": 93, "query": "关闭空调，但是不要关座椅加热", "lang": "zh", "category": "negation_avoidance", "expected_domains": ["climate"], "expected_exclusions": ["seat"], "turn_off": ["climate"], "expected_choice": "climate"},
    {"id": 94, "query": "把车窗打开，不要动空调", "lang": "zh", "category": "negation_avoidance", "expected_domains": ["window"], "expected_exclusions": ["climate"], "expected_choice": "window"},
    {"id": 95, "query": "导航去公司，避开高速，不要播放音乐", "lang": "zh", "category": "negation_avoidance", "expected_domains": ["navigation"], "expected_exclusions": ["music"], "expected_choice": "navigation"},
    {"id": 96, "query": "把温度调低两度，不要开外循环", "lang": "zh", "category": "negation_avoidance", "expected_domains": ["climate"], "expected_choice": "climate"},
    {"id": 97, "query": "放一首轻快的歌，别开导航", "lang": "zh", "category": "negation_avoidance", "expected_domains": ["music"], "expected_exclusions": ["navigation"], "expected_choice": "music"},
    {"id": 98, "query": "關閉音樂，但保持導航開啟", "lang": "zhtw", "category": "negation_avoidance", "expected_domains": ["music"], "expected_exclusions": ["navigation"], "turn_off": ["music"], "expected_choice": "music"},
    {"id": 99, "query": "Turn off the climate control, but keep seat heating on", "lang": "en", "category": "negation_avoidance", "expected_domains": ["climate"], "expected_exclusions": ["seat"], "turn_off": ["climate"], "expected_choice": "climate"},
    {"id": 100, "query": "Open the windows halfway, do not touch the air conditioner", "lang": "en", "category": "negation_avoidance", "expected_domains": ["window"], "expected_exclusions": ["climate"], "expected_choice": "window"}
]

with open("benchmark/test_cases_100.json", "w", encoding="utf-8") as f:
    json.dump(test_cases, f, ensure_ascii=False, indent=2)

print(f"Generated {len(test_cases)} benchmark test cases into benchmark/test_cases_100.json")
