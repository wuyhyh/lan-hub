# lan-hub

`lan-hub` 是一套在局域网内快速搭建“个人开发中心”的脚本和配置文件集合，核心目标：

- 以一台 Rocky Linux 机器作为中心节点（开发中心）；
- 在任意局域网中，通过统一域名访问：`Tokamak-4-rocky.local`；
- 为 Windows / macOS / Linux / WSL 提供一致的接入方式。

中心节点提供的能力：

- SSH 登录与 Git 仓库托管（裸仓库）
- Samba 文件共享（跨 Windows / Linux / macOS）
- HTTP 文档浏览服务（Notebook / Sphinx 等）

---

## 目录结构

```text
lan-hub/
  server/      # 在 Rocky 上一键部署开发中心
    bootstrap_rocky.sh
    rocky-config.yaml
    docs-http.service
  client/      # 各类客户端的接入脚本
    setup_unix_client.sh
    win_update_rocky_hosts.py
  docs/        # 详细文档
    DEPLOY_ROCKY.md       # Rocky 开发中心部署手册
    CLIENT_SETUP.md       # 客户端接入手册
```

---

## 快速开始

### 1. 在 Rocky 上部署开发中心

```bash
git clone <your_repo_url> lan-hub
cd lan-hub/server
sudo ./bootstrap_rocky.sh
```

执行完成后，在同一局域网内，可通过：

* `ssh <user>@Tokamak-4-rocky.local`
* `ssh git@Tokamak-4-rocky.local:/home/git/repos/demo.git`
* `\\Tokamak-4-rocky.local\devshare`
* `http://Tokamak-4-rocky.local:8000/`

访问开发中心。

详细说明见 `docs/DEPLOY_ROCKY.md`。

### 2. 客户端接入

在客户端（Linux / macOS / 另一台 Rocky / WSL 等）：

```bash
cd lan-hub/client
sudo ./setup_unix_client.sh   # 或按文档手工配置
```

在 Windows 上：

```powershell
cd lan-hub\client
python win_update_rocky_hosts.py   # 以管理员权限运行（可选）
```

更多细节与排错方法见 `docs/CLIENT_SETUP.md`。

---

## 适用场景

* 小团队在办公室 / 实验室内部署统一的 Git + 文档 + 文件共享中心；
* 主机可物理移动（例如笔记本 Rocky Server），在不同局域网之间迁移使用；
* 不依赖任何第三方云服务，所有配置和逻辑完全掌握在自己手中。
