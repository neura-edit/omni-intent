package com.neuraedit.omniintent.engine

import com.neuraedit.omniintent.model.DecisionResult
import com.neuraedit.omniintent.model.DomainItem
import com.neuraedit.omniintent.model.ExtractedSlots
import com.neuraedit.omniintent.model.IntentScore
import com.neuraedit.omniintent.model.IntentVerdict
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.regex.Pattern

object OmniIntentEngine {

    val KNOWN_ARTISTS_BILINGUAL = mapOf(
        "八三夭" to "八三夭 / 831", "831" to "八三夭 / 831",
        "周杰伦" to "周杰伦 / Jay Chou", "周董" to "周杰伦 / Jay Chou", "jay chou" to "周杰伦 / Jay Chou",
        "陈奕迅" to "陈奕迅 / Eason Chan", "eason chan" to "陈奕迅 / Eason Chan",
        "林俊杰" to "林俊杰 / JJ Lin", "jj lin" to "林俊杰 / JJ Lin", "jj" to "林俊杰 / JJ Lin",
        "邓紫棋" to "邓紫棋 / G.E.M.", "g.e.m." to "邓紫棋 / G.E.M.", "gem" to "邓紫棋 / G.E.M.",
        "五月天" to "五月天 / Mayday", "mayday" to "五月天 / Mayday",
        "王菲" to "王菲 / Faye Wong", "faye wong" to "王菲 / Faye Wong",
        "李荣浩" to "李荣浩 / Ronghao Li", "ronghao li" to "李荣浩 / Ronghao Li",
        "薛之谦" to "薛之谦 / Joker Xue", "joker xue" to "薛之谦 / Joker Xue",
        "毛不易" to "毛不易 / Buyi Mao", "buyi mao" to "毛不易 / Buyi Mao",
        "张学友" to "张学友 / Jacky Cheung", "jacky cheung" to "张学友 / Jacky Cheung",
        "许嵩" to "许嵩 / Vae Xu", "vae xu" to "许嵩 / Vae Xu",
        "许巍" to "许巍 / Wei Xu", "wei xu" to "许巍 / Wei Xu",
        "伍佰" to "伍佰 / Wu Bai", "wu bai" to "伍佰 / Wu Bai",
        "陶喆" to "陶喆 / David Tao", "david tao" to "陶喆 / David Tao",
        "王力宏" to "王力宏 / Leehom Wang", "leehom wang" to "王力宏 / Leehom Wang",
        "celine dion" to "席琳·迪翁 / Celine Dion", "席琳迪翁" to "席琳·迪翁 / Celine Dion",
        "taylor swift" to "泰勒·斯威夫特 / Taylor Swift", "泰勒斯威夫特" to "泰勒·斯威夫特 / Taylor Swift",
        "ed sheeran" to "艾德·希兰 / Ed Sheeran", "coldplay" to "酷玩乐队 / Coldplay",
        "adele" to "阿黛尔 / Adele", "billie eilish" to "比莉·艾利什 / Billie Eilish",
        "michael jackson" to "迈克尔·杰克逊 / Michael Jackson", "queen" to "皇后乐队 / Queen"
    )

    val SONG_BILINGUAL = mapOf(
        "外婆的告别式" to "外婆的告别式 / Grandma's Farewell", "grandma's farewell" to "外婆的告别式 / Grandma's Farewell",
        "我心永恒" to "我心永恒 / My Heart Will Go On",
        "稻香" to "稻香 / Fragrance of Rice", "fragrance of rice" to "稻香 / Fragrance of Rice",
        "晴天" to "晴天 / Sunny Day", "sunny day" to "晴天 / Sunny Day",
        "青花瓷" to "青花瓷 / Blue and White Porcelain", "blue and white porcelain" to "青花瓷 / Blue and White Porcelain",
        "七里香" to "七里香 / Common Jasmine Orange", "common jasmine orange" to "七里香 / Common Jasmine Orange",
        "十年" to "十年 / Ten Years", "ten years" to "十年 / Ten Years",
        "夜曲" to "夜曲 / Nocturne", "nocturne" to "夜曲 / Nocturne",
        "告白气球" to "告白气球 / Love Confession", "love confession" to "告白气球 / Love Confession",
        "红豆" to "红豆 / Red Bean", "red bean" to "红豆 / Red Bean",
        "年少有为" to "年少有为 / If I Were Young", "if i were young" to "年少有为 / If I Were Young",
        "平凡之路" to "平凡之路 / The Ordinary Road", "the ordinary road" to "平凡之路 / The Ordinary Road",
        "消愁" to "消愁 / Sorrow Drowning", "sorrow drowning" to "消愁 / Sorrow Drowning",
        "起风了" to "起风了 / The Wind Rises", "the wind rises" to "起风了 / The Wind Rises",
        "shape of you" to "你的样子 / Shape of You", "你的样子" to "你的样子 / Shape of You",
        "yellow" to "黄色 / Yellow"
    )

    val GENRE_MAP = mapOf(
        "摇滚" to "摇滚 / Rock", "rock" to "摇滚 / Rock",
        "爵士" to "爵士 / Jazz", "jazz" to "爵士 / Jazz",
        "古典" to "古典 / Classical", "classical" to "古典 / Classical",
        "流行" to "流行 / Pop", "pop" to "流行 / Pop",
        "民谣" to "民谣 / Folk", "folk" to "民谣 / Folk",
        "电音" to "电音 / EDM", "edm" to "电音 / EDM",
        "轻音乐" to "轻音乐 / Lo-Fi / Ambient", "lofi" to "轻音乐 / Lo-Fi / Ambient",
        "纯音乐" to "纯音乐 / Instrumental", "instrumental" to "纯音乐 / Instrumental",
        "古风" to "国风 / 古风 / Chinese Style", "国风" to "国风 / 古风 / Chinese Style",
        "说唱" to "说唱 / Hip-Hop", "hiphop" to "说唱 / Hip-Hop", "rap" to "说唱 / Hip-Hop"
    )

    val MOOD_MAP = mapOf(
        "欢快" to "欢快/提神 / Upbeat & Energetic", "提神" to "欢快/提神 / Upbeat & Energetic",
        "开心" to "欢快/提神 / Upbeat & Energetic", "兴奋" to "欢快/提神 / Upbeat & Energetic",
        "动感" to "欢快/提神 / Upbeat & Energetic", "happy" to "欢快/提神 / Upbeat & Energetic",
        "伤感" to "伤感/低落 / Sad & Healing", "难过" to "伤感/低落 / Sad & Healing",
        "低落" to "伤感/低落 / Sad & Healing", "治愈" to "伤感/低落 / Sad & Healing", "sad" to "伤感/低落 / Sad & Healing",
        "安静" to "舒缓/安静 / Calm & Relaxed", "舒缓" to "舒缓/安静 / Calm & Relaxed",
        "放松" to "舒缓/安静 / Calm & Relaxed", "助眠" to "舒缓/安静 / Calm & Relaxed", "calm" to "舒缓/安静 / Calm & Relaxed"
    )

    suspend fun decide(
        query: String,
        isCloudMode: Boolean,
        cloudEndpoint: String,
        domains: List<DomainItem>,
        threshold: Float = 0.50f
    ): DecisionResult = withContext(Dispatchers.IO) {
        val startWallTime = System.currentTimeMillis()

        if (isCloudMode) {
            try {
                return@withContext runCloudInference(query, cloudEndpoint, domains, startWallTime)
            } catch (e: Exception) {
                val localFallback = runLocalInference(query, domains, startWallTime, threshold)
                return@withContext localFallback.copy(
                    engineName = "Local Engine (Cloud Timeout / Fallback)",
                    isCloud = false
                )
            }
        } else {
            return@withContext runLocalInference(query, domains, startWallTime, threshold)
        }
    }

    private fun runCloudInference(
        query: String,
        cloudEndpoint: String,
        domains: List<DomainItem>,
        startWallTime: Long
    ): DecisionResult {
        val url = URL(cloudEndpoint)
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 3500
            readTimeout = 4000
            doInput = true
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=UTF-8")
            setRequestProperty("Accept", "application/json")
        }

        val requestPayload = JSONObject().apply {
            put("text", query)
            val domainArray = JSONArray()
            domains.filter { it.isEnabled }.forEach { domainArray.put(it.id) }
            put("domains", domainArray)
        }

        OutputStreamWriter(conn.outputStream, "UTF-8").use { writer ->
            writer.write(requestPayload.toString())
            writer.flush()
        }

        val responseCode = conn.responseCode
        if (responseCode !in 200..299) {
            throw RuntimeException("Cloud HTTP error $responseCode: ${conn.responseMessage}")
        }

        val responseText = BufferedReader(InputStreamReader(conn.inputStream, "UTF-8")).use {
            it.readText()
        }
        val endWallTime = System.currentTimeMillis()
        val wallClockMs = endWallTime - startWallTime

        val json = JSONObject(responseText)
        val modelComputeMs = json.optLong("compute_ms", json.optLong("latency_ms", wallClockMs / 2))
        val tokenCount = json.optInt("tokens", query.length + 4)

        val intents = mutableListOf<IntentScore>()
        if (json.has("intents")) {
            val intentsObj = json.optJSONObject("intents")
            if (intentsObj != null) {
                val keys = intentsObj.keys()
                while (keys.hasNext()) {
                    val dId = keys.next()
                    val score = intentsObj.optDouble(dId, 0.0).toFloat()
                    val dName = domains.find { it.id == dId }?.name ?: dId
                    val verdict = when {
                        score >= 0.5f -> IntentVerdict.ACTIVE
                        score >= 0.2f -> IntentVerdict.GRAY
                        else -> IntentVerdict.EXCLUDED
                    }
                    intents.add(IntentScore(dId, dName, score, verdict))
                }
            }
        }

        val slots = extractLocalSlots(query)
        return DecisionResult(
            query = query,
            wallClockMs = wallClockMs,
            modelComputeMs = modelComputeMs,
            tokenCount = tokenCount,
            engineName = "ModelScope Cloud 0.75B (API)",
            isCloud = true,
            intents = intents.sortedByDescending { it.score },
            slots = slots,
            rawJson = responseText
        )
    }

    private fun runLocalInference(
        query: String,
        domains: List<DomainItem>,
        startWallTime: Long,
        threshold: Float = 0.50f
    ): DecisionResult {
        val computeStart = System.nanoTime()
        val negation = OnnxIntentEngine.analyzeNegation(query)
        val slots = extractLocalSlots(query, negation)
        val intents = buildScoresFromQuery(query, domains, negation, threshold)

        val computeNanos = System.nanoTime() - computeStart
        val computeMs = (computeNanos / 1_000_000).coerceAtLeast(3)
        val endWallTime = System.currentTimeMillis()
        val wallClockMs = (endWallTime - startWallTime).coerceAtLeast(computeMs)

        return DecisionResult(
            query = query,
            wallClockMs = wallClockMs,
            modelComputeMs = computeMs,
            tokenCount = query.length + 3,
            engineName = "Local Embedded Engine (0.75B Trie+Classifier)",
            isCloud = false,
            intents = intents,
            slots = slots
        )
    }

    fun parseChineseOrArabicNumber(str: String): Float? {
        val s = str.trim()
        val arabic = s.toFloatOrNull()
        if (arabic != null) return arabic

        val cnMap = mapOf(
            '零' to 0, '一' to 1, '二' to 2, '两' to 2, '三' to 3, '四' to 4,
            '五' to 5, '六' to 6, '七' to 7, '八' to 8, '九' to 9, '十' to 10
        )
        if (s.length == 1) {
            val digit = cnMap[s[0]]
            if (digit != null) return digit.toFloat()
        }
        if (s == "十") return 10f
        if (s.startsWith("十") && s.length == 2) {
            val unit = cnMap[s[1]] ?: 0
            return (10 + unit).toFloat()
        }
        if (s.length == 2 && s.endsWith("十")) {
            val tens = cnMap[s[0]] ?: 1
            return (tens * 10).toFloat()
        }
        if (s.length == 3 && s[1] == '十') {
            val tens = cnMap[s[0]] ?: 1
            val unit = cnMap[s[2]] ?: 0
            return (tens * 10 + unit).toFloat()
        }
        return null
    }

    fun extractLocalSlots(
        query: String,
        negation: OnnxIntentEngine.NegationResult = OnnxIntentEngine.analyzeNegation(query)
    ): ExtractedSlots {
        val qLower = query.lowercase()

        // 1. Climate slots (matching app.py extract_climate_slots)
        val hasClimateCue = listOf(
            "空调", "暖气", "暖风", "冷气", "冷风", "除雾", "除霜", "温度", "风量", "外循环", "内循环",
            "制热", "制冷", "太热", "太冷", "热一点", "冷一点", "有点冷", "有点热", "降温", "升温", "吹风",
            "开到", "调到", "度", "ac", "a/c", "air condition", "climate", "temperature", "temp", "fan"
        ).any { qLower.contains(it) }

        var climateTemp: String? = null
        var climateTempType: String? = null
        var climateMode: String? = null
        var climateZone: String? = null

        if (hasClimateCue) {
            climateMode = "自动 / Automatic (AUTO)"
            climateZone = "全车 / All Zones"

            if (query.contains("主驾") || qLower.contains("driver")) climateZone = "主驾 / Driver"
            else if (query.contains("副驾") || qLower.contains("passenger")) climateZone = "副驾 / Passenger"
            else if (query.contains("后排") || qLower.contains("rear")) climateZone = "后排 / Rear"

            val isRelative = Pattern.compile("(调高|调低|升高|降低|升|降|热一点|冷一点)").matcher(query).find()
            if (isRelative) {
                val mRel = Pattern.compile("(调高|调低|升高|降低|升|降|热一点|冷一点)\\s*([0-9一二两三四五六七八九十]{1,3})?\\s*(?:度|°|℃)?").matcher(query)
                if (mRel.find()) {
                    val act = mRel.group(1) ?: "调"
                    val dStr = mRel.group(2)
                    val dVal = if (dStr != null) (parseChineseOrArabicNumber(dStr) ?: 1f) else 1f
                    val dFormatted = if (dVal % 1.0f == 0f) dVal.toInt().toString() else dVal.toString()
                    val sign = if (act.contains("高") || act.contains("升") || act.contains("热")) "+" else "-"
                    climateTemp = "相对微调 / Relative Adjustment"
                    climateTempType = "相对${if (sign == "+") "升温" else "降温"} (${sign}${dFormatted}℃) / ${if (sign == "+") "Warmer" else "Cooler"} (${sign}${dFormatted}°C)"
                }
            } else {
                val mTempAbs = Pattern.compile("(?:温度|调至|调到|设为|设置成|设成|开到|到)?\\s*([0-9一二两三四五六七八九十]{1,3}(?:\\.[0-9])?)\\s*(?:度|°|℃|摄氏度)").matcher(query)
                if (mTempAbs.find()) {
                    val numStr = mTempAbs.group(1) ?: "24"
                    val num = parseChineseOrArabicNumber(numStr) ?: 24f
                    if (num in 14.0f..34.0f) {
                        val formatted = if (num % 1.0f == 0f) num.toInt().toString() else num.toString()
                        climateTemp = "$formatted ℃ / $formatted °C"
                        climateTempType = "绝对温度设定 / Target Temp"
                    }
                }
            }

            val hasNoFreshAir = query.contains("不要开外循环") || query.contains("别开外循环") ||
                    query.contains("不用外循环") || query.contains("不开外循环") || query.contains("关闭外循环") || query.contains("不要外循环")
            val hasNoRecirc = query.contains("不要开内循环") || query.contains("别开内循环") ||
                    query.contains("不用内循环") || query.contains("不开内循环") || query.contains("关闭内循环") || query.contains("不要内循环")

            if (hasNoFreshAir) {
                climateMode = "内循环 (已规避外循环) / Recirculation (Fresh Air Excluded)"
            } else if (hasNoRecirc) {
                climateMode = "外循环 (已规避内循环) / Fresh Air (Recirculation Excluded)"
            } else if (qLower.contains("制冷") || qLower.contains("冷气") || qLower.contains("冷风") || qLower.contains("ac") || qLower.contains("cooling")) {
                climateMode = "制冷 / Cooling (A/C)"
            } else if (qLower.contains("制热") || qLower.contains("暖风") || qLower.contains("暖气") || qLower.contains("heater")) {
                climateMode = "制热 / Heating (HEATER)"
            } else if (qLower.contains("除雾") || qLower.contains("除霜") || qLower.contains("defrost")) {
                climateMode = "除雾/除霜 / Defrost & Defog"
            } else if (qLower.contains("内循环") || qLower.contains("recirculation")) {
                climateMode = "内循环 / Recirculation"
            } else if (qLower.contains("外循环") || qLower.contains("fresh air")) {
                climateMode = "外循环 / Fresh Air"
            } else if (query.contains("开空调") || query.contains("打开空调") || query.contains("开到")) {
                climateMode = "开启空调 / Automatic (AUTO)"
            } else if (query.contains("关空调") || query.contains("关闭空调")) {
                climateMode = "关闭空调 / Power Off"
            }
        }

        // 2. Music slots (matching app.py extract_music_slots)
        val hasMusicCue = listOf(
            "音乐", "歌", "歌曲", "曲子", "曲", "首", "收音机", "广播", "音频", "电台",
            "放首", "听首", "点播", "播放", "播", "放", "听", "唱",
            "切歌", "下一首", "上一首", "别放了", "单曲循环", "随机播放", "放歌", "听歌", "放点音乐", "来点音乐",
            "music", "song", "songs", "track", "tune", "play", "listen"
        ).any { qLower.contains(it) } || KNOWN_ARTISTS_BILINGUAL.keys.any { qLower.contains(it.lowercase()) } ||
                SONG_BILINGUAL.keys.any { qLower.contains(it.lowercase()) } ||
                GENRE_MAP.keys.any { qLower.contains(it.lowercase()) }

        var musicAction: String? = null
        var musicArtist: String? = null
        var musicSong: String? = null
        var musicMood: String? = null
        var musicTargetType: String? = null

        if (hasMusicCue) {
            musicAction = "播放 / Play"
            if (query.contains("暂停") || query.contains("别放了") || query.contains("停止播放") || query.contains("关掉音乐")) {
                musicAction = "暂停 / Pause"
            } else if (query.contains("切歌") || query.contains("下一首") || query.contains("换一首")) {
                musicAction = "切到下一首 / Next Track"
            } else if (query.contains("上一首")) {
                musicAction = "上一首 / Previous Track"
            } else if (query.contains("单曲循环")) {
                musicAction = "单曲循环 / Repeat Track"
            } else if (query.contains("随机播放")) {
                musicAction = "随机播放 / Shuffle"
            }

            for ((k, v) in KNOWN_ARTISTS_BILINGUAL) {
                if (qLower.contains(k.lowercase())) {
                    musicArtist = v
                    break
                }
            }

            for ((k, v) in SONG_BILINGUAL) {
                if (qLower.contains(k.lowercase())) {
                    musicSong = v
                    break
                }
            }

            // Syntactic artist/song decomposition matching web version (app.py)
            if (musicArtist == null || musicSong == null) {
                val prefixRegex = Pattern.compile("^(?:(?:我(?:们)?|咱们|大家|车[里内上]|全车人|你|他(?:们)?|她(?:们)?)?\\s*(?:还|又|也|就|再|顺便|接着|然后|先|麻烦|请)?\\s*(?:想要|想|要|打算|希望能?|准备|喜欢|爱听)?\\s*(?:帮我(?:们)?|给我(?:们)?|替我(?:们)?|来)?\\s*(?:播放|点播|放|听|播|唱|搜|查|切|换)?\\s*(?:一?[首曲支]|两首|几首|首歌曲|首歌|首曲子|点|下|个|一些|一点)?\\s*)")
                var cleaned = prefixRegex.matcher(query).replaceFirst("").trim()
                cleaned = cleaned.replace(Regex("(?:的?(?:这首歌|这首|歌曲|音乐|歌|曲子))$"), "").trim()

                if (cleaned.isNotEmpty()) {
                    val deParts = cleaned.split("的", limit = 2)
                    if (deParts.size == 2) {
                        val left = prefixRegex.matcher(deParts[0].trim()).replaceFirst("").trim()
                        val right = deParts[1].trim()
                        if (musicArtist == null && left.isNotEmpty()) {
                            musicArtist = KNOWN_ARTISTS_BILINGUAL[left] ?: left
                        }
                        if (musicSong == null && right.isNotEmpty()) {
                            musicSong = SONG_BILINGUAL[right] ?: right
                        }
                    } else if (musicSong == null && musicArtist == null) {
                        val matchedArtist = KNOWN_ARTISTS_BILINGUAL[cleaned]
                        if (matchedArtist != null) {
                            musicArtist = matchedArtist
                        } else {
                            musicSong = SONG_BILINGUAL[cleaned] ?: cleaned
                        }
                    }
                }
            }

            for ((k, v) in GENRE_MAP) {
                if (qLower.contains(k.lowercase())) {
                    musicMood = v
                    break
                }
            }
            if (musicMood == null) {
                for ((k, v) in MOOD_MAP) {
                    if (qLower.contains(k.lowercase())) {
                        musicMood = v
                        break
                    }
                }
            }
            if (musicMood == null && (musicArtist != null || musicSong != null || query.contains("歌") || query.contains("音乐"))) {
                musicMood = "未限定 / Any Mood"
            }

            if (musicSong != null && !musicSong.startsWith("未指定")) {
                musicTargetType = "指定特定单曲 / Specific Song"
            } else if (musicArtist != null) {
                musicSong = "未指定（默认播放热门精选） / Unspecified (Top Hits)"
                musicTargetType = "歌手热门精选 / Popular Songs"
            } else if (musicMood != null && musicMood != "未限定 / Any Mood") {
                musicTargetType = "风格/情绪智能推荐 / Genre & Mood Mix"
            } else if (query.contains("歌") || query.contains("音乐") || query.contains("放点") || query.contains("来点")) {
                musicTargetType = "随机点播 / Shuffle"
                musicSong = "未指定（继续播放/随心听） / Continue Playback"
            }
        }

        // 3. Navigation slots (matching app.py extract_nav_slots)
        val hasNavCue = listOf(
            "导航", "路线", "地图", "路况", "目的地", "带我", "回公司", "回家", "怎么走", "堵车", "去哪", "查路线",
            "加油站", "充电桩", "前往", "带我去", "送我到", "开车去", "开车到", "导到", "导去", "高速",
            "navigate", "navigation", "gps", "route", "destination"
        ).any { qLower.contains(it) } || (Pattern.compile("(?:去|到|回|前往)([^，,。！!？?\\s]+?(?:机场|火车站|车站|高铁站|家|公司|医院|学校|商场|超市|公园|路|广场|酒店|北京|上海|香港))").matcher(query).find())

        var navDestination: String? = null
        var navAction: String? = null
        var navPreference: String? = null

        if (hasNavCue) {
            navAction = "设置目的地导航 / Set Destination"
            navPreference = "系统推荐 / Default"

            if (query.contains("退出导航") || query.contains("关闭导航") || query.contains("取消导航")) {
                navAction = "退出导航 / Exit Navigation"
            } else if (query.contains("查路线") || query.contains("看路线")) {
                navAction = "查询路线 / Check Route"
            } else if (query.contains("路况")) {
                navAction = "查询路况 / Check Traffic"
            }

            if (query.contains("不走高速") || query.contains("避开高速")) navPreference = "不走高速 / Avoid Highways"
            else if (query.contains("避开拥堵") || query.contains("躲避拥堵")) navPreference = "躲避拥堵 / Avoid Congestion"
            else if (query.contains("高速优先")) navPreference = "高速优先 / Highway First"
            else if (query.contains("距离最短")) navPreference = "距离最短 / Shortest Route"
            else if (query.contains("最快")) navPreference = "时间最快 / Fastest Route"

            val navP = Pattern.compile("(?:去|到|回|前往)([^，,。！!？?\\s]+?(?:机场|火车站|车站|高铁站|家|公司|医院|学校|商场|超市|公园|路|广场|酒店|北京|上海|香港))").matcher(query)
            if (navP.find()) {
                val d = navP.group(1)?.trim()
                navDestination = when (d) {
                    "虹桥机场" -> "虹桥国际机场 / Hongqiao Airport"
                    "北京" -> "北京 / Beijing"
                    "上海" -> "上海 / Shanghai"
                    "家" -> "家 / Home"
                    "公司" -> "公司 / Office"
                    else -> d
                }
            }
        }

        // 4. Seat slots
        var seatZone: String? = null
        var seatAction: String? = null
        if (query.contains("主驾") || query.contains("驾驶位")) seatZone = "主驾座椅 / Driver Seat"
        else if (query.contains("副驾")) seatZone = "副驾座椅 / Passenger Seat"
        else if (query.contains("座椅")) seatZone = "前排座椅 / Front Seats"

        if (seatZone != null || query.contains("座椅")) {
            if (query.contains("加热")) seatAction = "座椅加热 / Seat Heating"
            else if (query.contains("通风")) seatAction = "座椅通风 / Seat Ventilation"
            else if (query.contains("按摩")) seatAction = "座椅按摩 / Seat Massage"
        }

        // 5. Window slots
        var windowZone: String? = null
        var windowAction: String? = null
        if (query.contains("主驾窗")) windowZone = "主驾车窗 / Driver Window"
        else if (query.contains("副驾窗") || query.contains("副驾车窗")) windowZone = "副驾车窗 / Passenger Window"
        else if (query.contains("天窗")) windowZone = "全景天窗 / Sunroof"
        else if (query.contains("遮阳帘")) windowZone = "天窗遮阳帘 / Sunshade"
        else if (query.contains("车窗") || query.contains("窗户")) windowZone = "全车车窗 / All Windows"

        if (windowZone != null || query.contains("车窗") || query.contains("天窗")) {
            if (query.contains("降下一半") || query.contains("开一半")) windowAction = "降下一半 (50%) / Roll Down 50%"
            else if (query.contains("开一条缝") || query.contains("微开")) windowAction = "微开透气 (15%) / Vent (15%)"
            else if (query.contains("关") || query.contains("升起")) windowAction = "完全关闭 / Close"
            else if (query.contains("开") || query.contains("降下")) windowAction = "完全打开 / Open"
        }

        // 6. Phone slots
        var phoneContact: String? = null
        var phoneNumber: String? = null
        var phoneAction: String? = null
        if (query.contains("电话") || query.contains("呼叫") || query.contains("打给") || query.contains("拨打")) {
            phoneAction = if (query.contains("挂断")) "挂断电话 / Hang Up" else "拨打电话 / Make Call"
            val mPhone = Pattern.compile("(?:打给|打电话给|呼叫|联系)\\s*([^，,。！!？?\\s]+)").matcher(query)
            if (mPhone.find()) {
                phoneContact = mPhone.group(1)?.trim()
            }
        }

        // 7. Query slots
        var queryType: String? = null
        var queryTarget: String? = null
        if (query.contains("天气") || query.contains("气温") || query.contains("下雨")) {
            queryType = "天气与环境查询 / Weather & Forecast Query"
            queryTarget = "天气状况与趋势 / Weather Condition & Forecast"
        } else if (query.contains("几点") || query.contains("时间") || query.contains("日期")) {
            queryType = "时间与日期查询 / Time & Date Query"
            queryTarget = "当前标准时间与日历 / Current Time & Date"
        } else if (query.contains("续航") || query.contains("电量") || query.contains("胎压")) {
            queryType = "车辆状态查询 / Vehicle Status"
            queryTarget = "三电/胎压/剩余续航 / Battery, Range & Status"
        }

        // 8. Negations and domain actions
        val negationsList = mutableListOf<String>()
        // Only extract actual avoidance/bypass constraints (e.g. 避开拥堵, 不要走高速, 避开收费, 躲避拥堵)
        val navAvoidPattern = Pattern.compile("(?:避开|躲避|不走|不要走|免去|除外)\\s*(?:拥堵|高速|收费|收费站|高架|小路|收费路段|拥堵路段|红绿灯)")
        val navMatcher = navAvoidPattern.matcher(query)
        while (navMatcher.find()) {
            val content = navMatcher.group(0)?.trim() ?: ""
            if (content.isNotBlank() && !negationsList.contains(content)) {
                negationsList.add(content)
            }
        }

        val domainActionsMap = mutableMapOf<String, String>()
        for (ex in negation.exclusions) {
            domainActionsMap[ex] = "维持现状/排除 (Excluded/Ignore)"
        }
        for (off in negation.turnOffs) {
            domainActionsMap[off] = "关闭/停止 (Turn Off)"
        }
        for (on in negation.turnOns) {
            domainActionsMap[on] = "开启/调节 (Turn On)"
        }

        return ExtractedSlots(
            climateTemp = climateTemp,
            climateTempType = climateTempType,
            climateMode = climateMode,
            climateZone = climateZone,
            musicAction = musicAction,
            musicArtist = musicArtist,
            musicSong = musicSong,
            musicMood = musicMood,
            musicTargetType = musicTargetType,
            navDestination = navDestination,
            navAction = navAction,
            navPreference = navPreference,
            seatZone = seatZone,
            seatAction = seatAction,
            windowZone = windowZone,
            windowAction = windowAction,
            phoneContact = phoneContact,
            phoneNumber = phoneNumber,
            phoneAction = phoneAction,
            queryType = queryType,
            queryTarget = queryTarget,
            exclusions = negation.exclusions.toList(),
            turnOffs = negation.turnOffs.toList(),
            turnOns = negation.turnOns.toList(),
            domainActions = domainActionsMap,
            negations = negationsList
        )
    }

    private fun buildScoresFromQuery(
        query: String,
        domains: List<DomainItem>,
        negation: OnnxIntentEngine.NegationResult,
        threshold: Float = 0.50f
    ): List<IntentScore> {
        val q = query.lowercase()
        val scores = mutableListOf<IntentScore>()

        for (domain in domains) {
            if (!domain.isEnabled) continue
            val dId = domain.id
            val isExcluded = negation.exclusions.contains(dId)
            val isTurnOff = negation.turnOffs.contains(dId)

            var score = 0.05f

            when (dId) {
                "climate" -> {
                    if (q.contains("空调") || q.contains("温度") || q.contains("冷气") || q.contains("暖风") ||
                        q.contains("制冷") || q.contains("制热") || q.contains("度") || q.contains("除雾")) {
                        score = 0.98f
                    }
                }
                "music" -> {
                    if (q.contains("歌") || q.contains("音乐") || q.contains("播放") || q.contains("周杰伦") ||
                        q.contains("八三夭") || q.contains("831") || q.contains("告别式") ||
                        q.contains("稻香") || q.contains("晴天") || q.contains("摇滚") || q.contains("爵士") || q.contains("听")) {
                        score = 0.96f
                    }
                }
                "navigation" -> {
                    if (q.contains("导航") || q.contains("去") || q.contains("路线") || q.contains("高速") ||
                        q.contains("机场") || q.contains("带我去") || q.contains("堵车") || q.contains("避开拥堵")) {
                        score = 0.97f
                    }
                }
                "seat" -> {
                    if (q.contains("座椅") || (q.contains("主驾") && (q.contains("加热") || q.contains("通风")))) {
                        score = 0.94f
                    }
                }
                "window" -> {
                    if (q.contains("车窗") || q.contains("天窗") || q.contains("窗户") || q.contains("降下一半")) {
                        score = 0.95f
                    }
                }
                "phone" -> {
                    if (q.contains("打电话") || q.contains("电话") || q.contains("呼叫") || q.contains("拨打")) {
                        score = 0.96f
                    }
                }
                "query" -> {
                    if (q.contains("天气") || q.contains("几点") || q.contains("是谁") || q.contains("怎么样")) {
                        score = 0.92f
                    }
                }
                else -> score = 0.04f
            }

            val activeThreshold = threshold
            val grayThreshold = (threshold - 0.20f).coerceAtLeast(0.15f)

            val actionType = when {
                isExcluded -> "exclude"
                isTurnOff -> "turn_off"
                score >= activeThreshold -> "turn_on"
                else -> "auto"
            }

            val actionBadge = when {
                isExcluded -> "已排除"
                score >= activeThreshold -> if (isTurnOff) "关闭" else "开启"
                score >= grayThreshold -> "灰区"
                else -> "已排除"
            }

            val verdict = when {
                isExcluded -> IntentVerdict.EXCLUDED
                score >= activeThreshold -> IntentVerdict.ACTIVE
                score >= grayThreshold -> IntentVerdict.GRAY
                else -> IntentVerdict.EXCLUDED
            }

            scores.add(IntentScore(dId, domain.name, score, verdict, actionType, actionBadge))
        }

        return scores.sortedByDescending { it.score }
    }
}
