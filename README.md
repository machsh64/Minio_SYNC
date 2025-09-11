MinIO 同步工具（Python）

功能概述：
- 支持本地目录与 MinIO 桶之间的单向同步（本地->MinIO 或 MinIO->本地）
- 支持镜像删除（使目标端与源端一致）
- 支持按固定周期轮询监视（--watch）
- 支持 include/exclude 通配过滤
- Windows/Unix 通用，CLI 友好

新增（GUI + mc 增量镜像）：
- 使用 `mc` 命令在 服务器A 的 MinIO 同步到 服务器B 的 MinIO
- 图形界面设置 A/B 连接、桶、是否镜像删除和每日定时
- 可保存配置，支持一键“立即同步”与“每日 HH:MM”定时

快速开始：
1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 复制并修改配置
```bash
copy config.example.yaml config.yaml
# 或手动创建并编辑 config.yaml
```

3. 运行
```bash
python -m miniosync --help
```

示例：
```bash
# 本地 -> MinIO（带镜像删除）
python -m miniosync sync up --config config.yaml --mirror

# MinIO -> 本地（只下载变化）
python -m miniosync sync down --config config.yaml

# 轮询监视，每 10 秒执行一次同步
python -m miniosync sync up --config config.yaml --watch 10
```

图形界面（A->B，经 mc）：
```bash
python -m miniosync.gui
```
界面中填写：
- mc 路径（Windows 可下载 `mc.exe` 并选择）
- 服务器 A/B：host:port 与 Access/Secret（可选 https）
- A 桶名、B 桶名（可不同）、是否镜像删除、每日时间（HH:MM）

PyInstaller 打包：
```bash
pip install pyinstaller
pyinstaller -F -w -n MinioSyncGUI -p . --collect-all customtkinter miniosync/gui.py
# 运行 dist/MinioSyncGUI.exe
```

mc 同步说明：
- 程序会执行：
  - `mc alias set a http(s)://A access secret`
  - `mc alias set b http(s)://B access secret`
  - `mc mb --ignore-existing b/<bucketB>`
  - `mc mirror --overwrite [--remove] a/<bucketA> b/<bucketB>`
- `--remove` 开启“镜像删除”以清理 B 端多余对象；未开启则为增量复制。

配置说明（config.yaml）：
```yaml
endpoint: "127.0.0.1:9000"   # MinIO 地址（host:port）
secure: false                 # 是否使用 https
access_key: "minioadmin"
secret_key: "minioadmin"

bucket: "my-bucket"          # 目标桶
prefix: "backup/"            # 可选，桶内前缀（目标路径前缀）

local_dir: "./data"          # 本地目录

include:                      # 可选，包含通配（任一匹配即包含）
  - "**/*"
exclude:                      # 可选，排除通配（优先级高于 include）
  - "**/*.tmp"

concurrency: 4                # 并发度（上传/下载）
etag_by_content: true         # 若本地文件系统不稳定，强制计算内容 MD5 比对
delete_extraneous: false      # 镜像删除：删除目标端多余文件
```

注意：
- 生产环境请妥善保管凭证，不要提交到版本库。
- 若使用 https，请将 `secure` 设置为 true，并配置证书。


