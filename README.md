# 车机语音意图测试台 · 部署与使用说明

基于 Ollaya 的 `decision:eos` 模型（0.75B 决策模型，一次前向传播输出类型化判定），
输入一句话，同时给出**主意图分布（choice）**和**多标签检出（noul）**，并显示判断耗时。

---

## 一、本目录文件

| 文件 | 作用 |
|---|---|
| `app.py` | 全部代码。单文件、纯 Python 标准库、零第三方依赖 |
| `config.json` | 功能域配置（页面上增删改会写回此文件；缺失时自动生成默认 8 域） |

## 二、运行条件

| 条件 | 要求 | 说明 |
|---|---|---|
| Python | ≥ 3.7（本机 3.12.3） | 只用标准库，无需 pip install |
| Ollaya | ≥ 0.7.0 | 注意是 **ollaya**（ollaya.dev，端口 11435），不是 ollama（ollama.com，端口 11434），两者是不同软件 |
| 模型 | `decision:eos` | 约 1.5 GB，权重从 HuggingFace 下载 |

## 三、启动步骤

```bash
# 1. 启动 ollaya 守护进程（Linux 安装脚本默认已注册 systemd 服务）
systemctl status ollaya        # 不在则: ollaya serve &

# 2. 拉模型（首次，约 1.5GB）
ollaya pull decision:eos

# 3. 启动本网站
python3 app.py                 # 监听 0.0.0.0:8080
```

访问：<http://localhost:8080>（同网段设备用服务器 IP 访问，如 http://172.20.101.56:8080）

## 四、国内网络拉模型的坑（重要）

模型权重从 `huggingface.co` 下载，国内 DNS 常被污染（解析到错误 IP），
导致 `ollaya pull` 卡在 0% 不动。原因：ollaya 守护进程是 systemd 服务，
**不继承终端里的代理环境变量**。修法——给守护进程注入代理：

```bash
sudo mkdir -p /etc/systemd/system/ollaya.service.d
sudo tee /etc/systemd/system/ollaya.service.d/proxy.conf <<'EOF'
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:2080/"
Environment="HTTPS_PROXY=http://127.0.0.1:2080/"
Environment="NO_PROXY=localhost,127.0.0.1,::1"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollaya
```

> `2080` 换成自己机器的代理端口。验证：`tr '\0' '\n' < /proc/$(pgrep -x ollaya)/environ | grep -i proxy`

## 五、移植到其他电脑

1. 拷贝本目录两个文件（`app.py` + `config.json`）
2. 新机器满足第二节条件后，按第三节启动
3. 或者离线搬模型：把已下载的模型目录整体拷贝过去
   （系统服务安装在 `/usr/share/ollaya/.ollaya/models`，用户安装在 `~/.ollaya/models`）
4. 也可让网站指向远端 ollaya：改 `app.py` 顶部 `OLLAYA_URL`（默认 `http://127.0.0.1:11435`）
   ——但 ollaya 默认只绑 127.0.0.1，对外开放需改其 `OLLAYA_HOST`，不建议

## 六、页面功能

- **功能域管理**（页面底部）：增/删/改功能域，写入 `config.json`，对下一次判断立即生效；
  `other` 为兜底类不可删除；域名要求小写字母开头的 `a-z0-9_`
- **判定阈值**（实测校准值）：noul ≥ 0.70 记 YES；0.50–0.70 为灰区（建议走兜底）
- **耗时**：端到端（服务端实测）/ 模型耗时（ollaya 返回的 total_duration）/ 输入 tokens
- CPU 参考性能：7 问合一约 4~5s，首次冷加载约 16s；NVIDIA GPU 上为毫秒级

## 七、HTTP 接口

```bash
# 判断一句话
curl -s localhost:8080/api/decide -H "Content-Type: application/json" \
     -d '{"text":"打开空调，然后播放周杰伦的歌"}'

# 读取 / 增改 / 删除 功能域
curl -s localhost:8080/api/config
curl -s -X POST localhost:8080/api/config/intent -H "Content-Type: application/json" \
     -d '{"name":"defroster","desc":"除雾、除霜相关控制","in_choice":true,"in_noul":true}'
curl -s -X DELETE localhost:8080/api/config/intent -H "Content-Type: application/json" \
     -d '{"name":"defroster"}'
```

## 八、已知边界（实测结论）

- ✅ 多标签检出、否定语义（区分"提到"与"要求执行"）表现好
- ❌ 不理解指令先后顺序（"先 A 再 B" 会判反），顺序需上层规则/LLM 处理
- ⚠️ 条件句（"如果太热就…"）在无关域上可能出假阳性
- ❌ 不抽槽位（destination、temperature 等），只做路由判定
