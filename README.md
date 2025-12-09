# lan-hub

`lan-hub` 是一套在局域网内快速搭建“个人开发中心”的脚本和配置文件集合，核心目标：

- 以一台 Rocky Linux 机器（Tokamak-4）作为中心节点（开发中心）；
- 在任意局域网中，通过统一域名访问：`tokamak-4-rocky.local` / `tokamak-4-rocky`；
- 为 Windows / macOS / Linux / WSL 提供一致的接入方式；
- 为 GitLab 等服务提供稳定的主机名，避免 IP 变化导致 clone/push 失败。

中心节点通常提供的能力包括：

- SSH 登录（远程维护服务器）；
- GitLab 代码托管（推荐方式）；
- 也可以扩展为文件共享、内部 Web 服务等。

`lan-hub` 本身只负责**域名和主机名的统一**，以及客户端 `/etc/hosts`/`hosts` 的自动维护，不直接管理 GitLab 或其他服务的安装逻辑。

---

## 1. 目录结构

```text
lan-hub/
  server/                 # 在 Rocky 上配置统一主机名与 mDNS
    setup_lanhub_server.sh

  client/                 # 各类客户端的接入脚本
    lanhub_client_unix.sh   # Linux / WSL / macOS
    lanhub_client_win.py    # Windows

  docs/                   # 详细文档
    DEPLOY_ROCKY.md       # Rocky 开发中心部署手册
    CLIENT_SETUP.md       # 客户端接入手册
```

---

## 2. 快速开始

### 2.1 在 Rocky（Tokamak-4）上部署开发中心基础环境

在 Tokamak-4 上执行：

```bash
git clone <your_repo_url> lan-hub
cd lan-hub/server
sudo ./setup_lanhub_server.sh
```

脚本会完成：

* 设置主机名为 `tokamak-4-rocky`；
* 安装 `avahi` / `nss-mdns` 并启用 mDNS；
* 调整 `/etc/nsswitch.conf`，让 `tokamak-4-rocky.local` 在局域网内可被解析。

此后，在同一局域网内其它机器应能成功：

```bash
ping tokamak-4-rocky.local
ping tokamak-4-rocky
```

> GitLab、Samba、HTTP 等服务请按自身需求单独安装。
> 推荐将 GitLab 的 `external_url` 与 `gitlab_ssh_host` 都配置为 `tokamak-4-rocky.local`，这样网页端的 “Clone with SSH” 会自动使用统一主机名。

详细部署步骤见 `docs/DEPLOY_ROCKY.md`。

---

### 2.2 客户端接入（Linux / WSL / macOS）

在任意 Unix 类客户端上：

```bash
git clone <your_repo_url> lan-hub
cd lan-hub/client
sudo ./lanhub_client_unix.sh
```

脚本会：

* 解析 `tokamak-4-rocky.local` 当前 IP；
* 备份 `/etc/hosts`；
* 删除旧的 `tokamak-4-rocky` 相关记录；
* 写入一条新的映射：

  ```text
  <当前IP> tokamak-4-rocky tokamak-4-rocky.local
  ```

验证：

```bash
ping tokamak-4-rocky
ping tokamak-4-rocky.local
```

之后即可使用统一主机名访问服务器，例如：

```bash
ssh <user>@tokamak-4-rocky.local
ssh git@tokamak-4-rocky.local
```

更多细节与 SSH key 配置流程见 `docs/CLIENT_SETUP.md`。

---

### 2.3 Windows 客户端接入

前提条件：

* 已安装 Python 3；
* PowerShell 以管理员权限运行（用于修改 `C:\Windows\System32\drivers\etc\hosts`）。

步骤：

```powershell
git clone <your_repo_url> lan-hub
cd lan-hub\client
python lanhub_client_win.py
```

脚本会：

* 使用 `ping tokamak-4-rocky.local` 获取当前 IP；
* 清理旧的 `tokamak-4-rocky` 相关 hosts 条目；
* 写入新的映射：

  ```text
  <当前IP> tokamak-4-rocky tokamak-4-rocky.local
  ```

验证：

```powershell
ping tokamak-4-rocky
ping tokamak-4-rocky.local
```

之后即可在 Windows 上通过统一主机名访问服务器，例如：

```powershell
ssh <user>@tokamak-4-rocky.local
```

Git 操作示例（以 GitLab 为例）：

```powershell
git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git
```

---

## 3. 与 GitLab 集成时的命名规则

在 GitLab 中，每个项目有两个概念：

* **Project name（显示名）**：例如 `HPC_project`，保留大小写，仅用于界面展示；
* **Project path（路径）**：例如 `hpc_project`，用于 URL 和 ssh 地址。

GitLab 会自动将 Project path 规范化为“小写 + 去掉空格”，因此：

* 即使项目名是 `HPC_project`，仓库地址也会是：

  ```text
  git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git
  ```

本项目约定：

1. 文档和脚本中出现的仓库地址一律使用小写 `project_path`；
2. 若希望本地目录名保留大写，可以在 `git clone` 时指定目录名，例如：

   ```bash
   git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git HPC_project
   ```

---

## 4. 适用场景

* 小团队在办公室 / 实验室内部署统一的开发中心（GitLab + 文档 + 文件共享等），LAN 内访问统一使用 `tokamak-4-rocky.local`；
* 服务器是可移动的笔记本（Tokamak-4），在不同局域网之间迁移，只需重新运行客户端脚本更新 hosts 即可；
* 不依赖公网 DNS 和第三方云服务，所有配置完全掌握在自己手里。

---

## 5. 后续计划（可选）

* 增加自动安装 / 升级 GitLab 的脚本；
* 增加对 Samba / NFS 等共享服务的示例配置；
* 增加一键检查脚本（自检 ping / ssh / GitLab Web / Git SSH）。

欢迎在实际使用过程中补充更多脚本和文档。
