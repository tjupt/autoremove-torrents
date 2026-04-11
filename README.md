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