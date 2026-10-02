package com.neuraedit.omniintent.i18n

enum class AppLanguage(val code: String, val displayName: String, val localizedName: String) {
    ZH("zh", "简体中文", "Simplified Chinese"),
    ZHTW("zh-tw", "繁體中文", "Traditional Chinese"),
    EN("en", "English", "English")
}

data class LocalizedStrings(
    // App Bar & Navigation
    val appTitle: String,
    val appSubtitle: String,
    val tabCommand: String,
    val tabSettings: String,
    val tabAbout: String,

    // Language Selection Screen
    val selectLanguageTitle: String,
    val selectLanguageSubtitle: String,
    val langZhTitle: String,
    val langZhDesc: String,
    val langZhtwTitle: String,
    val langZhtwDesc: String,
    val langEnTitle: String,
    val langEnDesc: String,
    val btnConfirmLanguage: String,

    // Model Warmup / Loading Screen
    val loadingTitle: String,
    val loadingSubtitle: String,
    val loadingStep1: String,
    val loadingStep2: String,
    val loadingStep3: String,
    val loadingReady: String,

    // Command Screen
    val engineOnDeviceBadge: String,
    val engineCloudBadge: String,
    val presetTitle: String,
    val presets: List<String>,
    val inputPlaceholder: String,
    val btnExecute: String,
    val btnExecuting: String,
    val metricsTitle: String,
    val metricWallClock: String,
    val metricInference: String,
    val metricTokens: String,
    val metricActive: String,
    val intentsTitle: String,
    val thresholdLabel: (percent: Int) -> String,
    val badgeYesOn: String,
    val badgeYesOff: String,
    val badgeGray: String,
    val badgeExcluded: String,
    val slotsTitle: String,
    val slotsSubtitle: String,
    val slotNegationPrefix: String,
    val singleCommandBanner: (domainName: String, action: String) -> String,
    val multiCommandBanner: (domains: String) -> String,

    // Settings Screen
    val settingsTitle: String,
    val settingsSubtitle: String,
    val languageSectionTitle: String,
    val thresholdSectionTitle: String,
    val thresholdSectionSubtitle: (percent: Int) -> String,
    val thresholdPresetLenient: String,
    val thresholdPresetDefault: String,
    val thresholdPresetStrict: String,
    val thresholdGuideActive: (percent: Int) -> String,
    val thresholdGuideGray: (grayMin: Int, percent: Int) -> String,
    val thresholdGuideExcluded: (grayMin: Int) -> String,
    val engineModeSectionTitle: String,
    val optionOnDeviceTitle: String,
    val optionOnDeviceSubtitle: String,
    val optionCloudTitle: String,
    val optionCloudSubtitle: String,
    val modelWeightsReady: String,
    val modelWeightsMissing: String,
    val deviceModelPathLabel: String,
    val cloudEndpointLabel: String,
    val domainsSectionTitle: (active: Int, total: Int) -> String,
    val domainsSubtitle: String,
    val btnResetDefault: String,
    val registerDomainTitle: String,
    val registerDomainSubtitle: String,
    val domainIdLabel: String,
    val domainNameLabel: String,
    val domainDescLabel: String,
    val multiLabelCheckbox: String,
    val btnAddDomain: String,

    // About Screen
    val aboutHeaderTitle: String,
    val aboutHeaderSubtitle: String,
    val brandFullName: String,
    val brandProductTitle: String,
    val brandProductSubtitle: String,
    val badgeOnDeviceTag: String,
    val badgeOnnxTag: String,
    val badgeAutomotiveTag: String,
    val badgeOpenSourceTag: String,
    val sloganSectionTitle: String,
    val sloganPrimary: String,
    val sloganSecondary: String,
    val sloganMission: String,
    val githubCardTitle: String,
    val githubCardSubtitle: String,
    val btnVisitGithub: String,
    val btnCopyLink: String,
    val toastCopied: String,
    val matrixSectionTitle: String,
    val matrixSectionSubtitle: String,
    val linkWebHudTitle: String,
    val linkWebHudSub: String,
    val linkModelScopeTitle: String,
    val linkModelScopeSub: String,
    val linkOrgTitle: String,
    val linkOrgSub: String,
    val specsSectionTitle: String,
    val spec1Title: String,
    val spec1Desc: String,
    val spec2Title: String,
    val spec2Desc: String,
    val spec3Title: String,
    val spec3Desc: String,
    val footerVersion: String,
    val footerLicense: String
)

object AppStrings {
    val ZH = LocalizedStrings(
        appTitle = "OMNIINTENT",
        appSubtitle = "Multi-label Decision Engine",
        tabCommand = "执行指令",
        tabSettings = "配置管理",
        tabAbout = "关于 N/E",

        selectLanguageTitle = "选择语言",
        selectLanguageSubtitle = "请选择应用交互与展示语言",
        langZhTitle = "简体中文",
        langZhDesc = "面向端侧的多意图决策引擎",
        langZhtwTitle = "繁體中文",
        langZhtwDesc = "面向端側的多意圖決策引擎",
        langEnTitle = "English",
        langEnDesc = "On-Device Multi-Intent Decision Engine",
        btnConfirmLanguage = "进入系统",

        loadingTitle = "正在启动端侧 0.75B 神经引擎",
        loadingSubtitle = "加载 1.9GB INT8 权重与 ONNX Runtime 环境...",
        loadingStep1 = "检测设备本地权重文件...",
        loadingStep2 = "初始化 ONNX Runtime 运行环境...",
        loadingStep3 = "构建 0.75B 张量计算会话与前向路由图...",
        loadingReady = "模型就绪，进入应用",

        engineOnDeviceBadge = "🧠 端侧 0.75B (ONNX)",
        engineCloudBadge = "☁️ 0.75B 云端",
        presetTitle = "推荐测试例句 · 点击即测",
        presets = listOf(
            "我要听八三夭的外婆的告别式这首歌",
            "把温度调低两度，不要开外循环",
            "周杰伦的稻香，顺便把空调开到24度",
            "关闭空调，但是不要关座椅加热",
            "导航去虹桥机场，避开拥堵但不要走高速",
            "放一首摇滚，顺便打开主驾座椅加热",
            "把副驾车窗降下一半",
            "明天上海天气怎么样"
        ),
        inputPlaceholder = "输入测试指令（例如：放首稻香，关闭空调但不要关座椅加热）...",
        btnExecute = "开始判定",
        btnExecuting = "深度神经判定中...",
        metricsTitle = "耗时与指标统计",
        metricWallClock = "端到端耗时",
        metricInference = "模型推理",
        metricTokens = "Token 统计",
        metricActive = "命中意图",
        intentsTitle = "意图识别结果",
        thresholdLabel = { percent -> "阈值: ≥$percent% 触发" },
        badgeYesOn = "开启",
        badgeYesOff = "关闭",
        badgeGray = "灰区待确认",
        badgeExcluded = "已排除",
        slotsTitle = "槽位与参数提取",
        slotsSubtitle = "从自然语言中精准抽取的全维度执行参数",
        slotNegationPrefix = "⚠️ 负向规避约束: ",
        singleCommandBanner = { domain, act -> "单指令 · $domain · $act" },
        multiCommandBanner = { domains -> "多意图协同 · $domains" },

        settingsTitle = "ENGINE CONFIGURATION",
        settingsSubtitle = "指令域注册表与运行参数配置",
        languageSectionTitle = "界面交互语言",
        thresholdSectionTitle = "意图判定阈值配置",
        thresholdSectionSubtitle = { percent -> "调节激活意图判定阈值，当前为 ≥$percent%" },
        thresholdPresetLenient = "宽松 35%",
        thresholdPresetDefault = "推荐 50%",
        thresholdPresetStrict = "严格 65%",
        thresholdGuideActive = { percent -> "≥ $percent%: 判定为开启或关闭激活意图" },
        thresholdGuideGray = { gray, percent -> "$gray% ~ $percent%: 判定为灰区待确认" },
        thresholdGuideExcluded = { gray -> "< $gray%: 判定为排除不触发" },
        engineModeSectionTitle = "决策模型运行模式",
        optionOnDeviceTitle = "端侧 0.75B INT8 本地模型",
        optionOnDeviceSubtitle = "在设备本地运行神经网络张量计算，单次前向无迟滞",
        optionCloudTitle = "云端 0.75B 神经引擎",
        optionCloudSubtitle = "在线请求云端容器执行推理，超时自动回退",
        modelWeightsReady = "本地权重已就绪 · 1.9GB",
        modelWeightsMissing = "暂未检测到本地权重文件",
        deviceModelPathLabel = "设备端模型路径:",
        cloudEndpointLabel = "云端 API 端点",
        domainsSectionTitle = { active, total -> "当前支持的指令域 · $active/$total" },
        domainsSubtitle = "参考架构配置：支持多标签与单选互斥",
        btnResetDefault = "重置默认",
        registerDomainTitle = "注册新增指令域",
        registerDomainSubtitle = "动态拓展模型决策范围",
        domainIdLabel = "唯一标识 ID",
        domainNameLabel = "显示名称",
        domainDescLabel = "指令域描述 / 功能释义",
        multiLabelCheckbox = "支持多标签并发",
        btnAddDomain = "添加",

        aboutHeaderTitle = "ABOUT NEURA EDIT",
        aboutHeaderSubtitle = "项目全名、官方标识与开源技术规格",
        brandFullName = "NEURA EDIT",
        brandProductTitle = "OmniIntent 决策引擎",
        brandProductSubtitle = "端侧多意图神经路由与确定性槽位直出",
        badgeOnDeviceTag = "端侧 0.75B INT8",
        badgeOnnxTag = "ONNX Runtime",
        badgeAutomotiveTag = "车规高确定性",
        badgeOpenSourceTag = "开源生态",
        sloganSectionTitle = "核心定位",
        sloganPrimary = "端侧多意图神经决策引擎",
        sloganSecondary = "单次前向张量路由 · 零延迟响应",
        sloganMission = "端侧单次前向张量计算，实现空调、音乐、导航、座椅加热、车窗等多域指令毫秒级并行判定与确定性槽位抽取，无云端依赖，离线实时可控。",
        githubCardTitle = "GitHub 开源仓库",
        githubCardSubtitle = "代码、量化工具链与座舱交互规范",
        btnVisitGithub = "访问 GitHub",
        btnCopyLink = "复制链接",
        toastCopied = "已复制到剪贴板",
        matrixSectionTitle = "在线体验与多端矩阵",
        matrixSectionSubtitle = "云端免安装试用、开源模型权重与 HUD 控制台",
        linkWebHudTitle = "Web HUD 在线控制台",
        linkWebHudSub = "在线直连推理控制台",
        linkModelScopeTitle = "阿里云魔搭创空间",
        linkModelScopeSub = "云端在线端点与权重托管",
        linkOrgTitle = "GitHub 官方组织主页",
        linkOrgSub = "github.com/neura-edit",
        specsSectionTitle = "核心技术规格",
        spec1Title = "单次前向神经路由",
        spec1Desc = "基于 0.75B Transformer 决策头，单次前向推理计算产出全域概率分布，彻底消除自回归逐字生成延迟。",
        spec2Title = "端侧 INT8 量化与动态门控剪枝",
        spec2Desc = "1.9GB 本地权重直接运行在设备本地 CPU 上，结合候选域门控剪枝，实现极致轻量化与毫秒级时延。",
        spec3Title = "车规级否定词抑制与多域解耦",
        spec3Desc = "精准区分主领域排除（如“不要关空调”）与二级参数约束（如“不要开外循环”），确保零误判。",
        footerVersion = "NEURA EDIT · OmniIntent v1.2.0 (Automotive Edition)",
        footerLicense = "Open Source under MIT License · 2026"
    )

    val ZHTW = LocalizedStrings(
        appTitle = "OMNIINTENT",
        appSubtitle = "Multi-label Decision Engine",
        tabCommand = "執行指令",
        tabSettings = "配置管理",
        tabAbout = "關於 N/E",

        selectLanguageTitle = "選擇語言",
        selectLanguageSubtitle = "請選擇應用互動與展示語言",
        langZhTitle = "简体中文",
        langZhDesc = "面向端侧的多意图决策引擎",
        langZhtwTitle = "繁體中文",
        langZhtwDesc = "面向端側的多意圖決策引擎",
        langEnTitle = "English",
        langEnDesc = "On-Device Multi-Intent Decision Engine",
        btnConfirmLanguage = "進入系統",

        loadingTitle = "正在啟動端側 0.75B 神經引擎",
        loadingSubtitle = "載入 1.9GB INT8 權重與 ONNX Runtime 環境...",
        loadingStep1 = "檢測設備本地權重檔案...",
        loadingStep2 = "初始化 ONNX Runtime 運行環境...",
        loadingStep3 = "構建 0.75B 張量計算會話與前向路由圖...",
        loadingReady = "模型就緒，進入應用",

        engineOnDeviceBadge = "🧠 端側 0.75B (ONNX)",
        engineCloudBadge = "☁️ 0.75B 雲端",
        presetTitle = "推薦測試語句 · 點擊即測",
        presets = listOf(
            "我要聽八三夭的外婆的告別式這首歌",
            "把溫度調低兩度，不要開外循環",
            "周杰倫的稻香，順便把空調開到24度",
            "關閉空調，但是不要關座椅加熱",
            "導航去機場，避開擁堵但不要走高速",
            "放一首搖滾，順便打開主駕座椅加熱",
            "把副駕車窗降下一半",
            "明天天氣怎麼樣"
        ),
        inputPlaceholder = "輸入測試指令（例如：放首稻香，關閉空調但不要關座椅加熱）...",
        btnExecute = "開始判定",
        btnExecuting = "深度神經判定中...",
        metricsTitle = "耗時與指標統計",
        metricWallClock = "端到端耗時",
        metricInference = "模型推理",
        metricTokens = "Token 統計",
        metricActive = "命中意圖",
        intentsTitle = "意圖識別結果",
        thresholdLabel = { percent -> "閾值: ≥$percent% 觸發" },
        badgeYesOn = "開啟",
        badgeYesOff = "關閉",
        badgeGray = "灰區待確認",
        badgeExcluded = "已排除",
        slotsTitle = "槽位與參數提取",
        slotsSubtitle = "從自然語言中精準抽取的全維度執行參數",
        slotNegationPrefix = "⚠️ 負向規避約束: ",
        singleCommandBanner = { domain, act -> "單指令 · $domain · $act" },
        multiCommandBanner = { domains -> "多意圖協同 · $domains" },

        settingsTitle = "ENGINE CONFIGURATION",
        settingsSubtitle = "指令域註冊表與運行參數配置",
        languageSectionTitle = "介面互動語言",
        thresholdSectionTitle = "意圖判定閾值配置",
        thresholdSectionSubtitle = { percent -> "調節激活意圖判定閾值，當前為 ≥$percent%" },
        thresholdPresetLenient = "寬鬆 35%",
        thresholdPresetDefault = "推薦 50%",
        thresholdPresetStrict = "嚴格 65%",
        thresholdGuideActive = { percent -> "≥ $percent%: 判定為開啟或關閉激活意圖" },
        thresholdGuideGray = { gray, percent -> "$gray% ~ $percent%: 判定為灰區待確認" },
        thresholdGuideExcluded = { gray -> "< $gray%: 判定為排除不觸發" },
        engineModeSectionTitle = "決策模型運行模式",
        optionOnDeviceTitle = "端側 0.75B INT8 本地模型",
        optionOnDeviceSubtitle = "在設備本地運行神經網絡張量計算，單次前向無遲滯",
        optionCloudTitle = "雲端 0.75B 神經引擎",
        optionCloudSubtitle = "在線請求雲端容器執行推理，超時自動回退",
        modelWeightsReady = "本地權重已就緒 · 1.9GB",
        modelWeightsMissing = "暫未檢測到本地權重檔案",
        deviceModelPathLabel = "設備端模型路徑:",
        cloudEndpointLabel = "雲端 API 端點",
        domainsSectionTitle = { active, total -> "當前支援的指令域 · $active/$total" },
        domainsSubtitle = "參考架構配置：支援多標籤與單選互斥",
        btnResetDefault = "重置預設",
        registerDomainTitle = "註冊新增指令域",
        registerDomainSubtitle = "動態拓展模型決策範圍",
        domainIdLabel = "唯一標識 ID",
        domainNameLabel = "顯示名稱",
        domainDescLabel = "指令域描述 / 功能釋義",
        multiLabelCheckbox = "支援多標籤並發",
        btnAddDomain = "新增",

        aboutHeaderTitle = "ABOUT NEURA EDIT",
        aboutHeaderSubtitle = "專案全名、官方標識與開源技術規格",
        brandFullName = "NEURA EDIT",
        brandProductTitle = "OmniIntent 決策引擎",
        brandProductSubtitle = "端側多意圖神經路由與確定性槽位直出",
        badgeOnDeviceTag = "端側 0.75B INT8",
        badgeOnnxTag = "ONNX Runtime",
        badgeAutomotiveTag = "車規高確定性",
        badgeOpenSourceTag = "開源生態",
        sloganSectionTitle = "核心定位",
        sloganPrimary = "端側多意圖神經決策引擎",
        sloganSecondary = "單次前向張量路由 · 零延遲響應",
        sloganMission = "端側單次前向張量計算，實現空調、音樂、導航、座椅加熱、車窗等多域指令毫秒級並行判定與確定性槽位抽取，無雲端依賴，離線即時可控。",
        githubCardTitle = "GitHub 開源倉庫",
        githubCardSubtitle = "程式碼、量化工具鏈與座艙互動規範",
        btnVisitGithub = "造訪 GitHub",
        btnCopyLink = "複製連結",
        toastCopied = "已複製到剪貼簿",
        matrixSectionTitle = "線上體驗與多端矩陣",
        matrixSectionSubtitle = "雲端免安裝試用、開源模型權重與 HUD 控制台",
        linkWebHudTitle = "Web HUD 線上控制台",
        linkWebHudSub = "線上直連推理控制台",
        linkModelScopeTitle = "阿里雲魔搭創空間",
        linkModelScopeSub = "雲端線上端點與權重託管",
        linkOrgTitle = "GitHub 官方組織首頁",
        linkOrgSub = "github.com/neura-edit",
        specsSectionTitle = "核心技術規格",
        spec1Title = "單次前向神經路由",
        spec1Desc = "基於 0.75B Transformer 決策頭，單次前向推理計算產出全域機率分佈，徹底消除自回歸逐字生成延遲。",
        spec2Title = "端側 INT8 量化與動態門控剪枝",
        spec2Desc = "1.9GB 本地權重直接運行在設備本地 CPU 上，結合候選域門控剪枝，實現極致輕量化與毫秒級時延。",
        spec3Title = "車規級否定詞抑制與多域解耦",
        spec3Desc = "精準區分主領域排除（如“不要關空調”）與次級參數約束（如“不要開外循環”），確保零誤判。",
        footerVersion = "NEURA EDIT · OmniIntent v1.2.0 (Automotive Edition)",
        footerLicense = "Open Source under MIT License · 2026"
    )

    val EN = LocalizedStrings(
        appTitle = "OMNIINTENT",
        appSubtitle = "Multi-label Decision Engine",
        tabCommand = "Command",
        tabSettings = "Settings",
        tabAbout = "About N/E",

        selectLanguageTitle = "Select Display Language",
        selectLanguageSubtitle = "Choose application interface and output language",
        langZhTitle = "简体中文",
        langZhDesc = "面向端侧的多意图决策引擎",
        langZhtwTitle = "繁體中文",
        langZhtwDesc = "面向端側的多意圖決策引擎",
        langEnTitle = "English",
        langEnDesc = "On-Device Multi-Intent Decision Engine",
        btnConfirmLanguage = "Enter System",

        loadingTitle = "Initializing On-Device 0.75B Neural Engine",
        loadingSubtitle = "Loading 1.9GB INT8 weights & ONNX Runtime environment...",
        loadingStep1 = "Checking local INT8 weight files...",
        loadingStep2 = "Initializing ONNX Runtime execution environment...",
        loadingStep3 = "Constructing 0.75B tensor session & forward routing graph...",
        loadingReady = "Engine ready, entering app",

        engineOnDeviceBadge = "🧠 On-Device 0.75B (ONNX)",
        engineCloudBadge = "☁️ 0.75B Cloud",
        presetTitle = "Recommended Test Utterances · Tap to test",
        presets = listOf(
            "Play rock music and turn on driver seat heating",
            "Turn down temperature by 2 degrees, do not open fresh air",
            "Close AC, but do not turn off seat heating",
            "Navigate to airport, avoid congestion but do not take highway",
            "Lower passenger window by half",
            "Turn on AC to 22 degrees and play some jazz",
            "What is the weather like tomorrow",
            "Call John on phone"
        ),
        inputPlaceholder = "Enter test command (e.g. Turn down temp by 2 degrees, don't open fresh air)...",
        btnExecute = "Run Decision Engine",
        btnExecuting = "Evaluating Neural Graph...",
        metricsTitle = "Performance & Metrics",
        metricWallClock = "End-to-End Latency",
        metricInference = "Inference Time",
        metricTokens = "Token Count",
        metricActive = "Active Intents",
        intentsTitle = "Multi-Intent Decision Results",
        thresholdLabel = { percent -> "Threshold: ≥$percent%" },
        badgeYesOn = "ON",
        badgeYesOff = "OFF",
        badgeGray = "GRAY",
        badgeExcluded = "EXCLUDED",
        slotsTitle = "Deterministic Slot Breakdown",
        slotsSubtitle = "Execution parameters parsed from natural language",
        slotNegationPrefix = "⚠️ Negative Constraint: ",
        singleCommandBanner = { domain, act -> "Single Intent · $domain · $act" },
        multiCommandBanner = { domains -> "Concurrent Multi-Intent · $domains" },

        settingsTitle = "ENGINE CONFIGURATION",
        settingsSubtitle = "Intent Domains Registry & Runtime Parameters",
        languageSectionTitle = "Display Language",
        thresholdSectionTitle = "Decision Threshold Configuration",
        thresholdSectionSubtitle = { percent -> "Adjust activation cutoff for positive intent decision, current: ≥$percent%" },
        thresholdPresetLenient = "Lenient 35%",
        thresholdPresetDefault = "Default 50%",
        thresholdPresetStrict = "Strict 65%",
        thresholdGuideActive = { percent -> "≥ $percent%: Active intent triggered (ON/OFF)" },
        thresholdGuideGray = { gray, percent -> "$gray% ~ $percent%: Ambiguous gray zone" },
        thresholdGuideExcluded = { gray -> "< $gray%: Excluded from execution" },
        engineModeSectionTitle = "Decision Model Runtime Mode",
        optionOnDeviceTitle = "On-Device 0.75B INT8 Local Model",
        optionOnDeviceSubtitle = "Execute neural network tensor compute locally on device with zero delay",
        optionCloudTitle = "Cloud 0.75B Neural Engine",
        optionCloudSubtitle = "Request cloud container for inference with local fallback",
        modelWeightsReady = "Local weights ready · 1.9GB",
        modelWeightsMissing = "Local weight file not detected",
        deviceModelPathLabel = "Device Model Path:",
        cloudEndpointLabel = "Cloud API Endpoint",
        domainsSectionTitle = { active, total -> "Supported Intent Domains · $active/$total" },
        domainsSubtitle = "Reference architecture: Supports multi-label and single mutex",
        btnResetDefault = "Reset Defaults",
        registerDomainTitle = "Register New Intent Domain",
        registerDomainSubtitle = "Dynamically extend model decision scope",
        domainIdLabel = "Unique Domain ID",
        domainNameLabel = "Display Name",
        domainDescLabel = "Domain Description / Purpose",
        multiLabelCheckbox = "Support Multi-Label Concurrency",
        btnAddDomain = "Add Domain",

        aboutHeaderTitle = "ABOUT NEURA EDIT",
        aboutHeaderSubtitle = "Brand Full Name, Official Logo & Open Source Specs",
        brandFullName = "NEURA EDIT",
        brandProductTitle = "OmniIntent Decision Engine",
        brandProductSubtitle = "On-Device Neural Routing & Deterministic Slot Extraction",
        badgeOnDeviceTag = "On-Device 0.75B INT8",
        badgeOnnxTag = "ONNX Runtime",
        badgeAutomotiveTag = "Automotive Determinism",
        badgeOpenSourceTag = "Open Source",
        sloganSectionTitle = "Core Architecture",
        sloganPrimary = "On-Device Multi-Intent Decision Engine",
        sloganSecondary = "Single-pass forward tensor routing · Zero delay",
        sloganMission = "Executes on-device single-pass forward tensor compute across HVAC, media, navigation, seats, and windows with zero cloud dependency.",
        githubCardTitle = "GitHub Official Repository",
        githubCardSubtitle = "Source code, quantization pipeline & interaction specs",
        btnVisitGithub = "Open GitHub",
        btnCopyLink = "Copy Link",
        toastCopied = "Copied to clipboard",
        matrixSectionTitle = "Online Demos & Ecosystem",
        matrixSectionSubtitle = "Cloud trial, open model weights & HUD console",
        linkWebHudTitle = "Web HUD Online Console",
        linkWebHudSub = "Live browser inference console",
        linkModelScopeTitle = "ModelScope Studio Cloud Backend",
        linkModelScopeSub = "Cloud container endpoint & model hosting",
        linkOrgTitle = "GitHub Official Organization",
        linkOrgSub = "github.com/neura-edit",
        specsSectionTitle = "Technical Specifications",
        spec1Title = "Single-pass Forward Neural Routing",
        spec1Desc = "Based on 0.75B Transformer architecture, a single forward pass calculates all domain probabilities, eliminating token-by-token delay.",
        spec2Title = "On-Device INT8 Quantization & Gating",
        spec2Desc = "1.9GB weights run directly on device CPU with candidate gating, achieving minimal memory footprint and fast inference.",
        spec3Title = "Automotive-Grade Negation Resolution",
        spec3Desc = "Strictly distinguishes domain exclusion from sub-parameter negation, preventing false avoidance in cabin control.",
        footerVersion = "NEURA EDIT · OmniIntent v1.2.0 (Automotive Edition)",
        footerLicense = "Open Source under MIT License · 2026"
    )

    fun get(language: AppLanguage): LocalizedStrings = when (language) {
        AppLanguage.ZH -> ZH
        AppLanguage.ZHTW -> ZHTW
        AppLanguage.EN -> EN
    }

    fun getLocalizedDomainName(domainId: String, fallback: String, lang: AppLanguage): String {
        return when (domainId.lowercase()) {
            "climate" -> when (lang) {
                AppLanguage.ZH -> "空调温控"
                AppLanguage.ZHTW -> "空調溫控"
                AppLanguage.EN -> "Climate"
            }
            "music" -> when (lang) {
                AppLanguage.ZH -> "媒体音乐"
                AppLanguage.ZHTW -> "媒體音樂"
                AppLanguage.EN -> "Media/Music"
            }
            "navigation" -> when (lang) {
                AppLanguage.ZH -> "导航地图"
                AppLanguage.ZHTW -> "導航地圖"
                AppLanguage.EN -> "Navigation"
            }
            "seat" -> when (lang) {
                AppLanguage.ZH -> "座椅调节"
                AppLanguage.ZHTW -> "座椅調節"
                AppLanguage.EN -> "Seat Comfort"
            }
            "window" -> when (lang) {
                AppLanguage.ZH -> "车窗天窗"
                AppLanguage.ZHTW -> "車窗天窗"
                AppLanguage.EN -> "Windows"
            }
            "phone" -> when (lang) {
                AppLanguage.ZH -> "车载电话"
                AppLanguage.ZHTW -> "車載電話"
                AppLanguage.EN -> "Phone Calls"
            }
            "query" -> when (lang) {
                AppLanguage.ZH -> "通用问答"
                AppLanguage.ZHTW -> "通用問答"
                AppLanguage.EN -> "General Q&A"
            }
            "other" -> when (lang) {
                AppLanguage.ZH -> "其他兜底"
                AppLanguage.ZHTW -> "其他兜底"
                AppLanguage.EN -> "Other/Fallback"
            }
            else -> fallback
        }
    }

    fun getLocalizedDomainDesc(domainId: String, fallback: String, lang: AppLanguage): String {
        return when (domainId.lowercase()) {
            "climate" -> when (lang) {
                AppLanguage.ZH -> "车内温度/风速调节、除雾除霜、内外循环"
                AppLanguage.ZHTW -> "車內溫度/風速調節、除霧除霜、內外循環"
                AppLanguage.EN -> "Cabin temperature, fan speed, defogger, air circulation"
            }
            "music" -> when (lang) {
                AppLanguage.ZH -> "音乐播放、曲名/歌手搜索、曲风推荐"
                AppLanguage.ZHTW -> "音樂播放、曲名/歌手搜尋、曲風推薦"
                AppLanguage.EN -> "Music playback, artist/track search, mood recommendations"
            }
            "navigation" -> when (lang) {
                AppLanguage.ZH -> "目的地检索、路线规划、规避高速/拥堵"
                AppLanguage.ZHTW -> "目的地檢索、路線規劃、規避高速/擁堵"
                AppLanguage.EN -> "Destination search, route planning, avoiding highway/traffic"
            }
            "seat" -> when (lang) {
                AppLanguage.ZH -> "主副驾座椅加热、通风、按摩档位切换"
                AppLanguage.ZHTW -> "主副駕座椅加熱、通風、按摩檔位切換"
                AppLanguage.EN -> "Seat heating, ventilation, and massage adjustments"
            }
            "window" -> when (lang) {
                AppLanguage.ZH -> "升降车窗、打开天窗/遮阳帘、微开通风"
                AppLanguage.ZHTW -> "升降車窗、打開天窗/遮陽簾、微開通風"
                AppLanguage.EN -> "Power windows, sunroof, sunshade, slight ventilation"
            }
            "phone" -> when (lang) {
                AppLanguage.ZH -> "蓝牙拨号、联系人查找、接听与拒接"
                AppLanguage.ZHTW -> "藍牙撥號、聯絡人查詢、接聽與拒接"
                AppLanguage.EN -> "Bluetooth calling, contact search, answer and decline"
            }
            "query" -> when (lang) {
                AppLanguage.ZH -> "实时天气、时间日期、百科问答查询"
                AppLanguage.ZHTW -> "即時天氣、時間日期、百科問答查詢"
                AppLanguage.EN -> "Real-time weather, time/date, general Q&A lookup"
            }
            "other" -> when (lang) {
                AppLanguage.ZH -> "无法分类或超出车控范围的开放域输入"
                AppLanguage.ZHTW -> "無法分類或超出車控範圍的開放域輸入"
                AppLanguage.EN -> "Out-of-domain or unclassified open-ended inputs"
            }
            else -> fallback
        }
    }

    fun localizeSlotValue(raw: String?, lang: AppLanguage): String {
        if (raw == null) return ""
        var text = raw.trim()

        if (text.contains(" / ")) {
            val parts = text.split(" / ")
            text = when (lang) {
                AppLanguage.EN -> parts.last().trim()
                AppLanguage.ZH -> parts.first().trim()
                AppLanguage.ZHTW -> toTraditional(parts.first().trim())
            }
        } else {
            text = when (lang) {
                AppLanguage.EN -> translateEntityToEn(text)
                AppLanguage.ZHTW -> toTraditional(text)
                AppLanguage.ZH -> text
            }
        }

        // Clean any residual awkward parenthetical notations like (AUTO), (开), (关), (已规避外循环)
        text = text.replace(" (AUTO)", "")
            .replace("(AUTO)", "")
            .replace(" (A/C)", "")
            .replace("(A/C)", "")
            .replace(" (HEATER)", "")
            .replace("(HEATER)", "")
            .replace("(开)", "")
            .replace("(关)", "")
            .replace("(ON)", "")
            .replace("(OFF)", "")
            .replace("（默认播放热门精选）", " · 热门精选")
            .replace("（继续播放/随心听）", " · 随机播放")
            .replace("(已规避外循环)", " · 规避外循环")
            .replace("(已规避内循环)", " · 规避内循环")
            .replace("(Fresh Air Excluded)", " · Fresh Air Excluded")
            .replace("(Recirculation Excluded)", " · Recirculation Excluded")
            .replace("(Top Hits)", " · Top Hits")
            .replace("(Continue Playback)", " · Continue")
            .replace("(", "")
            .replace(")", "")
            .replace("（", "")
            .replace("）", "")
            .trim()

        return text
    }

    private fun translateEntityToEn(str: String): String = when (str.trim()) {
        "八三夭" -> "831"
        "周杰伦" -> "Jay Chou"
        "外婆的告别式" -> "Grandma's Farewell"
        "稻香" -> "Fragrance of Rice"
        "晴天" -> "Sunny Day"
        "青花瓷" -> "Blue and White Porcelain"
        "七里香" -> "Common Jasmine Orange"
        "十年" -> "Ten Years"
        "夜曲" -> "Nocturne"
        "告白气球" -> "Love Confession"
        "红豆" -> "Red Bean"
        "年少有为" -> "If I Were Young"
        "平凡之路" -> "The Ordinary Road"
        "消愁" -> "Sorrow Drowning"
        "起风了" -> "The Wind Rises"
        "主驾" -> "Driver Seat"
        "副驾" -> "Passenger Seat"
        "全车" -> "All Zones"
        "后排" -> "Rear Seats"
        "空调" -> "Climate"
        "座椅" -> "Seat"
        "车窗" -> "Windows"
        "音乐" -> "Music"
        "导航" -> "Navigation"
        "虹桥机场" -> "Hongqiao Airport"
        "北京" -> "Beijing"
        "上海" -> "Shanghai"
        "摇滚" -> "Rock"
        "爵士" -> "Jazz"
        "流行" -> "Pop"
        "说唱" -> "Hip-Hop"
        "民谣" -> "Folk"
        "轻音乐" -> "Ambient"
        "纯音乐" -> "Instrumental"
        "播放" -> "Play"
        "暂停" -> "Pause"
        "切到下一首" -> "Next Track"
        "上一首" -> "Previous Track"
        "自动" -> "Auto Mode"
        "制冷" -> "Cooling"
        "制热" -> "Heating"
        "除雾" -> "Defog"
        "除霜" -> "Defrost"
        "内循环" -> "Recirculation"
        "外循环" -> "Fresh Air"
        "开启" -> "ON"
        "关闭" -> "OFF"
        else -> str
    }

    private fun toTraditional(str: String): String {
        val map = mapOf(
            '车' to '車', '机' to '機', '开' to '開', '关' to '關', '温' to '溫',
            '调' to '調', '听' to '聽', '电' to '電', '台' to '臺', '广' to '廣',
            '导' to '導', '航' to '航', '图' to '圖', '驾' to '駕', '热' to '熱',
            '风' to '風', '窗' to '窗', '体' to '體', '乐' to '樂', '设' to '設',
            '定' to '定', '问' to '問', '题' to '題', '别' to '別', '选' to '選',
            '择' to '擇', '应' to '應', '用' to '用', '统' to '統', '确' to '確',
            '认' to '認', '进' to '進', '入' to '入', '环' to '環', '节' to '節',
            '点' to '點', '话' to '話', '联' to '聯', '系' to '繫', '发' to '發',
            '协' to '協', '同' to '同', '拟' to '擬', '总' to '總', '数' to '數',
            '线' to '線', '规' to '規', '划' to '劃', '避' to '避', '让' to '讓',
            '负' to '負', '向' to '向', '现' to '現', '状' to '狀', '维' to '維',
            '持' to '持', '断' to '斷', '执' to '執', '行' to '行', '门' to '門',
            '级' to '級', '轻' to '輕', '量' to '量', '库' to '庫', '算' to '算',
            '会' to '會', '预' to '預', '备' to '備', '码' to '碼', '录' to '錄',
            '结' to '結', '果' to '果', '简' to '簡', '繁' to '繁', '态' to '態',
            '标' to '標', '签' to '籤', '识' to '識', '构' to '構', '建' to '建'
        )
        val sb = StringBuilder(str.length)
        for (ch in str) {
            sb.append(map[ch] ?: ch)
        }
        return sb.toString()
    }
}
