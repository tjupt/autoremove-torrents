# 开发文档

## 开发环境搭建

```bash
git clone git@github.com:tjupt/autoremove-torrents.git
cd autoremove-torrents

uv venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"   # 若无 dev extra，用下面一行
uv pip install -r dev-requirements.txt
python setup.py develop
```

---

## 测试

### 测试套件说明

| 目录 | 依赖实体客户端 | 说明 |
|------|:-----------:|------|
| `pytest/test_strategies/` | 否 | 条件/过滤器逻辑单元测试，**最常用** |
| `pytest/test_tasks/` | 否 | Task 流程测试（使用 mock 客户端） |
| `pytest/test_main/` | 否 | 配置解析与入口测试 |
| `pytest/test_clients/` | **是** | 需要真实 qBittorrent/Transmission 等实例，CI 专用 |

### 日常开发只跑策略测试

```bash
# 跑所有策略测试（无需客户端）
py.test pytest/test_strategies/ -s --log-level=INFO

# 跑单个条件的测试用例
py.test pytest/test_strategies/ -s -k "seeding_time"
```

### test_strategies 数据驱动机制

测试框架读取以下共享数据文件（位于 `pytest/test_strategies/`）：

| 文件 | 作用 |
|------|------|
| `data.json` | 模拟种子列表，包含每条种子的全部属性 |
| `environment.json` | 模拟运行环境（当前时间戳 `time.time`、磁盘用量等） |
| `clientstatus.json` | 模拟客户端全局状态（上传/下载速度、剩余空间等） |

每个条件的测试用例放在 `cases/<condition_name>/` 目录下，每个 `.yml` 文件是一个独立用例：

```yaml
test:               # 直接对应策略配置
  seeding_time: 21600

remove:             # 期望被删除的种子名称列表
  - Torrent - 1
  - Torrent - 3

remain:             # 期望保留的种子（可选，不写则不校验）
  - Torrent - 2

exceptions:         # 期望抛出的异常类名（测试异常场景时使用）
  - ConditionSyntaxError
```

---

## 新增条件（Condition）

以新增 `min_peers`（最小 peer 数）为例：

### 1. 创建条件类

新建 `autoremovetorrents/condition/minpeers.py`：

```python
from .base import Comparer, Condition

class MinPeersCondition(Condition):
    def __init__(self, threshold, comp=Comparer.LT):
        Condition.__init__(self)
        self._threshold = threshold
        self._comparer = comp

    def apply(self, client_status, torrents):
        for torrent in torrents:
            if self.compare(torrent.leecher, self._threshold, self._comparer):
                self.remove.add(torrent)
            else:
                self.remain.add(torrent)
```

规则：
- 继承 `Condition`，调用 `Condition.__init__(self)` 初始化 `self.remain` / `self.remove`
- `apply()` 遍历 `torrents`，按条件分别放入 `self.remove` 或 `self.remain`
- `client_status` 是全局客户端状态，仅 `free_space`、`download_speed` 等全局指标需要用到

### 2. 注册到 strategy.py

在 `strategy.py` 的 `_apply_conditions()` 的 `conditions` 字典中添加：

```python
from .condition.minpeers import MinPeersCondition

conditions = {
    ...
    'min_peers': MinPeersCondition,
}
```

### 3. 注册到 conditionparser.py（仅当需要支持 `remove:` DSL 表达式时）

在 `conditionparser.py` 的 `_condition_map` 中添加，并补充 PLY 语法规则。若该条件不需要出现在 `remove: xxx > yyy` 表达式中，可跳过此步。

### 4. 添加测试用例

新建 `pytest/test_strategies/cases/min_peers/test_min_peers.yml`：

```yaml
test:
  min_peers: 5

remove:
  - Torrent - 2   # leecher < 5 的种子名称（参照 data.json）
remain:
  - Torrent - 1
```

---

## 新增客户端适配器

新建 `autoremovetorrents/client/myclient.py`，实现以下接口：

```python
class MyClient(object):
    def login(self, username, password): ...
    def version(self) -> str: ...
    def api_version(self) -> str: ...
    def client_status(self) -> ClientStatus: ...
    def torrents_list(self) -> list[str]: ...          # 返回 hash 列表
    def torrent_properties(self, hash_) -> Torrent: ... # 返回填充好的 Torrent 对象
    def remove_torrents(self, hashes, delete_data) -> tuple[list, list]:
        # 返回 (成功的 hash 列表, 失败的 [{'hash': ..., 'reason': ...}] 列表)
        ...
```

`Torrent` 对象需要填充的字段参见 `torrent.py`。

然后在 `task.py` 的 `_login()` 中的 `clients` 字典注册：

```python
clients = {
    ...
    u'myclient': MyClient,
}
```

---

## HNR 条件开发说明

HNR 条件（`condition/hnr.py`）与其他条件不同，它有**外部 API 依赖**，在 `strategy.py` 中有特殊处理逻辑。

### API 接口规范

`HnrClient.check_torrents(info_hashes)` 调用的 API 需满足：

- **Method**: `POST`
- **Auth**: `Authorization: Bearer <api_token>`
- **Request body**: `{"info_hash": ["hash1", "hash2", ...]}`（每批最多 50 个）
- **Response**:
  ```json
  {
    "data": [
      {
        "torrent": {"info_hash": "abc123"},
        "status": {
          "hnr_status_code": 0,
          "hnr_status": "未触发考核"
        }
      }
    ]
  }
  ```

`HnrClient` 会在**类级别**缓存 API 响应，同一进程内不重复请求已查询过的 hash。调试时可用 `HnrClient.clear_cache()` 清除。

### HNR 条件的检查逻辑（AND 组合）

1. 先检查 `target_codes` — 状态码不匹配则直接保留
2. 状态码匹配后，依次检查 `last_activity`、`min_seed_time`、`min_upload_speed`、`min_ratio`
3. 未配置的子条件跳过（视为通过）
4. **全部通过才删除**

---

## 删除日志

程序在 `--log` 目录下同时生成两个日志文件：

- `autoremove.YYYY-MM-DD.log` — 完整运行日志
- `autoremove.deleted.YYYY-MM-DD.log` — 删除专项日志，格式：

```
INFO  REMOVED | <种子名> | Task: <任务名> | Reason: <策略名> > <条件名>
ERROR FAILED  | <种子名> | Task: <任务名> | Reason: <策略名> > <条件名> | Error: <原因>
INFO  SUMMARY | Task: <任务名> | Removed: N | Failed: N
```

删除日志由 `Logger.register_deletion_logger()` 创建，不输出到控制台。

---

## 发布新版本

### 发布步骤

```bash
# 1. 修改版本号
# 编辑 autoremovetorrents/version.py，将 __version__ 改为新版本号
# 例如：__version__ = '2.2.0'

# 2. 更新 README.md 的 changelog 部分，简述本版本改动

# 3. 提交、打 tag、推送
git add autoremovetorrents/version.py README.md
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin master --tags
```

推送带 `v*.*.*` 格式的 tag 后，`.github/workflows/publish.yml` 自动触发，完成构建并发布到 PyPI。

---

### GitHub Actions 自动发布流程

发布 workflow（`.github/workflows/publish.yml`）分两个 job：

| Job | 说明 |
|-----|------|
| `build` | 用 `uv build` 生成 `dist/` 下的 `.whl` 和 `.tar.gz`，上传为 artifact |
| `publish` | 下载 artifact，通过 OIDC Trusted Publishing 发布到 PyPI，**无需手动配置 API token** |

发布结果可在 GitHub → Actions → **Publish to PyPI** 查看。

---

### 首次配置：PyPI Trusted Publishing

首次发布前需在 PyPI 网站完成一次性配置，之后推送 tag 即可全自动发布。

**步骤：**

1. 登录 [https://pypi.org](https://pypi.org)，进入项目页面  
   → **Manage** → **Publishing**（或直接访问 `https://pypi.org/manage/project/autoremove-torrents-hnr/settings/publishing/`）

2. 点击 **Add a new publisher**，填写：

   | 字段 | 值 |
   |------|----|
   | Owner | `tjupt`（GitHub 组织或用户名） |
   | Repository | `autoremove-torrents` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

3. 保存后，GitHub Actions 使用 OIDC 令牌即可通过身份验证，无需在 GitHub Secrets 中存储任何密钥。

> **注意**：workflow 里的 `environment: pypi` 和 PyPI 上填写的 Environment name 必须一致，否则 OIDC 验证会失败。

---

### 在 GitHub 上创建 `pypi` 环境（可选但推荐）

在 GitHub 仓库 → **Settings** → **Environments** → **New environment** 中创建名为 `pypi` 的环境，并可设置：

- **Required reviewers**：需要人工审批才能触发发布（防止误操作）
- **Deployment branches**：仅允许从 `master` 分支的 tag 触发

---

### 本地手动构建与上传（备用）

正常情况下无需手动操作，仅在 CI 出现问题时使用：

```bash
# 构建
uv build
# dist/ 下会生成 .whl 和 .tar.gz

# 上传（需要 PyPI API token）
TWINE_PASSWORD=pypi-your-token-here \
  uvx twine upload dist/autoremove_torrents_hnr-X.Y.Z* -u __token__
```

PyPI API token 在 [https://pypi.org/manage/account/token/](https://pypi.org/manage/account/token/) 生成，建议限定作用域为当前项目。

---

### 常见问题

**Q: 推送 tag 后 Actions 没有触发？**  
A: 确认 tag 格式为 `vX.Y.Z`（以 `v` 开头），workflow 的触发条件是 `tags: ["v*.*.*"]`。

**Q: publish job 报 `invalid-publisher` 错误？**  
A: 检查 PyPI Trusted Publishing 配置中的 Owner / Repository / Workflow name / Environment name 是否与实际完全一致（区分大小写）。

**Q: 已发布版本能否重新覆盖？**  
A: PyPI **不允许**覆盖已发布的版本号，必须递增版本号重新发布。若发布了有问题的版本，可在 PyPI 上 yank 该版本（不会删除，但 `pip install` 默认跳过）。
