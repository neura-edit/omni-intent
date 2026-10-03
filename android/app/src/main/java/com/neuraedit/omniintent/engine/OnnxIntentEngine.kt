package com.neuraedit.omniintent.engine

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.neuraedit.omniintent.model.DecisionResult
import com.neuraedit.omniintent.model.DomainItem
import com.neuraedit.omniintent.model.IntentScore
import com.neuraedit.omniintent.model.IntentVerdict
import org.json.JSONObject
import java.io.File
import java.io.InputStreamReader
import kotlin.math.exp
import kotlin.math.max

object OnnxIntentEngine {

    private var ortEnv: OrtEnvironment? = null
    private var ortSession: OrtSession? = null
    private var currentModelPath: String = "/data/local/tmp/decision_eos_int8.ort"

    private var prefixTokens: LongArray = longArrayOf(1905L, 25L, 198L)
    private var padTokenId: Long = 248044L
    private var temperature: Float = 1.0389139f

    // Domain templates: domain_id -> DomainTemplate
    private data class DomainTemplate(
        val suffixTokens: LongArray,
        val candOffsets: IntArray,
        val queryOffset: Int
    )

    private val domainTemplates = mutableMapOf<String, DomainTemplate>()
    private val vocabMap = mutableMapOf<String, LongArray>()

    var isInitialized = false
        private set

    // Domain keyword dictionary matching the production vehicle router
    val DOMAIN_KEYWORDS: Map<String, List<String>> = mapOf(
        "seat" to listOf(
            "座椅加热", "座椅通风", "座椅按摩", "座椅", "加热", "通风", "屁股", "座",
            "座椅加熱", "座椅通風", "通風", "駕駛座", "副駕駛座",
            "seat heater", "seat heating", "heated seat", "heated seats", "seat ventilation",
            "ventilated seat", "ventilated seats", "seat massage", "seat", "seats"
        ),
        "climate" to listOf(
            "空调", "暖气", "暖风", "冷气", "冷风", "除雾", "除霜", "温度", "风量", "外循环", "内循环",
            "制热", "制冷", "太热", "太冷", "热一点", "冷一点", "有点冷", "有点热", "降温", "升温", "吹风",
            "开到", "调到", "度",
            "空調", "暖氣", "暖風", "冷氣", "冷風", "除霧", "溫度", "風量", "外循環", "內循環",
            "製熱", "製冷", "太熱", "熱一點", "有點冷", "有點熱", "降溫", "升溫", "吹風", "開到", "調到", "調至",
            "ac", "a/c", "air condition", "climate", "temperature", "temp", "fan"
        ),
        "window" to listOf(
            "车窗", "天窗", "后排窗", "主驾窗", "副驾窗", "窗户", "开窗", "关窗", "降下", "升起", "留缝",
            "車窗", "後排窗", "主駕窗", "副駕窗", "窗戶", "開窗", "關窗", "留縫", "遮陽簾", "遮阳帘",
            "window", "windows", "sunroof", "moonroof"
        ),
        "music" to listOf(
            "音乐", "歌", "歌曲", "曲子", "曲", "首", "收音机", "广播", "音频", "电台", "听", "放", "唱",
            "點播", "點歌", "點一首", "音樂", "收音機", "廣播", "音頻", "電台", "聽",
            "点播", "播放", "播", "来点", "來點", "周董", "周杰伦", "周杰倫", "陈奕迅", "陳奕迅", "林俊杰", "林俊傑", "邓紫棋", "鄧紫棋", "五月天", "许巍", "許巍",
            "八三夭", "831", "外婆的告别式", "外婆的告別式", "稻香", "晴天", "夜曲", "告白气球", "告白氣球", "七里香", "古典", "爵士", "轻音乐", "輕音樂", "纯音乐", "純音樂", "钢琴", "鋼琴", "摇滚", "搖滾",
            "民谣", "民謠", "古风", "古風", "电音", "電音", "老歌", "切歌", "下一首", "上一首", "别放了", "別放了", "单曲循环", "單曲循環", "随机播放", "隨機播放",
            "放歌", "听歌", "聽歌", "放点音乐", "放點音樂", "来点音乐", "來點音樂", "music", "song", "songs", "track", "tune", "play", "listen"
        ),
        "navigation" to listOf(
            "导航", "路线", "地图", "路况", "目的地", "带我", "回公司", "回家", "怎么走", "堵车", "去哪", "查路线",
            "加油站", "充电桩", "前往", "带我去", "送我到", "开车去", "开车到", "导到", "导去",
            "導航", "路線", "地圖", "路況", "帶我", "怎麼走", "塞車", "充電樁", "帶我去", "開車去", "開車到", "導到", "導去",
            "navigate", "navigation", "gps", "route", "map", "traffic", "destination"
        ),
        "phone" to listOf(
            "电话", "呼叫", "拨号", "联系人", "打给", "接听", "挂断", "接电话", "拨打", "打电话", "致电", "联系",
            "電話", "撥號", "聯絡人", "聯繫人", "打給", "接聽", "掛斷", "接電話", "撥打", "打電話", "致電", "聯繫",
            "call", "dial", "phone", "contact"
        ),
        "query" to listOf(
            "天气", "气温", "下雨", "降雨", "温度如何", "几点", "时间", "星期", "礼拜", "日期",
            "天氣", "氣溫", "幾點", "時間", "禮拜",
            "限行", "尾号", "续航", "电量", "油量", "胎压", "笑话", "百科", "谁", "吗", "怎么样", "如何",
            "尾號", "續航", "電量", "胎壓", "笑話", "誰", "嗎", "怎麼樣",
            "weather", "clock", "date", "battery", "range"
        )
    )

    data class NegationResult(
        val exclusions: Set<String>,
        val turnOffs: Set<String>,
        val turnOns: Set<String>
    )

    private val DOMAIN_EXCLUSION_TARGETS = mapOf(
        "seat" to listOf("座椅加热", "座椅加熱", "座椅通风", "座椅通風", "座椅按摩", "座椅", "主驾座椅", "主駕座椅", "副驾座椅", "副駕座椅", "后排座椅", "後排座椅", "seat", "駕駛座"),
        "climate" to listOf("空调", "空調", "暖气", "暖氣", "暖风", "暖風", "冷气", "冷氣", "冷风", "冷風", "ac", "a/c", "air condition", "climate"),
        "window" to listOf("车窗", "車窗", "天窗", "后排窗", "後排窗", "主驾窗", "主駕窗", "副驾窗", "副駕窗", "窗户", "窗戶", "遮阳帘", "遮陽簾", "window", "sunroof"),
        "music" to listOf("音乐", "音樂", "歌", "歌曲", "收音机", "收音機", "广播", "廣播", "电台", "電台", "播放", "music", "song"),
        "navigation" to listOf("导航", "導航", "路线", "路線", "地图", "地圖", "目的地", "navigation", "route"),
        "phone" to listOf("电话", "電話", "通话", "通話", "呼叫", "phone", "call"),
        "query" to listOf("问答", "問答", "语音助手", "語音助手", "assistant")
    )

    fun analyzeNegation(text: String): NegationResult {
        val clauses = text.split(Regex("[,;!?，；！？]|\\band\\b|\\bbut\\b|\\bthen\\b|并且|並且|但是|然后|然後|同时|同時|顺便|順便|而且|接着|接著"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }

        val exclusions = mutableSetOf<String>()
        val turnOffs = mutableSetOf<String>()
        val turnOns = mutableSetOf<String>()

        val domainOrder = listOf("seat", "window", "climate", "music", "navigation", "phone", "query")

        for (c in clauses) {
            val cClean = c.replace("告别", "").replace("告別", "")
                .replace("特别", "").replace("特別", "")
                .replace("区别", "").replace("區別", "")
                .replace("级别", "").replace("級別", "")
                .replace("别人", "").replace("別人", "")
                .replace("别墅", "").replace("別墅", "")
                .replace("别致", "").replace("別致", "")
                .replace("离别", "").replace("離別", "")
            val cLower = cClean.lowercase()
            // 1. Preservation pattern (e.g. 不要关座椅加热 / 别动天窗 / 保持空调现状 / 不要關座椅加熱 / 別動天窗)
            val hasExclusionCue = cClean.contains("不要") || cClean.contains("别") || cClean.contains("別") ||
                    cClean.contains("不用") || cClean.contains("切勿") || cClean.contains("请勿") || cClean.contains("請勿") ||
                    cLower.contains("don't") || cLower.contains("do not") || cLower.contains("keep") || cLower.contains("maintain")
            val hasActionVerb = cClean.contains("关") || cClean.contains("關") ||
                    cClean.contains("开") || cClean.contains("開") ||
                    cClean.contains("动") || cClean.contains("動") ||
                    cClean.contains("停") || cClean.contains("改") ||
                    cClean.contains("碰") || cClean.contains("调整") || cClean.contains("調整") ||
                    cClean.contains("改变") || cClean.contains("改變") ||
                    cLower.contains("touch") || cLower.contains("turn off") || cLower.contains("close")

            if (hasExclusionCue && hasActionVerb) {
                // Must target the entire domain, NOT sub-parameters like 外循环 / 风量 / 温度
                for (d in domainOrder) {
                    val kws = DOMAIN_EXCLUSION_TARGETS[d] ?: emptyList()
                    if (kws.any { c.lowercase().contains(it.lowercase()) }) {
                        exclusions.add(d)
                        break
                    }
                }
                continue
            }

            // 2. Deactivation pattern (e.g. 关闭空调 / 关掉车窗 / 停止播放 / 關閉空調 / 關掉車窗)
            val hasTurnOffCue = cClean.startsWith("关") || cClean.startsWith("關") ||
                    cClean.startsWith("停") || cClean.startsWith("退出") || cClean.startsWith("取消") ||
                    cClean.endsWith("关掉") || cClean.endsWith("關掉") ||
                    cClean.endsWith("关闭") || cClean.endsWith("關閉") ||
                    cClean.endsWith("停掉") || cClean.endsWith("关了") || cClean.endsWith("關了") ||
                    cLower.startsWith("turn off") || cLower.startsWith("shut down") || cLower.startsWith("stop") || cLower.startsWith("close")
            if (hasTurnOffCue) {
                for (d in domainOrder) {
                    val kws = DOMAIN_EXCLUSION_TARGETS[d] ?: emptyList()
                    if (kws.any { c.lowercase().contains(it.lowercase()) }) {
                        turnOffs.add(d)
                        break
                    }
                }
                continue
            }

            // 3. Positive activation
            for (d in domainOrder) {
                val kws = DOMAIN_KEYWORDS[d] ?: emptyList()
                if (kws.any { c.lowercase().contains(it.lowercase()) }) {
                    turnOns.add(d)
                }
            }
        }

        // Positive commands in the same utterance always dominate negative preservation or deactivation
        exclusions.removeAll(turnOns)
        turnOffs.removeAll(turnOns)

        return NegationResult(exclusions, turnOffs, turnOns)
    }

    fun extractCandidateDomains(text: String, domains: List<DomainItem>): List<DomainItem> {
        val textLower = text.lowercase()
        val matchedIds = mutableSetOf<String>()

        for ((domainId, kws) in DOMAIN_KEYWORDS) {
            if (kws.any { textLower.contains(it.lowercase()) }) {
                matchedIds.add(domainId)
            }
        }

        // Additional navigation heuristics (e.g. 去上海虹桥火车站, 前往...)
        if (Regex("(?:我想|我要|帮我|请)?(?:去|到|回|前往)[\\u4e00-\\u9fa5]{2,15}").containsMatchIn(textLower) &&
            !Regex("(?:调到|升到|降到|吹到|开到)\\s*[0-9一二两三四五六七八九十]+度?").containsMatchIn(textLower)) {
            matchedIds.add("navigation")
        }

        return domains.filter { it.isEnabled && matchedIds.contains(it.id) && domainTemplates.containsKey(it.id) }
    }

    fun resolveModelPath(preferredPath: String = currentModelPath): String {
        val ortCandidate = File("/data/local/tmp/decision_eos_int8.ort")
        if (ortCandidate.exists() && ortCandidate.canRead() && ortCandidate.length() > 1000) {
            return ortCandidate.absolutePath
        }
        val onnxCandidate = File("/data/local/tmp/decision_eos_int8.onnx")
        if (onnxCandidate.exists() && onnxCandidate.canRead() && onnxCandidate.length() > 1000) {
            return onnxCandidate.absolutePath
        }
        return preferredPath
    }

    fun isModelFileAvailable(path: String = currentModelPath): Boolean {
        val target = resolveModelPath(path)
        val f = File(target)
        return f.exists() && f.canRead() && f.length() > 1000
    }

    @Synchronized
    fun init(context: Context, modelPath: String = currentModelPath): Boolean {
        try {
            val resolved = resolveModelPath(modelPath)
            currentModelPath = resolved
            loadAssets(context)

            if (!isModelFileAvailable(resolved)) {
                return false
            }

            if (ortEnv == null) {
                ortEnv = OrtEnvironment.getEnvironment()
            }

            val env = ortEnv ?: return false
            val sessionOpts = OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(4)
                setOptimizationLevel(OrtSession.SessionOptions.OptLevel.BASIC_OPT)
                addConfigEntry("session.use_env_allocators", "1")
            }

            ortSession?.close()
            ortSession = env.createSession(resolved, sessionOpts)
            isInitialized = true
            return true
        } catch (e: Throwable) {
            e.printStackTrace()
            isInitialized = false
            return false
        }
    }

    /**
     * Executes a true dummy forward pass through the ONNX graph.
     * This forces ONNX Runtime to initialize memory arena allocators, threadpools,
     * and compile runtime execution kernels during the loading animation,
     * so that the user's first real command executes in ~140ms with zero freeze.
     */
    @Synchronized
    fun warmup(context: Context): Long {
        if (!isInitialized) {
            init(context, currentModelPath)
        }
        val session = ortSession ?: return 0L
        val env = ortEnv ?: return 0L
        if (domainTemplates.isEmpty()) return 0L

        val start = System.currentTimeMillis()
        try {
            val dummyQuery = "音乐"
            val queryTokenIds = tokenize(dummyQuery)
            val textLen = queryTokenIds.size
            val dKey = domainTemplates.keys.first()
            val tmpl = domainTemplates[dKey] ?: return 0L

            val rowTokens = LongArray(prefixTokens.size + textLen + tmpl.suffixTokens.size)
            System.arraycopy(prefixTokens, 0, rowTokens, 0, prefixTokens.size)
            System.arraycopy(queryTokenIds, 0, rowTokens, prefixTokens.size, textLen)
            System.arraycopy(tmpl.suffixTokens, 0, rowTokens, prefixTokens.size + textLen, tmpl.suffixTokens.size)

            val padTo = 64
            val batchIds = Array(1) { LongArray(padTo) { padTokenId } }
            System.arraycopy(rowTokens, 0, batchIds[0], 0, rowTokens.size)

            val rowsQueryPos = LongArray(1) { (prefixTokens.size + textLen + tmpl.queryOffset).toLong() }
            val rowsCandPos = Array(1) {
                longArrayOf(
                    (prefixTokens.size + textLen + tmpl.candOffsets[0]).toLong(),
                    (prefixTokens.size + textLen + tmpl.candOffsets[1]).toLong()
                )
            }

            val tInputIds = OnnxTensor.createTensor(env, batchIds)
            val tQueryPos = OnnxTensor.createTensor(env, rowsQueryPos)
            val tCandPos = OnnxTensor.createTensor(env, rowsCandPos)

            val inputs = mapOf(
                "input_ids" to tInputIds,
                "query_pos" to tQueryPos,
                "cand_pos" to tCandPos
            )

            val results = session.run(inputs)
            tInputIds.close()
            tQueryPos.close()
            tCandPos.close()
            results.close()

            return System.currentTimeMillis() - start
        } catch (e: Throwable) {
            e.printStackTrace()
            return -1L
        }
    }

    private fun loadAssets(context: Context) {
        if (domainTemplates.isNotEmpty() && vocabMap.isNotEmpty()) return

        try {
            context.assets.open("domain_templates.json").use { stream ->
                val json = JSONObject(InputStreamReader(stream, "UTF-8").readText())
                val prefixArr = json.getJSONArray("prefix_tokens")
                val pTokens = LongArray(prefixArr.length()) { prefixArr.getLong(it) }
                prefixTokens = pTokens
                padTokenId = json.optLong("pad_token_id", 248044L)
                temperature = json.optDouble("temperature", 1.0389139).toFloat()

                val domainsObj = json.getJSONObject("domains")
                val keys = domainsObj.keys()
                while (keys.hasNext()) {
                    val dKey = keys.next()
                    val dObj = domainsObj.getJSONObject(dKey)
                    val sArr = dObj.getJSONArray("suffix_tokens")
                    val sTokens = LongArray(sArr.length()) { sArr.getLong(it) }

                    val cArr = dObj.getJSONArray("cand_offsets")
                    val cOffsets = IntArray(cArr.length()) { cArr.getInt(it) }
                    val qOffset = dObj.getInt("query_offset")

                    domainTemplates[dKey] = DomainTemplate(sTokens, cOffsets, qOffset)
                }
            }

            context.assets.open("tokenizer_vocab.json").use { stream ->
                val json = JSONObject(InputStreamReader(stream, "UTF-8").readText())
                val keys = json.keys()
                while (keys.hasNext()) {
                    val k = keys.next()
                    val arr = json.getJSONArray(k)
                    val ids = LongArray(arr.length()) { arr.getLong(it) }
                    vocabMap[k] = ids
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun tokenize(text: String): LongArray {
        val result = mutableListOf<Long>()
        var i = 0
        while (i < text.length) {
            var matched = false
            val maxLen = minOf(4, text.length - i)
            for (len in maxLen downTo 2) {
                val sub = text.substring(i, i + len)
                val ids = vocabMap[sub]
                if (ids != null) {
                    ids.forEach { result.add(it) }
                    i += len
                    matched = true
                    break
                }
            }
            if (!matched) {
                val single = text.substring(i, i + 1)
                val ids = vocabMap[single]
                if (ids != null) {
                    ids.forEach { result.add(it) }
                }
                i += 1
            }
        }
        return result.toLongArray()
    }

    fun runInference(
        context: Context,
        query: String,
        domains: List<DomainItem>,
        startWallTime: Long,
        threshold: Float = 0.50f
    ): DecisionResult {
        if (!isInitialized) {
            init(context, currentModelPath)
        }

        val session = ortSession ?: throw IllegalStateException("ONNX Runtime session not initialized")
        val env = ortEnv ?: throw IllegalStateException("ONNX Runtime environment null")

        val computeStart = System.currentTimeMillis()

        // 1. Analyze Negation & Extract Candidate Domains
        val negation = analyzeNegation(query)
        val candidates = extractCandidateDomains(query, domains)

        // Dynamic Candidate Routing:
        // If candidates are detected, ONLY run the Transformer on relevant candidate domains (B = 1 or 2)!
        // If no candidate is detected, fallback to all enabled domains that have templates.
        val activeDomains = if (candidates.isNotEmpty()) {
            candidates
        } else {
            domains.filter { it.isEnabled && domainTemplates.containsKey(it.id) }
        }
        val dKeys = activeDomains.map { it.id }
        val B = dKeys.size

        val queryTokenIds = tokenize(query)
        val textLen = queryTokenIds.size

        val rowsTokens = mutableListOf<LongArray>()
        val rowsQueryPos = LongArray(B)
        val rowsCandPos = Array(B) { LongArray(2) }

        var maxLen = 0
        for (idx in 0 until B) {
            val dKey = dKeys[idx]
            val tmpl = domainTemplates[dKey]!!

            val rowTokens = LongArray(prefixTokens.size + textLen + tmpl.suffixTokens.size)
            System.arraycopy(prefixTokens, 0, rowTokens, 0, prefixTokens.size)
            System.arraycopy(queryTokenIds, 0, rowTokens, prefixTokens.size, textLen)
            System.arraycopy(tmpl.suffixTokens, 0, rowTokens, prefixTokens.size + textLen, tmpl.suffixTokens.size)

            val baseOffset = prefixTokens.size + textLen
            rowsQueryPos[idx] = (baseOffset + tmpl.queryOffset).toLong()
            rowsCandPos[idx][0] = (baseOffset + tmpl.candOffsets[0]).toLong()
            rowsCandPos[idx][1] = (baseOffset + tmpl.candOffsets[1]).toLong()

            rowsTokens.add(rowTokens)
            if (rowTokens.size > maxLen) {
                maxLen = rowTokens.size
            }
        }

        val padTo = ((maxLen + 63) / 64) * 64
        val batchIds = Array(B) { LongArray(padTo) { padTokenId } }
        for (i in 0 until B) {
            val src = rowsTokens[i]
            System.arraycopy(src, 0, batchIds[i], 0, src.size)
        }

        // Create ONNX Tensors and Run Forward Inference
        val tensorInputIds = OnnxTensor.createTensor(env, batchIds)
        val tensorQueryPos = OnnxTensor.createTensor(env, rowsQueryPos)
        val tensorCandPos = OnnxTensor.createTensor(env, rowsCandPos)

        val inputs = mapOf(
            "input_ids" to tensorInputIds,
            "query_pos" to tensorQueryPos,
            "cand_pos" to tensorCandPos
        )

        val results = session.run(inputs)
        val computeEnd = System.currentTimeMillis()
        val computeMs = computeEnd - computeStart

        @Suppress("UNCHECKED_CAST")
        val logits = results[0].value as Array<FloatArray>

        tensorInputIds.close()
        tensorQueryPos.close()
        tensorCandPos.close()
        results.close()

        val evaluatedScores = mutableMapOf<String, Float>()
        for (i in 0 until B) {
            val dId = dKeys[i]
            val l0 = logits[i][0] / temperature
            val l1 = logits[i][1] / temperature
            val maxL = max(l0, l1)
            val e0 = exp(l0 - maxL)
            val e1 = exp(l1 - maxL)
            val prob1 = e1 / (e0 + e1)
            evaluatedScores[dId] = prob1
        }

        val intentScores = mutableListOf<IntentScore>()
        for (domain in domains) {
            if (!domain.isEnabled) continue
            val dId = domain.id
            val dName = domain.name
            val isExcluded = negation.exclusions.contains(dId)
            val isTurnOff = negation.turnOffs.contains(dId)
            val prob = evaluatedScores[dId]

            val activeThreshold = if (candidates.isNotEmpty()) threshold else (threshold + 0.15f).coerceAtMost(0.95f)
            val grayThreshold = (threshold - 0.20f).coerceAtLeast(0.15f)

            val actionType = when {
                isExcluded -> "exclude"
                isTurnOff -> "turn_off"
                (prob ?: 0f) >= activeThreshold -> "turn_on"
                else -> "auto"
            }

            val (verdict, actionBadge) = when {
                isExcluded -> Pair(IntentVerdict.EXCLUDED, "已排除")
                prob != null && prob >= activeThreshold -> {
                    val badge = if (isTurnOff) "关闭" else "开启"
                    Pair(IntentVerdict.ACTIVE, badge)
                }
                prob != null && prob >= grayThreshold -> Pair(IntentVerdict.GRAY, "灰区")
                else -> Pair(IntentVerdict.EXCLUDED, "已排除")
            }

            val finalScore = if (isExcluded) (prob ?: 0.05f) else (prob ?: 0.02f)
            intentScores.add(IntentScore(dId, dName, finalScore, verdict, actionType, actionBadge))
        }

        val endWallTime = System.currentTimeMillis()
        val wallClockMs = endWallTime - startWallTime

        val slots = OmniIntentEngine.extractLocalSlots(query, negation)

        return DecisionResult(
            query = query,
            wallClockMs = wallClockMs,
            modelComputeMs = computeMs,
            tokenCount = queryTokenIds.size + 16,
            engineName = "On-Device 0.75B INT8 (Gated ONNX)",
            isCloud = false,
            intents = intentScores.sortedByDescending { it.score },
            slots = slots
        )
    }
}
