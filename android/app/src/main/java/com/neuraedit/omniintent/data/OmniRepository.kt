package com.neuraedit.omniintent.data

import android.content.Context
import com.neuraedit.omniintent.engine.OmniIntentEngine
import com.neuraedit.omniintent.engine.OnnxIntentEngine
import com.neuraedit.omniintent.model.DecisionResult
import com.neuraedit.omniintent.model.DomainItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

enum class EngineMode {
    LOCAL_ONNX,       // 端侧 0.75B INT8 (ONNX Runtime 真实端侧硬件推理)
    LOCAL_EMBEDDED,   // 本地极速微引擎 (3ms 离线语义前缀树)
    CLOUD_NEURAL      // 云端 0.75B 神经模型 (ModelScope 在线 API)
}

class OmniRepository {

    private val _domains = MutableStateFlow<List<DomainItem>>(DomainItem.defaultDomains())
    val domains: StateFlow<List<DomainItem>> = _domains.asStateFlow()

    private val _engineMode = MutableStateFlow(EngineMode.LOCAL_ONNX)
    val engineMode: StateFlow<EngineMode> = _engineMode.asStateFlow()

    private val _modelPath = MutableStateFlow("/data/local/tmp/decision_eos_int8.onnx")
    val modelPath: StateFlow<String> = _modelPath.asStateFlow()

    private val _cloudEndpoint = MutableStateFlow("https://neuraedit-omni-intent.ms.show/api/decide")
    val cloudEndpoint: StateFlow<String> = _cloudEndpoint.asStateFlow()

    private val _decisionThreshold = MutableStateFlow(0.50f)
    val decisionThreshold: StateFlow<Float> = _decisionThreshold.asStateFlow()

    private val _lastResult = MutableStateFlow<DecisionResult?>(null)
    val lastResult: StateFlow<DecisionResult?> = _lastResult.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    fun isModelFilePresent(): Boolean {
        return OnnxIntentEngine.isModelFileAvailable(_modelPath.value)
    }

    fun clearResult() {
        _lastResult.value = null
        _errorMessage.value = null
    }

    suspend fun executeDecision(context: Context, query: String) = withContext(Dispatchers.IO) {
        if (query.isBlank()) return@withContext
        _isLoading.value = true
        _errorMessage.value = null
        val startWall = System.currentTimeMillis()
        val currentThreshold = _decisionThreshold.value

        try {
            val result = when (_engineMode.value) {
                EngineMode.LOCAL_ONNX -> {
                    if (OnnxIntentEngine.isModelFileAvailable(_modelPath.value)) {
                        OnnxIntentEngine.runInference(
                            context = context,
                            query = query.trim(),
                            domains = _domains.value,
                            startWallTime = startWall,
                            threshold = currentThreshold
                        )
                    } else {
                        // Model weights not yet pushed to device -> fallback to local embedded engine
                        val fallback = OmniIntentEngine.decide(
                            query = query.trim(),
                            isCloudMode = false,
                            cloudEndpoint = "",
                            domains = _domains.value,
                            threshold = currentThreshold
                        )
                        fallback.copy(
                            engineName = "Local Engine (ONNX weights not found, using fast fallback)"
                        )
                    }
                }
                EngineMode.LOCAL_EMBEDDED -> {
                    OmniIntentEngine.decide(
                        query = query.trim(),
                        isCloudMode = false,
                        cloudEndpoint = "",
                        domains = _domains.value,
                        threshold = currentThreshold
                    )
                }
                EngineMode.CLOUD_NEURAL -> {
                    OmniIntentEngine.decide(
                        query = query.trim(),
                        isCloudMode = true,
                        cloudEndpoint = _cloudEndpoint.value,
                        domains = _domains.value,
                        threshold = currentThreshold
                    )
                }
            }
            _lastResult.value = result
        } catch (e: Exception) {
            e.printStackTrace()
            _errorMessage.value = e.localizedMessage ?: "判定执行异常"
        } finally {
            _isLoading.value = false
        }
    }

    fun setEngineMode(mode: EngineMode) {
        _engineMode.value = mode
    }

    fun setModelPath(path: String) {
        _modelPath.value = path.trim()
    }

    fun setCloudEndpoint(url: String) {
        _cloudEndpoint.value = url.trim()
    }

    fun setDecisionThreshold(threshold: Float) {
        _decisionThreshold.value = threshold.coerceIn(0.10f, 0.90f)
    }

    fun toggleDomain(id: String) {
        _domains.value = _domains.value.map {
            if (it.id == id) it.copy(isEnabled = !it.isEnabled) else it
        }
    }

    fun toggleMultiLabel(id: String) {
        _domains.value = _domains.value.map {
            if (it.id == id) it.copy(isMultiLabel = !it.isMultiLabel) else it
        }
    }

    fun addDomain(id: String, name: String, description: String, isMultiLabel: Boolean) {
        val cleanId = id.trim().lowercase().replace(" ", "_")
        if (cleanId.isBlank() || _domains.value.any { it.id == cleanId }) return
        val newDomain = DomainItem(
            id = cleanId,
            name = name.ifBlank { cleanId },
            description = description.ifBlank { "自定义指令域" },
            isMultiLabel = isMultiLabel,
            isEnabled = true,
            isCustom = true
        )
        _domains.value = _domains.value + newDomain
    }

    fun removeDomain(id: String) {
        _domains.value = _domains.value.filterNot { it.id == id }
    }

    fun resetDomains() {
        _domains.value = DomainItem.defaultDomains()
    }
}
