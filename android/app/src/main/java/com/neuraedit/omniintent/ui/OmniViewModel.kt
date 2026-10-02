package com.neuraedit.omniintent.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.neuraedit.omniintent.data.EngineMode
import com.neuraedit.omniintent.data.OmniRepository
import com.neuraedit.omniintent.model.DecisionResult
import com.neuraedit.omniintent.model.DomainItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class OmniViewModel @JvmOverloads constructor(
    application: Application,
    private val repository: OmniRepository = OmniRepository()
) : AndroidViewModel(application) {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    private val _appLanguage = MutableStateFlow<com.neuraedit.omniintent.i18n.AppLanguage?>(null)
    val appLanguage: StateFlow<com.neuraedit.omniintent.i18n.AppLanguage?> = _appLanguage.asStateFlow()

    private val _isModelWarmedUp = MutableStateFlow(false)
    val isModelWarmedUp: StateFlow<Boolean> = _isModelWarmedUp.asStateFlow()

    val domains: StateFlow<List<DomainItem>> = repository.domains
    val engineMode: StateFlow<EngineMode> = repository.engineMode
    val modelPath: StateFlow<String> = repository.modelPath
    val cloudEndpoint: StateFlow<String> = repository.cloudEndpoint
    val decisionThreshold: StateFlow<Float> = repository.decisionThreshold
    val lastResult: StateFlow<DecisionResult?> = repository.lastResult
    val isLoading: StateFlow<Boolean> = repository.isLoading
    val errorMessage: StateFlow<String?> = repository.errorMessage

    fun setAppLanguage(language: com.neuraedit.omniintent.i18n.AppLanguage) {
        if (_appLanguage.value != language) {
            _appLanguage.value = language
            _query.value = ""
            repository.clearResult()
        }
    }

    fun markModelWarmedUp() {
        _isModelWarmedUp.value = true
    }

    fun isModelFilePresent(): Boolean {
        return repository.isModelFilePresent()
    }

    fun updateQuery(text: String) {
        _query.value = text
    }

    fun executeDecision() {
        val q = _query.value
        if (q.isBlank()) return
        viewModelScope.launch {
            repository.executeDecision(getApplication(), q)
        }
    }

    fun runPresetQuery(preset: String) {
        _query.value = preset
        viewModelScope.launch {
            repository.executeDecision(getApplication(), preset)
        }
    }

    fun setEngineMode(mode: EngineMode) {
        repository.setEngineMode(mode)
    }

    fun setModelPath(path: String) {
        repository.setModelPath(path)
    }

    fun setCloudEndpoint(url: String) {
        repository.setCloudEndpoint(url)
    }

    fun setDecisionThreshold(threshold: Float) {
        repository.setDecisionThreshold(threshold)
    }

    fun toggleDomain(id: String) {
        repository.toggleDomain(id)
    }

    fun toggleMultiLabel(id: String) {
        repository.toggleMultiLabel(id)
    }

    fun addDomain(id: String, name: String, desc: String, isMultiLabel: Boolean) {
        repository.addDomain(id, name, desc, isMultiLabel)
    }

    fun removeDomain(id: String) {
        repository.removeDomain(id)
    }

    fun resetDomains() {
        repository.resetDomains()
    }
}
