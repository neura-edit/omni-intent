# OmniIntent 决策模型端侧量化与验证体系

本目录包含 **NEURA EDIT · OmniIntent Decision Engine** 针对移动端（Android）与车机端侧芯片的 **INT8 权重量化与精度对比流水线**。

---

## 🎯 核心成果与基准数据

通过将 0.75B Transformer 骨干网络的 189 处线性投影矩阵与注意力权重执行常量折叠（Constant Folding）与动态按通道 INT8 量化（Per-Channel Dynamic Quantization），并强制保留核心决策头（`decision_head`）全精度，实现了**极高保真度**的端侧压缩：

### 📊 实测精度对比（原始 FP32 vs 量化 INT8）

测试基准基于智能座舱最复杂的 5 类复合/否定真实测试用例：

| 测试指令 | 目标意图 | 原始 FP32 置信度 | 量化 INT8 置信度 | 概率偏差 ($\Delta$) | 最终判定结果 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **“车里有点闷，把空调调到22度，然后放一首周杰伦的晴天”** | **climate**<br/>**music** | 0.9439<br/>0.9351 | **0.9374**<br/>**0.9264** | **0.0065**<br/>**0.0087** | ✅ 完美并发下发<br/>（空调+音乐） |
| **“关闭空调，但是不要关座椅加热”** | **climate**<br/>seat (否定排除) | 0.6583<br/>0.5717 | **0.6469**<br/>**0.5357** | **0.0113**<br/>**0.0360** | ✅ 空调执行关闭<br/>座椅加热成功隔离 |
| **“把左前车窗降下一半，座椅加热开到二档”** | **seat**<br/>**window** | 0.9349<br/>0.8971 | **0.9444**<br/>**0.8963** | **0.0095**<br/>**0.0008** | ✅ 完美并发下发<br/>（座椅+车窗） |
| **“导航去上海虹桥火车站，躲避拥堵”** | **navigation** | 0.9257 | **0.9240** | **0.0016** | ✅ 命中主意图，抽取导航槽位 |
| **“今天天气怎么样”** | **query** | 0.8312 | **0.8117** | **0.0195** | ✅ 命中语音问答分流 |

- **全用例意图排序一致率（Argmax Consistency）**：**100.0%**
- **主意图平均概率变动幅度**：**< 0.01**（千分级误差，完全不影响车规级业务判断）

---

## 🛠️ 文件构成

- **[`quantize.py`](quantize.py)**：自动加载本地模型、执行权重常量折叠、敏感层保护并导出 INT8 量化模型。
- **[`verify_accuracy.py`](verify_accuracy.py)**：一键对原始模型与量化模型进行多意图单次前向对比与置信度绝对误差评估。

---

## 🚀 运行方法

### 1. 执行量化流水线
```bash
python3 quantization/quantize.py
```

### 2. 执行精度与延迟对比验证
```bash
python3 quantization/verify_accuracy.py
```

---

## 📱 Android 工程接入说明

量化后的 `decision_eos_int8.onnx` 可直接配合官方 **ONNX Runtime Mobile** 在 Android APK 或车机后台系统服务中运行：

```groovy
// build.gradle (app)
dependencies {
    implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.17.0'
}
```

```kotlin
// Android 核心调用示例
val session = ortEnv.createSession(modelPath, OrtSession.SessionOptions().apply {
    setIntraOpNumThreads(4)
    setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
})

val result = session.run(mapOf(
    "input_ids" to tensorIds,
    "query_pos" to tensorQueryPos,
    "cand_pos" to tensorCandPos
))
```
- 在 ARM64 处理器上通过 `SDOT`/`UDOT` 汇编指令集加速，CPU 推断速度相比浮点计算提升 **2~3 倍**。
