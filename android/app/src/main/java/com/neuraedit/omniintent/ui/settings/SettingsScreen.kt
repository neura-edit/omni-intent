package com.neuraedit.omniintent.ui.settings

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.neuraedit.omniintent.data.EngineMode
import com.neuraedit.omniintent.i18n.AppLanguage
import com.neuraedit.omniintent.i18n.AppStrings
import com.neuraedit.omniintent.model.DomainItem
import com.neuraedit.omniintent.ui.OmniViewModel

@Composable
fun SettingsScreen(
    viewModel: OmniViewModel,
    onNavigateToAbout: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val domains by viewModel.domains.collectAsStateWithLifecycle()
    val engineMode by viewModel.engineMode.collectAsStateWithLifecycle()
    val modelPath by viewModel.modelPath.collectAsStateWithLifecycle()
    val cloudEndpoint by viewModel.cloudEndpoint.collectAsStateWithLifecycle()
    val appLanguage by viewModel.appLanguage.collectAsStateWithLifecycle()
    val decisionThreshold by viewModel.decisionThreshold.collectAsStateWithLifecycle()

    val currentLang = appLanguage ?: AppLanguage.ZH
    val strings = AppStrings.get(currentLang)

    var endpointInput by remember(cloudEndpoint) { mutableStateOf(cloudEndpoint) }
    var modelPathInput by remember(modelPath) { mutableStateOf(modelPath) }

    // Add Domain Form states
    var newId by remember { mutableStateOf("") }
    var newName by remember { mutableStateOf("") }
    var newDesc by remember { mutableStateOf("") }
    var newMultiLabel by remember { mutableStateOf(true) }

    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        // Minimalist Header
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

            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = strings.settingsTitle,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    letterSpacing = 0.8.sp
                )
                Text(
                    text = strings.settingsSubtitle,
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 1. Language Selection Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = strings.languageSectionTitle,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    LanguagePill(
                        title = "简体中文",
                        isSelected = currentLang == AppLanguage.ZH,
                        onClick = { viewModel.setAppLanguage(AppLanguage.ZH) },
                        modifier = Modifier.weight(1f)
                    )
                    LanguagePill(
                        title = "繁體中文",
                        isSelected = currentLang == AppLanguage.ZHTW,
                        onClick = { viewModel.setAppLanguage(AppLanguage.ZHTW) },
                        modifier = Modifier.weight(1f)
                    )
                    LanguagePill(
                        title = "English",
                        isSelected = currentLang == AppLanguage.EN,
                        onClick = { viewModel.setAppLanguage(AppLanguage.EN) },
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 2. Engine Running Mode
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = strings.engineModeSectionTitle,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))

                // Mode Option 1: LOCAL_ONNX (Removed "车机", left "在设备本地 CPU 运行真实 1.9GB 神经网络张量计算")
                EngineModeOptionCard(
                    title = strings.optionOnDeviceTitle,
                    subtitle = strings.optionOnDeviceSubtitle,
                    isSelected = engineMode == EngineMode.LOCAL_ONNX,
                    onSelect = { viewModel.setEngineMode(EngineMode.LOCAL_ONNX) }
                )

                Spacer(modifier = Modifier.height(6.dp))

                // Mode Option 2: CLOUD_NEURAL (Option 2 LOCAL_EMBEDDED removed as requested)
                EngineModeOptionCard(
                    title = strings.optionCloudTitle,
                    subtitle = strings.optionCloudSubtitle,
                    isSelected = engineMode == EngineMode.CLOUD_NEURAL,
                    onSelect = { viewModel.setEngineMode(EngineMode.CLOUD_NEURAL) }
                )

                // Extra config for LOCAL_ONNX
                if (engineMode == EngineMode.LOCAL_ONNX) {
                    Spacer(modifier = Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                    Spacer(modifier = Modifier.height(8.dp))

                    val isFileReady = viewModel.isModelFilePresent()
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = if (isFileReady) Color(0xFF10B981).copy(alpha = 0.12f) else Color(0xFFF59E0B).copy(alpha = 0.12f),
                        border = BorderStroke(1.dp, if (isFileReady) Color(0xFF10B981) else Color(0xFFF59E0B))
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = if (isFileReady) strings.modelWeightsReady else strings.modelWeightsMissing,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isFileReady) Color(0xFF059669) else Color(0xFFD97706)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = strings.deviceModelPathLabel,
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    OutlinedTextField(
                        value = modelPathInput,
                        onValueChange = {
                            modelPathInput = it
                            viewModel.setModelPath(it)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        textStyle = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace, fontSize = 10.sp),
                        shape = RoundedCornerShape(8.dp)
                    )
                }

                // Extra config for CLOUD_NEURAL
                if (engineMode == EngineMode.CLOUD_NEURAL) {
                    Spacer(modifier = Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = strings.cloudEndpointLabel,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedTextField(
                        value = endpointInput,
                        onValueChange = {
                            endpointInput = it
                            viewModel.setCloudEndpoint(it)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        textStyle = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace, fontSize = 11.sp),
                        shape = RoundedCornerShape(8.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant
                        )
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 3. Intent Decision Threshold Configuration (可配置意图判定阈值)
        val currentThreshold = decisionThreshold
        val thresholdPercent = (currentThreshold * 100).toInt()
        val grayMinPercent = ((currentThreshold - 0.20f) * 100).toInt().coerceAtLeast(10)

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = strings.thresholdSectionTitle,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = MaterialTheme.colorScheme.primaryContainer,
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.4f))
                    ) {
                        Text(
                            text = "≥ $thresholdPercent%",
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = strings.thresholdSectionSubtitle(thresholdPercent),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(8.dp))

                Slider(
                    value = currentThreshold,
                    onValueChange = { viewModel.setDecisionThreshold(it) },
                    valueRange = 0.20f..0.85f,
                    steps = 12,
                    modifier = Modifier.fillMaxWidth(),
                    colors = SliderDefaults.colors(
                        thumbColor = MaterialTheme.colorScheme.primary,
                        activeTrackColor = MaterialTheme.colorScheme.primary,
                        inactiveTrackColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                    )
                )

                Spacer(modifier = Modifier.height(6.dp))

                // Presets: 35%, 50%, 65%
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    PresetThresholdChip(
                        label = strings.thresholdPresetLenient,
                        isSelected = thresholdPercent == 35,
                        onClick = { viewModel.setDecisionThreshold(0.35f) },
                        modifier = Modifier.weight(1f)
                    )
                    PresetThresholdChip(
                        label = strings.thresholdPresetDefault,
                        isSelected = thresholdPercent == 50,
                        onClick = { viewModel.setDecisionThreshold(0.50f) },
                        modifier = Modifier.weight(1f)
                    )
                    PresetThresholdChip(
                        label = strings.thresholdPresetStrict,
                        isSelected = thresholdPercent == 65,
                        onClick = { viewModel.setDecisionThreshold(0.65f) },
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                Spacer(modifier = Modifier.height(8.dp))

                // Technical explanation of the 3 tiers
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🟢", fontSize = 10.sp)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(text = strings.thresholdGuideActive(thresholdPercent), fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(modifier = Modifier.height(3.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🟡", fontSize = 10.sp)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(text = strings.thresholdGuideGray(grayMinPercent, thresholdPercent), fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(modifier = Modifier.height(3.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "⚪", fontSize = 10.sp)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(text = strings.thresholdGuideExcluded(grayMinPercent), fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 4. Supported Commands / Domains Registry
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = strings.domainsSectionTitle(domains.count { it.isEnabled }, domains.size),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = strings.domainsSubtitle,
                            fontSize = 10.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    OutlinedButton(
                        onClick = { viewModel.resetDomains() },
                        shape = RoundedCornerShape(6.dp),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                        modifier = Modifier.height(28.dp)
                    ) {
                        Text(strings.btnResetDefault, fontSize = 10.sp)
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                domains.forEachIndexed { index, domain ->
                    DomainRowItem(
                        domain = domain,
                        language = currentLang,
                        onToggleEnabled = { viewModel.toggleDomain(domain.id) },
                        onToggleMultiLabel = { viewModel.toggleMultiLabel(domain.id) },
                        onDelete = { viewModel.removeDomain(domain.id) }
                    )
                    if (index < domains.size - 1) {
                        HorizontalDivider(
                            modifier = Modifier.padding(vertical = 6.dp),
                            color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 4. Add Custom Domain Form
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = strings.registerDomainTitle,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = strings.registerDomainSubtitle,
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = newId,
                        onValueChange = { newId = it },
                        label = { Text(strings.domainIdLabel, fontSize = 11.sp) },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        shape = RoundedCornerShape(8.dp)
                    )
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text(strings.domainNameLabel, fontSize = 11.sp) },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        shape = RoundedCornerShape(8.dp)
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = newDesc,
                    onValueChange = { newDesc = it },
                    label = { Text(strings.domainDescLabel, fontSize = 11.sp) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(8.dp)
                )

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = newMultiLabel,
                            onCheckedChange = { newMultiLabel = it }
                        )
                        Text(strings.multiLabelCheckbox, fontSize = 11.sp)
                    }

                    Button(
                        onClick = {
                            if (newId.isNotBlank() && newName.isNotBlank()) {
                                viewModel.addDomain(newId, newName, newDesc, newMultiLabel)
                                newId = ""
                                newName = ""
                                newDesc = ""
                            }
                        },
                        enabled = newId.isNotBlank() && newName.isNotBlank(),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.height(36.dp)
                    ) {
                        Text(strings.btnAddDomain, fontSize = 12.sp)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(30.dp))
    }
}

@Composable
private fun LanguagePill(
    title: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
        border = BorderStroke(
            width = if (isSelected) 1.5.dp else 0.5.dp,
            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant
        ),
        modifier = modifier
    ) {
        Row(
            modifier = Modifier.padding(vertical = 10.dp, horizontal = 12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = title,
                fontSize = 12.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
            )
            if (isSelected) {
                Spacer(modifier = Modifier.width(6.dp))
                Text(text = "✓", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Composable
private fun DomainRowItem(
    domain: DomainItem,
    language: AppLanguage,
    onToggleEnabled: () -> Unit,
    onToggleMultiLabel: () -> Unit,
    onDelete: () -> Unit
) {
    val localizedName = AppStrings.getLocalizedDomainName(domain.id, domain.name, language)
    val localizedDesc = AppStrings.getLocalizedDomainDesc(domain.id, domain.description, language)
    val multiLabelText = when (language) {
        AppLanguage.ZH -> if (domain.isMultiLabel) "多标签" else "单选"
        AppLanguage.ZHTW -> if (domain.isMultiLabel) "多標籤" else "單選"
        AppLanguage.EN -> if (domain.isMultiLabel) "Multi-Label" else "Single"
    }

    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = if (domain.isEnabled) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Text(
                        text = domain.id,
                        modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (domain.isEnabled) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.width(6.dp))

                Text(
                    text = localizedName,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = if (domain.isEnabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                )

                Spacer(modifier = Modifier.width(6.dp))

                Surface(
                    shape = RoundedCornerShape(3.dp),
                    color = if (domain.isMultiLabel) Color(0xFF10B981).copy(alpha = 0.12f) else Color(0xFF6B7280).copy(alpha = 0.12f)
                ) {
                    Text(
                        text = multiLabelText,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = if (domain.isMultiLabel) Color(0xFF059669) else Color(0xFF6B7280),
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(2.dp))

            Text(
                text = localizedDesc,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f)
            )
        }

        if (domain.isCustom) {
            IconButton(
                onClick = onDelete,
                modifier = Modifier.size(28.dp)
            ) {
                Text("✕", fontSize = 12.sp, color = MaterialTheme.colorScheme.error)
            }
            Spacer(modifier = Modifier.width(4.dp))
        }

        Switch(
            checked = domain.isEnabled,
            onCheckedChange = { onToggleEnabled() },
            modifier = Modifier.size(36.dp),
            colors = SwitchDefaults.colors(
                checkedThumbColor = MaterialTheme.colorScheme.primary,
                checkedTrackColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
    }
}

@Composable
private fun EngineModeOptionCard(
    title: String,
    subtitle: String,
    isSelected: Boolean,
    onSelect: () -> Unit
) {
    Surface(
        onClick = onSelect,
        shape = RoundedCornerShape(8.dp),
        color = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f) else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f),
        border = BorderStroke(
            width = if (isSelected) 1.5.dp else 0.5.dp,
            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.4f)
        ),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    fontSize = 12.sp,
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                    color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = subtitle,
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (isSelected) {
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = MaterialTheme.colorScheme.primary
                ) {
                    Text(
                        text = "✓",
                        color = MaterialTheme.colorScheme.onPrimary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun PresetThresholdChip(
    label: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
        border = BorderStroke(
            1.dp,
            if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.4f)
        ),
        modifier = modifier.height(34.dp)
    ) {
        androidx.compose.foundation.layout.Box(contentAlignment = Alignment.Center) {
            Text(
                text = label,
                fontSize = 11.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
