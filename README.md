# Auto Remove Torrents (H&R Version)

这是一个支持 H&R 检查的自动删种程序，基于 [autoremove-torrents](https://github.com/jerrymakesjelly/autoremove-torrents) 修改，在此感谢原作者jerrymakesjelly。

## 新增功能

v2.0.0
- 整体重构，可以根据 H&R 状态码灵活配置删除条件
- 支持多个策略组合使用
- 支持检查种子的做种时间、上传速度等条件
- 增加种子状态本地缓存，减少 API 请求次数

v1.6.1
- 支持通过 API 检查种子的 H&R 状态来删除种子

## 环境准备

本说明使用 [uv](https://docs.astral.sh/uv/) 管理 Python 与依赖。若尚未安装，请参考官方文档安装 uv。

## 安装

全局或当前环境中安装（与 `pip install` 等价，由 uv 加速解析与下载）：

```bash
uv pip install autoremove-torrents-hnr
```

仅需要命令行工具、希望隔离依赖时，可使用工具安装（可执行文件由 uv 管理）：

```bash
uv tool install autoremove-torrents-hnr
```

## 更新

```bash
uv pip install autoremove-torrents-hnr --upgrade
# 或固定版本
uv pip install autoremove-torrents-hnr==具体版本号
```

使用 `uv tool install` 安装的，可执行：

```bash
uv tool upgrade autoremove-torrents-hnr
```

## 卸载

```bash
uv pip uninstall autoremove-torrents-hnr
```

使用 `uv tool install` 安装的：

```bash
uv tool uninstall autoremove-torrents-hnr
```

## 配置示例

```yaml
my_task:
  client: qbittorrent
  host: http://127.0.0.1:7474
  username: admin
  password: password
  
  strategies:
    # 删除未触发考核的种子
    remove_untriggered_hnr:
      categories:  # 种子分类（可选）
        - TJUPT
      hnr:
        host: https://tjupt.org/api/v1/hnr.php
        api_token: your_api_token
        target_codes: 0  # 未触发考核的种子
        min_seed_time: 86400  # 做种时间大于1天将被删除
        min_upload_speed: 51200  # 上传速度小于50KB/s将被删除

    # 删除已通过考核的种子
    remove_completed_hnr:
      categories:
        - TJUPT
      hnr:
        host: https://tjupt.org/api/v1/hnr.php
        api_token: your_api_token
        target_codes: [20, 21]  # 已通过考核的种子
        last_activity: 172800  # 2天没有活动的种子将被删除
        min_upload_speed: 10240  # 上传速度小于10KB/s将被删除
        min_ratio: 1.0  # 分享率大于1.0将被删除

    # 删除考核被取消的种子
    remove_cancelled_hnr:
      categories:
        - TJUPT
      hnr:
        host: https://tjupt.org/api/v1/hnr.php
        api_token: your_api_token
        target_codes: [40, 41, 42]  # 考核被取消的种子

  delete_data: true  # 是否在删除种子的同时也删除数据
```

其他条件配置请参考原项目 [autoremove-torrents](https://autoremove-torrents.readthedocs.io/zh-cn/latest/) 的文档。

## hnr 配置说明

H&R API 接口文档：[hnr_api.md](https://github.com/tjupt/autoremove-torrents/blob/master/hnr_api.md)

在策略配置中添加 `hnr` 部分：

### 必需参数
- `host`: H&R API 地址
- `api_token`: API 访问令牌
- `target_codes`: 目标状态码，可以是单个状态码或状态码列表，具体见H&R API 接口文档：[hnr_api.md](https://github.com/tjupt/autoremove-torrents/blob/master/hnr_api.md)

### 可选参数
- `last_activity`: 种子不活跃时间限制，单位为秒
- `min_seed_time`: 最小做种时间，单位为秒
- `min_upload_speed`: 最小上传速度，单位为字节/秒
- `min_ratio`: 最小分享率

### 条件组合说明
1. 首先检查种子的 HNR 状态码是否匹配 `target_codes`
2. 如果状态码匹配，则继续检查其他配置的条件（如 `last_activity`、`min_seed_time` 等）
3. 只有当所有配置的条件都满足时，种子才会被删除
4. 未配置的条件会被跳过，不参与判断

## 使用方法
参考原项目 [autoremove-torrents](https://autoremove-torrents.readthedocs.io/zh-cn/latest/inst.html#run) 的运行说明
```bash
# 预览模式（不会真正删除）
autoremove-torrents --view --conf=config.yml

# 正常运行
autoremove-torrents --conf=config.yml
```

不事先安装包、临时运行一次（由 uv 拉取依赖并执行；包名与可执行名不同，需指定 `--from`）：

```bash
uvx --from autoremove-torrents-hnr autoremove-torrents --view --conf=config.yml
uvx --from autoremove-torrents-hnr autoremove-torrents --conf=config.yml
```

从本仓库源码安装并开发调试：

```bash
cd /path/to/autoremove-torrents
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e .
autoremove-torrents --conf=config.yml
```

## 日志

```bash
autoremove-torrents --conf=config.yml --log=logs/autoremove.log --debug
```

使用 `uvx` 时同样追加参数即可，例如：

```bash
uvx --from autoremove-torrents-hnr autoremove-torrents --conf=config.yml --log=logs/autoremove.log --debug
```

## 定时自动运行

定时任务里的环境通常**没有**你在终端里配置的 `PATH`（例如 `uv tool` 会把可执行文件放在 `~/.local/bin`）。请尽量使用**配置文件与日志的绝对路径**，并对 `autoremove-torrents` 使用 **`which autoremove-torrents`（或 `~/.local/bin/autoremove-torrents`）** 得到的绝对路径；若用虚拟环境，则用 **`/path/to/.venv/bin/autoremove-torrents`**。首次上线建议仍用 `--view` 在终端确认行为，再改为正式删除。

### Linux / macOS：cron

编辑当前用户的 crontab：

```bash
crontab -e
```

示例：**每 20 分钟**执行一次（请把路径改成你机器上的真实路径）：

```cron
*/20 * * * * /home/you/.local/bin/autoremove-torrents --conf=/home/you/autoremove/config.yml --log=/home/you/autoremove/logs/run.log >> /home/you/autoremove/logs/cron.log 2>&1
```

`cron` 表达式从左到右依次为：分、时、日、月、星期。`*/20` 表示从 0 分起每隔 20 分钟触发一次。若需其他周期可自行改写前两个字段（例如每天 03:15 一次为 `15 3 * * *`）。

### macOS：launchd（推荐）

比 `cron` 更易被系统唤醒、日志与权限行为更一致。新建 `~/Library/LaunchAgents/org.tjupt.autoremove-torrents.plist`（标签与文件名可自定）。下方示例用 `StartInterval` 的 `1200`（即 20×60 秒）实现约每 20 分钟触发一次：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>org.tjupt.autoremove-torrents</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/.local/bin/autoremove-torrents</string>
    <string>--conf</string>
    <string>/Users/you/autoremove/config.yml</string>
    <string>--log</string>
    <string>/Users/you/autoremove/logs/run.log</string>
  </array>
  <key>StartInterval</key>
  <integer>1200</integer>
  <key>StandardOutPath</key>
  <string>/Users/you/autoremove/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/you/autoremove/logs/launchd.err.log</string>
</dict>
</plist>
```

加载与卸载：

```bash
launchctl load ~/Library/LaunchAgents/org.tjupt.autoremove-torrents.plist
launchctl unload ~/Library/LaunchAgents/org.tjupt.autoremove-torrents.plist
```

修改 plist 后需 `unload` 再 `load` 才会生效。

`StartInterval` 表示上次任务**成功结束后**再等待的秒数，与 cron 按钟表对齐到每小时的 0、20、40 分略有不同；若必须与钟表对齐，可优先使用上文 **cron** 或 Debian 上的 **systemd timer**。

### Debian / Ubuntu：systemd 定时器（示例：每 20 分钟）

适合长期跑在 Linux 服务器、需要与 `journalctl` / `systemctl` 统一管理的场景。以下文件需 **root** 创建或修改。示例假定以 **root** 执行 `uv tool install autoremove-torrents-hnr`，默认可执行文件为 **`/root/.local/bin/autoremove-torrents`**；若改过 `UV_TOOL_DIR` / `XDG_*`，在 root 下用 `uv tool dir --bin` 或 `readlink -f "$(command -v autoremove-torrents)"` 核对后再写入 `ExecStart`。`--conf` / `--log` 请按实际部署改成绝对路径。长期以 root 跑删种权限较大，生产环境更稳妥的做法是改为**普通用户**安装工具并在 `[Service]` 里设置 `User=` 指向该用户。

**1）** `/etc/systemd/system/autoremove-torrents.service`

```ini
[Unit]
Description=Auto remove torrents (HNR)
Wants=network-online.target
After=network-online.target

[Service]
# Type=oneshot
# User=you
# Group=you
# 使用绝对路径；若在 venv 中安装则改为 /home/you/autoremove/.venv/bin/autoremove-torrents
# ExecStart=/home/you/.local/bin/autoremove-torrents --conf=/home/you/autoremove/config.yml --log=/home/you/autoremove/logs/run.log
Environment=HOME=/root
ExecStart=/root/.local/bin/autoremove-torrents --conf=/root/autoremove/config.yml --log=/root/autoremove/logs/run.log
```

**2）** `/etc/systemd/system/autoremove-torrents.timer`

```ini
[Unit]
Description=Run autoremove-torrents every 20 minutes

[Timer]
# 对齐到每小时的 0、20、40 分（与 cron */20 的常见语义一致）
OnCalendar=*-*-* *:00,20,40:00
Persistent=true

[Install]
WantedBy=timers.target
```

**3）** 加载并启用定时器：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now autoremove-torrents.timer
systemctl list-timers autoremove-torrents.timer
journalctl -u autoremove-torrents.service -n 50 --no-pager
```

停用：`sudo systemctl disable --now autoremove-torrents.timer`。若 systemd 版本较新且希望用步进写法，可将 `OnCalendar=` 改为 `*-*-* *:0/20:00`（与上面列表形式等价，视本机 `systemd.time(7)` 说明为准）。

### Windows：任务计划程序

打开「任务计划程序」，新建任务：触发器选择「每天」后在「高级设置」中将任务配置为**每 20 分钟重复一次**（或新建「一次」触发器并设置重复间隔 20 分钟，按向导界面为准）；操作选择「启动程序」，程序填 `autoremove-torrents` 的完整路径（或 `cmd.exe` / `powershell.exe` 配合参数），参数示例：`--conf=C:\path\to\config.yml --log=C:\path\to\run.log`。注意任务运行账户下的 `PATH` 是否包含该可执行文件所在目录。

## 项目结构
### 1 客户端模块 (client/)
- hnr_api.py: H&R API 客户端，用于查询种子的 H&R 状态
- 其他客户端适配器（如 qBittorrent, Transmission 等）
### 2 条件模块 (condition/)
- base.py: 条件基类，定义了条件的基本接口
- hnr.py: H&R 条件检查实现
- 其他条件实现（如分享率、做种时间等）
### 3 核心功能文件
- strategy.py: 策略执行器，负责：
- 应用各种条件
- 管理种子的保留和删除列表
- 执行删除操作

- conditionparser.py: 条件解析器，负责：
- 解析配置文件中的条件
- 创建对应的条件实例
- 处理条件组合

## 工作流程
### 1 配置加载
- 读取 config.yml
- 解析任务和策略配置
### 2 客户端连接
- 根据配置创建对应的客户端实例
- 建立连接并验证
### 3 策略执行
- 获取种子列表
- 应用分类过滤
- 执行条件检查
- 确定删除列表
### 4 删除操作
- 执行种子删除
- 记录操作日志

## 许可证

MIT License