package com.neuraedit.omniintent.ui.welcome

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neuraedit.omniintent.R
import com.neuraedit.omniintent.i18n.AppLanguage

@Composable
fun LanguageSelectScreen(
    onSelectLanguage: (AppLanguage) -> Unit
) {
    var selectedLanguage by remember { mutableStateOf<AppLanguage?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .padding(horizontal = 24.dp, vertical = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // Logo
        Box(
            modifier = Modifier
                .size(92.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(Color(0xFF0F172A))
                .padding(4.dp),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(id = R.drawable.neura_edit_logo),
                contentDescription = "NEURA EDIT Logo",
                modifier = Modifier
                    .size(84.dp)
                    .clip(RoundedCornerShape(16.dp))
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        Text(
            text = "NEURA EDIT",
            fontSize = 24.sp,
            fontWeight = FontWeight.Black,
            letterSpacing = 1.sp,
            color = MaterialTheme.colorScheme.onSurface
        )

        Text(
            text = "OmniIntent Decision Engine",
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.primary
        )

        // Note: No "选择语言" heading under the LOGO per user requirement #1
        Spacer(modifier = Modifier.height(32.dp))

        // Option 1: 简体中文 (No flag per user requirement #4)
        LanguageOptionCard(
            title = "简体中文",
            subtitle = "面向端侧的多意图决策引擎",
            isSelected = selectedLanguage == AppLanguage.ZH,
            onSelect = { selectedLanguage = AppLanguage.ZH }
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Option 2: 繁體中文 (Added per user requirement #5)
        LanguageOptionCard(
            title = "繁體中文",
            subtitle = "面向端側的多意圖決策引擎",
            isSelected = selectedLanguage == AppLanguage.ZHTW,
            onSelect = { selectedLanguage = AppLanguage.ZHTW }
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Option 3: English (No flag per user requirement #4)
        LanguageOptionCard(
            title = "English",
            subtitle = "On-Device Multi-Intent Decision Engine",
            isSelected = selectedLanguage == AppLanguage.EN,
            onSelect = { selectedLanguage = AppLanguage.EN }
        )

        Spacer(modifier = Modifier.height(28.dp))

        // Bottom Confirmation Button: Appears only after language selection (per user requirement #2 & #3)
        AnimatedVisibility(
            visible = selectedLanguage != null,
            enter = fadeIn() + slideInVertically { it / 2 }
        ) {
            val confirmText = when (selectedLanguage) {
                AppLanguage.ZH -> "进入系统"
                AppLanguage.ZHTW -> "進入系統"
                AppLanguage.EN -> "Enter System"
                null -> ""
            }

            Button(
                onClick = { selectedLanguage?.let { onSelectLanguage(it) } },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Text(
                    text = confirmText,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun LanguageOptionCard(
    title: String,
    subtitle: String,
    isSelected: Boolean,
    onSelect: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onSelect),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f) else MaterialTheme.colorScheme.surface
        ),
        border = BorderStroke(
            width = if (isSelected) 2.dp else 1.dp,
            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = subtitle,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Surface(
                shape = RoundedCornerShape(12.dp),
                color = if (isSelected) MaterialTheme.colorScheme.primary else Color.Transparent,
                border = BorderStroke(1.dp, if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.size(24.dp)
            ) {
                if (isSelected) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = "✓",
                            color = MaterialTheme.colorScheme.onPrimary,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}
