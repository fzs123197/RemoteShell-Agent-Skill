---
name: remote-shell-agent
description: >
  搭建基于 Python socket 的远程命令行系统，包含被控端服务端和多种控制端客户端。
  支持三种使用模式：Agent 纯 API 调用（结构化 JSON 返回）、人工交互式终端、命令行单条执行。
  用于在远程受控机器上执行系统 shell 命令（如 dir、ls、cd、ipconfig），返回 stdout、stderr 和当前工作目录。
  被控端带 token 鉴权，支持长输出分片接收，服务端维持 cd 状态。
  在以下场景触发本 Skill：
  (1) 用户需要远程执行命令或远程控制机器，
  (2) 用户需要为 Agent 提供远程 shell 工具能力，
  (3) 用户提到远程命令行、remote shell、远程 CMD / PowerShell / Bash，
  (4) 用户需要跨机器执行脚本或收集远程机器信息。
  仅用于用户自己可控的测试设备，严禁未授权使用。
---

# Remote Shell Agent远程命令行

⚠️ **安全警告：仅用于自己可控设备。未经授权控制他人计算机属于违法行为。**

## 文件结构

```
scripts/
  agent_server.py              # 被控端服务端（部署在远程机器）
  agent_client.py              # Agent 纯 API 客户端（Python 类调用）
  agent_client_interactive.py  # 两用客户端（Agent API + 人工交互式终端）
README.md
remote-shell-agent.skill       # 封装好的Skill
```

## 快速开始

### 1. 部署被控端

在被控制的远程机器上运行 `scripts/agent_server.py`：

```bash
python agent_server.py
```

默认监听 `0.0.0.0:9999`。**必须先修改文件中的 `AUTH_TOKEN`**，使用强密码。

同一局域网或内网穿透环境下，控制端通过 IP 连接即可。

### 2. 使用控制端

**模式 A：Agent 纯 API 调用**（推荐，无交互，函数式调用）

```python
from scripts.agent_client import RemoteShellAgentClient

cli = RemoteShellAgentClient("192.168.1.100", 9999, "YOUR_SECRET_TOKEN")
cli.connect()
res = cli.run_cmd("ipconfig")
print(res["stdout"])   # 标准输出
print(res["stderr"])   # 错误输出
print(res["cwd"])      # 当前工作目录
print(res["success"])  # 是否成功
cli.close()
```

`run_cmd()` 返回结构化字典，适合 LLM Agent function-call 直接解析。

**模式 B：人工交互式终端**

```bash
python scripts/agent_client_interactive.py --host 192.168.1.100 --token YOUR_SECRET_TOKEN
```

进入 `remote>` 提示符，可输入命令实时交互，输入 `exit` 退出。

**模式 C：命令行单条执行**

```bash
python scripts/agent_client_interactive.py --host 192.168.1.100 --token YOUR_SECRET_TOKEN --cmd "dir"
```

## 核心特性

- **非交互式函数调用**：`agent_client.py` 完全函数化，Agent 直接实例化调用 `run_cmd(cmd)`
- **Token 鉴权**：连接时先校验 `AUTH_TOKEN`，防止外部非法连接
- **结构化 JSON 返回**：包含 `success`、`stdout`、`stderr`、`cwd`，Agent 易于解析
- **服务端保存工作目录**：`cd` 命令生效，目录状态在连接会话中保持
- **消息结束标记协议**：`\n###END###\n` 解决 socket 粘包和大输出接收不全问题
- **超时保护**：`communicate(timeout=120)`，防止命令卡死
- **错误封装**：命令执行错误封装进返回字典，不会直接抛异常中断 Agent（网络异常除外）

## 安全配置

1. **修改 AUTH_TOKEN**：默认 `MY_AGENT_SECRET_123456` 必须替换为强密码，被控端和控制端保持一致。
2. **防火墙放行端口**：仅放行必要的内网端口，不要将服务端暴露到公网无防护环境。
3. **网络环境**：仅在内网或可信网络使用；公网必须使用 SSL/TLS 加密（如需此功能，使用 `ssl.wrap_socket` 包装 socket）。
4. **shell=True 风险**：被控端使用 `shell=True` 执行命令，存在命令注入风险，仅限可信 Agent 使用。

## 已知限制

- **明文传输**：未加 SSL，公网环境数据可能被嗅探。
- **单连接模型**：一个被控端同一时刻只处理一个控制端连接。
- **无断线自动重连**：控制端需自行捕获异常后重新 `connect()`。
- **每次新建连接 cd 失效**：如果 Agent 每次调用都新建 `RemoteShellAgentClient` 实例，服务端会话销毁导致 `cd` 状态丢失。解决方案：客户端层复用同一实例的长连接单例，或每次命令附带完整工作目录。
- **大输出风险**：虽然通过结束标记协议改善了粘包问题，但极端大输出仍可能受限于接收缓冲区。

## 扩展方向

如需以下增强功能，按对应方案实现：
- **SSL 加密**：使用 `ssl.wrap_socket()` 包装服务端和客户端 socket。
- **长连接单例**：将 `RemoteShellAgentClient` 实例作为全局变量复用，避免每次新建连接。
- **断线重连**：在 `run_cmd()` 外层捕获 `ConnectionError` / `IOError`，自动 `connect()` 重试。
- **多客户端并发**：服务端使用 `threading.Thread` 为每个连接创建独立线程。
