package com.neuraedit.omniintent.ui.execute

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.SuggestionChipDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.neuraedit.omniintent.i18n.AppLanguage
import com.neuraedit.omniintent.i18n.AppStrings
import com.neuraedit.omniintent.i18n.LocalizedStrings
import com.neuraedit.omniintent.model.DecisionResult
import com.neuraedit.omniintent.model.ExtractedSlots
import com.neuraedit.omniintent.model.IntentScore
import com.neuraedit.omniintent.model.IntentVerdict
import com.neuraedit.omniintent.ui.OmniViewModel

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun CommandScreen(
    viewModel: OmniViewModel,
    onNavigateToAbout: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val query by viewModel.query.collectAsStateWithLifecycle()
    val engineMode by viewModel.engineMode.collectAsStateWithLifecycle()
    val lastResult by viewModel.lastResult.collectAsStateWithLifecycle()
    val isLoading by viewModel.isLoading.collectAsStateWithLifecycle()
    val errorMessage by viewModel.errorMessage.collectAsStateWithLifecycle()
    val appLanguage by viewModel.appLanguage.collectAsStateWithLifecycle()
    val decisionThreshold by viewModel.decisionThreshold.collectAsStateWithLifecycle()

    val currentLang = appLanguage ?: AppLanguage.ZH
    val strings = AppStrings.get(currentLang)
    val presetQueries = strings.presets

    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        // Subtle Brand & Mode Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                onClick = onNavigateToAbout,
                shape = RoundedCornerShape(6.dp),
                color = MaterialTheme.colorScheme.primaryContainer,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.35f))
            ) {
                Text(
                    text = "N/E",
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                    fontWeight = FontWeight.Black,
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            Column {
                Text(
                    text = strings.appTitle,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                    letterSpacing = 0.8.sp
                )
                Text(
                    text = strings.appSubtitle,
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            val (badgeLabel, badgeColor, borderColor) = when (engineMode) {
                com.neuraedit.omniintent.data.EngineMode.LOCAL_ONNX -> Triple(strings.engineOnDeviceBadge, Color(0xFF7C3AED), Color(0xFF8B5CF6))
                com.neuraedit.omniintent.data.EngineMode.CLOUD_NEURAL -> Triple(strings.engineCloudBadge, Color(0xFF2563EB), Color(0xFF3B82F6))
                else -> Triple(strings.engineOnDeviceBadge, Color(0xFF7C3AED), Color(0xFF8B5CF6))
            }

            Surface(
                shape = RoundedCornerShape(12.dp),
                color = badgeColor.copy(alpha = 0.12f),
                border = BorderStroke(1.dp, borderColor)
            ) {
                Text(
                    text = badgeLabel,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = badgeColor
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Preset Prompt Chips
        Text(
            text = strings.presetTitle,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(6.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            presetQueries.forEach { preset ->
                SuggestionChip(
                    onClick = { viewModel.runPresetQuery(preset) },
                    label = { Text(preset, fontSize = 12.sp) },
                    colors = SuggestionChipDefaults.suggestionChipColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                    ),
                    border = BorderStroke(0.5.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.25f))
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Input Box
        OutlinedTextField(
            value = query,
            onValueChange = { viewModel.updateQuery(it) },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text(strings.inputPlaceholder, fontSize = 13.sp) },
            singleLine = false,
            maxLines = 3,
            trailingIcon = {
                if (query.isNotEmpty()) {
                    IconButton(onClick = { viewModel.updateQuery("") }) {
                        Text(
                            text = "✕",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            },
            keyboardOptions = KeyboardOptions.Default.copy(
                imeAction = ImeAction.Done
            ),
            keyboardActions = KeyboardActions(
                onDone = { viewModel.executeDecision() }
            ),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)
            ),
            shape = RoundedCornerShape(10.dp)
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Action Button
        Button(
            onClick = { viewModel.executeDecision() },
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            enabled = query.isNotBlank() && !isLoading,
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary
            )
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(strings.btnExecuting, fontSize = 14.sp)
            } else {
                Text(strings.btnExecute, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            }
        }

        if (errorMessage != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "⚠️ $errorMessage",
                color = MaterialTheme.colorScheme.error,
                fontSize = 12.sp
            )
        }

        // Decision Results Section
        lastResult?.let { result ->
            Spacer(modifier = Modifier.height(16.dp))

            // 0. High-level Decision Verdict Tag Banner
            val activeIntents = result.intents.filter { it.verdict == IntentVerdict.ACTIVE }
            val verdictSummary = when {
                activeIntents.size >= 2 -> {
                    val label = activeIntents.joinToString(" + ") {
                        val act = if (it.actionType == "turn_off") " · ${strings.badgeYesOff}" else if (it.actionType == "turn_on") " · ${strings.badgeYesOn}" else ""
                        val dName = AppStrings.getLocalizedDomainName(it.domainId, it.domainName, currentLang)
                        "$dName$act"
                    }
                    strings.multiCommandBanner(label)
                }
                activeIntents.size == 1 -> {
                    val act = if (activeIntents[0].actionType == "turn_off") strings.badgeYesOff else strings.badgeYesOn
                    val dName = AppStrings.getLocalizedDomainName(activeIntents[0].domainId, activeIntents[0].domainName, currentLang)
                    strings.singleCommandBanner(dName, act)
                }
                result.slots.exclusions.isNotEmpty() -> when (currentLang) {
                    AppLanguage.ZH -> "否定维持 · 阻断执行"
                    AppLanguage.ZHTW -> "否定維持 · 阻斷執行"
                    AppLanguage.EN -> "Negation Hold · Blocked"
                }
                else -> when (currentLang) {
                    AppLanguage.ZH -> "兜底 · 未明确触发"
                    AppLanguage.ZHTW -> "兜底 · 未明確觸發"
                    AppLanguage.EN -> "Fallback · No Trigger"
                }
            }

            Surface(
                shape = RoundedCornerShape(8.dp),
                color = if (activeIntents.isNotEmpty()) Color(0xFF3B82F6).copy(alpha = 0.1f) else Color(0xFF6B7280).copy(alpha = 0.1f),
                border = BorderStroke(1.dp, if (activeIntents.isNotEmpty()) Color(0xFF3B82F6).copy(alpha = 0.4f) else Color(0xFF6B7280).copy(alpha = 0.3f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "🚀 $verdictSummary",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (activeIntents.isNotEmpty()) Color(0xFF1D4ED8) else Color(0xFF374151)
                    )
                    if (result.slots.exclusions.isNotEmpty()) {
                        Spacer(modifier = Modifier.width(6.dp))
                        val holdPrefix = when (currentLang) {
                            AppLanguage.ZH -> "维持: "
                            AppLanguage.ZHTW -> "維持: "
                            AppLanguage.EN -> "Hold: "
                        }
                        val exText = result.slots.exclusions.joinToString { AppStrings.getLocalizedDomainName(it, it, currentLang) }
                        Text(
                            text = "· $holdPrefix$exText",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFFDC2626)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 1. Telemetry Bar
            TelemetryMetricCard(result, strings)

            Spacer(modifier = Modifier.height(12.dp))

            // 2. Intent Verdicts & Probability Distribution
            val thresholdPct = (decisionThreshold * 100).toInt()
            IntentDistributionCard(result.intents, strings, thresholdPct, currentLang)

            // 3. Slot Extraction
            if (!result.slots.isEmpty) {
                Spacer(modifier = Modifier.height(12.dp))
                SlotBreakdownCard(result.slots, strings, currentLang)
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun TelemetryMetricCard(result: DecisionResult, strings: LocalizedStrings) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)
        ),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "📊 ${strings.metricsTitle}",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = result.engineName,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.4f))
            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                MetricItem(label = strings.metricWallClock, value = "${result.wallClockMs} ms", isHighlight = true)
                MetricItem(label = strings.metricInference, value = "${result.modelComputeMs} ms")
                MetricItem(label = strings.metricTokens, value = "${result.tokenCount} tok")
                MetricItem(label = strings.metricActive, value = "${result.intents.count { it.verdict == IntentVerdict.ACTIVE }}")
            }
        }
    }
}

@Composable
private fun MetricItem(label: String, value: String, isHighlight: Boolean = false) {
    Column {
        Text(text = label, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(modifier = Modifier.height(2.dp))
        Text(
            text = value,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            color = if (isHighlight) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
private fun IntentDistributionCard(
    intents: List<IntentScore>,
    strings: LocalizedStrings,
    thresholdPercent: Int,
    language: AppLanguage
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "🎯 ${strings.intentsTitle}",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = strings.thresholdLabel(thresholdPercent),
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            intents.forEach { item ->
                val progress = item.score.coerceIn(0f, 1f)
                val percentText = "${(item.score * 100).toInt()}%"

                val (badgeText, badgeBg, badgeTextColor) = when (item.verdict) {
                    IntentVerdict.ACTIVE -> {
                        val badge = if (item.actionType == "turn_off") strings.badgeYesOff else strings.badgeYesOn
                        val color = if (item.actionType == "turn_off") Color(0xFFDC2626) else Color(0xFF059669)
                        Triple(badge, color.copy(alpha = 0.15f), color)
                    }
                    IntentVerdict.GRAY -> Triple(strings.badgeGray, Color(0xFFF59E0B).copy(alpha = 0.15f), Color(0xFFD97706))
                    IntentVerdict.EXCLUDED -> Triple(strings.badgeExcluded, Color(0xFF6B7280).copy(alpha = 0.1f), Color(0xFF6B7280))
                }

                val localizedDomain = AppStrings.getLocalizedDomainName(item.domainId, item.domainName, language)

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = localizedDomain,
                        fontSize = 12.sp,
                        fontWeight = if (item.verdict == IntentVerdict.ACTIVE) FontWeight.Bold else FontWeight.Normal,
                        color = if (item.verdict == IntentVerdict.ACTIVE) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.width(92.dp)
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    LinearProgressIndicator(
                        progress = { progress },
                        modifier = Modifier
                            .weight(1f)
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = when (item.verdict) {
                            IntentVerdict.ACTIVE -> MaterialTheme.colorScheme.primary
                            IntentVerdict.GRAY -> Color(0xFFF59E0B)
                            IntentVerdict.EXCLUDED -> MaterialTheme.colorScheme.outlineVariant
                        },
                        trackColor = MaterialTheme.colorScheme.surfaceVariant
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    Text(
                        text = percentText,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.width(36.dp)
                    )

                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = badgeBg
                    ) {
                        Text(
                            text = badgeText,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = badgeTextColor,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SlotBreakdownCard(
    slots: ExtractedSlots,
    strings: LocalizedStrings,
    language: AppLanguage
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = "🧩 ${strings.slotsTitle}",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = strings.slotsSubtitle,
                fontSize = 10.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(10.dp))

            // 1. Exclusions / Negation banner
            if (slots.exclusions.isNotEmpty()) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFDC2626).copy(alpha = 0.08f),
                    border = BorderStroke(1.dp, Color(0xFFDC2626).copy(alpha = 0.35f)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val exclusionHeader = when (language) {
                                AppLanguage.ZH -> "⏸️ 语义否定与维持现状"
                                AppLanguage.ZHTW -> "⏸️ 語義否定與維持現狀"
                                AppLanguage.EN -> "⏸️ Negation & State Hold"
                            }
                            Text(
                                text = exclusionHeader,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFDC2626)
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        slots.exclusions.forEach { ex ->
                            val label = when (ex) {
                                "seat" -> when (language) {
                                    AppLanguage.ZH -> "座椅调节 · 保持原位不关闭加热"
                                    AppLanguage.ZHTW -> "座椅調節 · 保持原位不關閉加熱"
                                    AppLanguage.EN -> "Seat Comfort · Maintain heating state"
                                }
                                "climate" -> when (language) {
                                    AppLanguage.ZH -> "空调系统 · 保持原设定不改变"
                                    AppLanguage.ZHTW -> "空調系統 · 保持原設定不改變"
                                    AppLanguage.EN -> "Climate · Keep current temperature"
                                }
                                "window" -> when (language) {
                                    AppLanguage.ZH -> "车窗天窗 · 维持原样不开窗"
                                    AppLanguage.ZHTW -> "車窗天窗 · 維持原樣不開窗"
                                    AppLanguage.EN -> "Windows · Keep current state"
                                }
                                "music" -> when (language) {
                                    AppLanguage.ZH -> "媒体音乐 · 维持播放不切歌"
                                    AppLanguage.ZHTW -> "媒體音樂 · 維持播放不切歌"
                                    AppLanguage.EN -> "Media · Continue current track"
                                }
                                "navigation" -> when (language) {
                                    AppLanguage.ZH -> "导航路线 · 不重新规划"
                                    AppLanguage.ZHTW -> "導航路線 · 不重新規劃"
                                    AppLanguage.EN -> "Navigation · Keep current route"
                                }
                                else -> AppStrings.getLocalizedDomainName(ex, ex, language)
                            }
                            val prefix = when (language) {
                                AppLanguage.ZH -> "• 维持现状 · "
                                AppLanguage.ZHTW -> "• 維持現狀 · "
                                AppLanguage.EN -> "• Hold state · "
                            }
                            Text(
                                text = "$prefix$label",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color(0xFFB91C1C)
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            // 2. Avoidance Constraints
            if (slots.negations.isNotEmpty()) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFF59E0B).copy(alpha = 0.08f),
                    border = BorderStroke(1.dp, Color(0xFFF59E0B).copy(alpha = 0.35f)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = strings.slotNegationPrefix, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFFD97706))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            slots.negations.forEach { neg ->
                                val cleanNeg = AppStrings.localizeSlotValue(neg, language)
                                Surface(
                                    shape = RoundedCornerShape(4.dp),
                                    color = Color(0xFFF59E0B).copy(alpha = 0.15f)
                                ) {
                                    Text(
                                        text = cleanNeg,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = Color(0xFFB45309),
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                            }
                        }
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            // 3. Climate slots
            if (slots.climateTemp != null || slots.climateMode != null || slots.climateZone != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "🌡️ 空调控制槽位"
                    AppLanguage.ZHTW -> "🌡️ 空調控制槽位"
                    AppLanguage.EN -> "🌡️ Climate Control Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.climateTemp?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "设定温度"
                                AppLanguage.ZHTW -> "設定溫度"
                                AppLanguage.EN -> "Target Temp"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.climateTempType?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "调节类型"
                                AppLanguage.ZHTW -> "調節類型"
                                AppLanguage.EN -> "Adjustment"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.climateMode?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "运转模式"
                                AppLanguage.ZHTW -> "運轉模式"
                                AppLanguage.EN -> "A/C Mode"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.climateZone?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "控制区域"
                                AppLanguage.ZHTW -> "控制區域"
                                AppLanguage.EN -> "Zone"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 4. Music slots
            if (slots.musicSong != null || slots.musicArtist != null || slots.musicAction != null || slots.musicMood != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "🎵 媒体音乐槽位"
                    AppLanguage.ZHTW -> "🎵 媒體音樂槽位"
                    AppLanguage.EN -> "🎵 Media & Music Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.musicArtist?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "歌手偏好"
                                AppLanguage.ZHTW -> "歌手偏好"
                                AppLanguage.EN -> "Artist"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.musicSong?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "点播目标"
                                AppLanguage.ZHTW -> "點播目標"
                                AppLanguage.EN -> "Song Title"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.musicMood?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "曲风偏好"
                                AppLanguage.ZHTW -> "曲風偏好"
                                AppLanguage.EN -> "Genre & Mood"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.musicAction?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "控制动作"
                                AppLanguage.ZHTW -> "控制動作"
                                AppLanguage.EN -> "Action"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.musicTargetType?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "推荐定位"
                                AppLanguage.ZHTW -> "推薦定位"
                                AppLanguage.EN -> "Target Type"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 5. Navigation slots
            if (slots.navDestination != null || slots.navPreference != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "🧭 导航地图槽位"
                    AppLanguage.ZHTW -> "🧭 導航地圖槽位"
                    AppLanguage.EN -> "🧭 Navigation Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.navDestination?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "目的地"
                                AppLanguage.ZHTW -> "目的地"
                                AppLanguage.EN -> "Destination"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.navAction?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "导航动作"
                                AppLanguage.ZHTW -> "導航動作"
                                AppLanguage.EN -> "Action"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.navPreference?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "路线偏好"
                                AppLanguage.ZHTW -> "路線偏好"
                                AppLanguage.EN -> "Route Preference"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 6. Seat slots
            if (slots.seatZone != null || slots.seatAction != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "💺 座椅控制槽位"
                    AppLanguage.ZHTW -> "💺 座椅控制槽位"
                    AppLanguage.EN -> "💺 Seat Comfort Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.seatZone?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "调节位置"
                                AppLanguage.ZHTW -> "調節位置"
                                AppLanguage.EN -> "Seat Zone"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.seatAction?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "动作指令"
                                AppLanguage.ZHTW -> "動作指令"
                                AppLanguage.EN -> "Action"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 7. Window slots
            if (slots.windowZone != null || slots.windowAction != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "🪟 车窗天窗槽位"
                    AppLanguage.ZHTW -> "🪟 車窗天窗槽位"
                    AppLanguage.EN -> "🪟 Window Control Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.windowZone?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "目标车窗"
                                AppLanguage.ZHTW -> "目標車窗"
                                AppLanguage.EN -> "Window Zone"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.windowAction?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "动作幅度"
                                AppLanguage.ZHTW -> "動作幅度"
                                AppLanguage.EN -> "Action"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 8. Phone slots
            if (slots.phoneContact != null || slots.phoneNumber != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "📞 车载电话槽位"
                    AppLanguage.ZHTW -> "📞 車載電話槽位"
                    AppLanguage.EN -> "📞 Phone Call Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.phoneContact?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "联系人"
                                AppLanguage.ZHTW -> "聯絡人"
                                AppLanguage.EN -> "Contact"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.phoneNumber?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "呼叫号码"
                                AppLanguage.ZHTW -> "呼叫號碼"
                                AppLanguage.EN -> "Phone Number"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.phoneAction?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "通话动作"
                                AppLanguage.ZHTW -> "通話動作"
                                AppLanguage.EN -> "Action"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
                Spacer(modifier = Modifier.height(6.dp))
            }

            // 9. Query slots
            if (slots.queryType != null || slots.queryTarget != null) {
                val groupTitle = when (language) {
                    AppLanguage.ZH -> "💬 通用问答槽位"
                    AppLanguage.ZHTW -> "💬 通用問答槽位"
                    AppLanguage.EN -> "💬 General Q&A Slots"
                }
                SlotGroupCard(
                    title = groupTitle,
                    items = listOfNotNull(
                        slots.queryType?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "查询类别"
                                AppLanguage.ZHTW -> "查詢類別"
                                AppLanguage.EN -> "Query Type"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        },
                        slots.queryTarget?.let {
                            val label = when (language) {
                                AppLanguage.ZH -> "查询目标"
                                AppLanguage.ZHTW -> "查詢目標"
                                AppLanguage.EN -> "Query Target"
                            }
                            label to AppStrings.localizeSlotValue(it, language)
                        }
                    )
                )
            }
        }
    }
}

@Composable
private fun SlotGroupCard(title: String, items: List<Pair<String, String>>) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Text(text = title, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.height(6.dp))
            items.forEach { (label, value) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = label, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(text = value, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
                }
            }
        }
    }
}
