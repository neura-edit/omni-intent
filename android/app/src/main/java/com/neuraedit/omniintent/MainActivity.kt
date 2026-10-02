package com.neuraedit.omniintent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.neuraedit.omniintent.i18n.AppLanguage
import com.neuraedit.omniintent.theme.OmniIntentTheme
import com.neuraedit.omniintent.ui.MainApp
import com.neuraedit.omniintent.ui.OmniViewModel
import com.neuraedit.omniintent.ui.welcome.LanguageSelectScreen
import com.neuraedit.omniintent.ui.welcome.ModelLoadingScreen

class MainActivity : ComponentActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    enableEdgeToEdge()
    setContent {
      OmniIntentTheme {
        Surface(
          modifier = Modifier.fillMaxSize(),
          color = MaterialTheme.colorScheme.background
        ) {
          val viewModel: OmniViewModel = viewModel()
          val appLanguage by viewModel.appLanguage.collectAsStateWithLifecycle()
          val isModelWarmedUp by viewModel.isModelWarmedUp.collectAsStateWithLifecycle()

          when {
            // Step 1: Language selection gate on entry
            appLanguage == null -> {
              LanguageSelectScreen(
                onSelectLanguage = { lang ->
                  viewModel.setAppLanguage(lang)
                }
              )
            }
            // Step 2: Model warmup loading screen with progress animation
            !isModelWarmedUp -> {
              ModelLoadingScreen(
                language = appLanguage ?: AppLanguage.ZH,
                onWarmupComplete = {
                  viewModel.markModelWarmedUp()
                }
              )
            }
            // Step 3: Main dashboard with warm on-device neural engine
            else -> {
              MainApp(viewModel = viewModel)
            }
          }
        }
      }
    }
  }
}
