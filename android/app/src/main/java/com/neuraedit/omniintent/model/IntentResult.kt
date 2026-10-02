package com.neuraedit.omniintent.model

enum class IntentVerdict {
    ACTIVE,   // 置信度达到阈值，触发执行
    GRAY,     // 灰度置信区间 (0.2 ~ 0.5)
    EXCLUDED  // 负向排除或低于阈值
}

data class IntentScore(
    val domainId: String,
    val domainName: String,
    val score: Float,
    val verdict: IntentVerdict,
    val actionType: String = "auto", // "turn_on", "turn_off", "exclude", "auto"
    val actionBadge: String = ""     // "YES (开)", "YES (关)", "已排除", "EXCLUDED"
)

data class ExtractedSlots(
    // Climate
    val climateTemp: String? = null,
    val climateTempType: String? = null,
    val climateMode: String? = null,
    val climateZone: String? = null,

    // Music matching web version
    val musicAction: String? = null,      // "播放 / Play", "暂停 / Pause", "切到下一首 / Next Track", etc.
    val musicArtist: String? = null,      // "周杰伦 / Jay Chou"
    val musicSong: String? = null,        // "稻香 / Fragrance of Rice"
    val musicMood: String? = null,        // "欢快/提神 / Upbeat & Energetic"
    val musicTargetType: String? = null,  // "指定特定单曲 / Specific Song", "歌手热门精选 / Popular Songs", etc.

    // Navigation
    val navDestination: String? = null,
    val navAction: String? = null,
    val navPreference: String? = null,

    // Seat
    val seatZone: String? = null,
    val seatAction: String? = null,

    // Window
    val windowZone: String? = null,
    val windowAction: String? = null,

    // Phone
    val phoneContact: String? = null,
    val phoneNumber: String? = null,
    val phoneAction: String? = null,

    // Query
    val queryType: String? = null,
    val queryTarget: String? = null,

    // Negation & Actions
    val exclusions: List<String> = emptyList(), // e.g. ["seat"] (维持现状/排除)
    val turnOffs: List<String> = emptyList(),   // e.g. ["climate"] (关闭/停止)
    val turnOns: List<String> = emptyList(),    // e.g. ["music"] (开启/调节)
    val domainActions: Map<String, String> = emptyMap(),
    val negations: List<String> = emptyList()
) {
    val isEmpty: Boolean
        get() = climateTemp == null &&
                climateMode == null &&
                musicSong == null &&
                musicArtist == null &&
                musicAction == null &&
                navDestination == null &&
                seatZone == null &&
                seatAction == null &&
                windowZone == null &&
                phoneContact == null &&
                queryType == null &&
                negations.isEmpty() &&
                exclusions.isEmpty()
}

data class DecisionResult(
    val query: String,
    val wallClockMs: Long,
    val modelComputeMs: Long,
    val tokenCount: Int,
    val engineName: String,
    val isCloud: Boolean,
    val intents: List<IntentScore>,
    val slots: ExtractedSlots,
    val rawJson: String? = null
)
