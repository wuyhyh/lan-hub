# 客户端接入手册

本文档描述 Windows、WSL、Linux、macOS 客户端如何接入 Tokamak-4 开发中心，包括：

- 使用统一域名访问服务器；
- 配置 SSH key 并访问 GitLab；
- 针对 WSL 与 Windows 分别配置的注意事项；
- GitLab 项目路径小写的说明。

## 1. 统一访问约定

无论 Windows、WSL 还是 macOS / Linux，统一使用以下名称访问服务器：

- FQDN：`tokamak-4-rocky.local`
- 短名：`tokamak-4-rocky`

Git 仓库访问一律使用：

```text
git@tokamak-4-rocky.local:<group>/<project_path>.git
````

> 说明：`project_path` 固定为小写，和 GitLab UI 中显示的路径一致。
> 例如项目显示名 `HPC_project`，路径为 `hpc_project`，仓库地址为
> `git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git`。

## 2. Windows 客户端接入流程

### 2.1 前提条件

* 已连接到与 Tokamak-4 相同的局域网（或 VPN）；
* 已安装：

    * Git for Windows（包含 OpenSSH）；
    * Python 3（用于运行 hosts 更新脚本）。

### 2.2 更新 hosts（统一域名）

1. 将仓库中的 `client/lanhub_client_win.py` 拷贝到本地任意目录；
2. 以管理员身份打开 PowerShell；
3. 执行：

   ```powershell
   cd 路径\到\脚本目录
   python lanhub_client_win.py
   ```

脚本会：

* 通过 `ping tokamak-4-rocky.local` 获取当前 IP；
* 清理原来 hosts 中含有 `tokamak-4-rocky` 的旧记录；
* 写入一条新记录，例如：

  ```text
  192.168.1.6 tokamak-4-rocky tokamak-4-rocky.local
  ```

验证：

```powershell
ping tokamak-4-rocky
ping tokamak-4-rocky.local
```

### 2.3 生成 SSH key

在 PowerShell 或 Git Bash 中执行：

```bash
ssh-keygen -t ed25519 -C "你的公司邮箱，例如 wuyuhang@aerospace.center.com"
```

一路回车，默认生成：

* 私钥：`C:\Users\<用户名>\.ssh\id_ed25519`
* 公钥：`C:\Users\<用户名>\.ssh\id_ed25519.pub`

查看公钥内容并复制：

```bash
cat ~/.ssh/id_ed25519.pub
```

### 2.4 在 GitLab 中添加 SSH key

1. 浏览器访问 `http://tokamak-4-rocky.local`；
2. 登录自己的 GitLab 账号；
3. 右上角头像 → **Preferences** → **SSH Keys**；
4. 将 `id_ed25519.pub` 的内容粘贴进去，Title 建议写明机器名，例如 `Tokamak-1-Windows`；
5. 保存。

### 2.5 验证 SSH 连接与克隆仓库

在 PowerShell / Git Bash 中：

```bash
ssh -T git@tokamak-4-rocky.local
```

预期输出类似：

```text
Welcome to GitLab, @wuyuhang!
```

然后即可克隆仓库，例如：

```bash
git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git
```

如需本地目录名保持大写，可以：

```bash
git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git HPC_project
```

## 3. WSL 客户端接入流程

WSL 的网络与 Windows 共用，但 **WSL 与 Windows 各自有独立的 `~/.ssh`**。
因此：

* 域名解析要在 WSL 中单独确认；
* SSH key 也需要在 WSL 内单独生成并添加到 GitLab。

### 3.1 更新 hosts（统一域名）

1. 在 WSL 中进入仓库目录 `client/`；
2. 以 root 权限运行脚本：

   ```bash
   cd client
   sudo ./lanhub_client_unix.sh
   ```

脚本会：

* 解析 `tokamak-4-rocky.local` 的 IP；
* 备份 `/etc/hosts` 到 `/etc/hosts.bak.*`；
* 删除其中包含 `tokamak-4-rocky` 的旧记录；
* 写入形如：

  ```text
  192.168.1.6 tokamak-4-rocky tokamak-4-rocky.local
  ```

验证：

```bash
ping tokamak-4-rocky
ping tokamak-4-rocky.local
```

### 3.2 在 WSL 中生成 SSH key

注意：**Windows 的 key 无法直接被 WSL 自动使用**，需要在 WSL 内单独生成一份。

```bash
ssh-keygen -t ed25519 -C "wuyuhang@aerospace.center.com"
# 默认生成 ~/.ssh/id_ed25519 和 ~/.ssh/id_ed25519.pub
cat ~/.ssh/id_ed25519.pub
```

将公钥内容复制到 GitLab（步骤同上，可使用不同 Title，例如 `Tokamak-1-WSL`）。

### 3.3 验证与克隆

在 WSL 中执行：

```bash
ssh -T git@tokamak-4-rocky.local
```

确认输出 `Welcome to GitLab, @用户名!` 后，即可克隆仓库：

```bash
git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git
```

后续 `git fetch`、`git push` 均与普通 Linux 环境一致。

## 4. Linux / macOS 物理机接入流程

Linux 与 macOS 的流程与 WSL 类似：

1. 确保能通过 mDNS 直接解析 `tokamak-4-rocky.local`：

    * 有些发行版默认支持；
    * 如希望固定映射，可直接使用 `client/lanhub_client_unix.sh`，以 root 运行一次。
2. 生成 SSH key：

   ```bash
   ssh-keygen -t ed25519 -C "你的邮箱"
   cat ~/.ssh/id_ed25519.pub
   ```
3. 将公钥添加到 GitLab；
4. 验证：

   ```bash
   ssh -T git@tokamak-4-rocky.local
   ```
5. 克隆仓库：

   ```bash
   git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git
   ```

## 5. GitLab 项目路径小写说明与约定

### 5.1 项目名与路径的区别

在 GitLab 中，每个项目有两个关键字段：

* **Name（项目名）**：显示名，可包含大写字母，例如 `HPC_project`；
* **Path（项目路径）**：用于 URL 和 SSH 地址的标识。

GitLab 会自动将 Path 规范化为：

* 全部小写；
* 空格替换为 `-`。

因此，项目名与路径的典型对应关系为：

| 项目名（Name）     | 项目路径（Path）    | SSH 地址示例                                                    |
| ------------- | ------------- | ----------------------------------------------------------- |
| `HPC_project` | `hpc_project` | `git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git` |
| `LAN-hub`     | `lan-hub`     | `git@tokamak-4-rocky.local:aerospacecenter/lan-hub.git`     |

### 5.2 项目命名约定

1. 在 GitLab 创建项目时：

    * Name 可以使用大写，如 `HPC_project`，方便阅读；
    * Path 建议直接按小写填写，例如 `hpc_project`，与自动转换结果一致。
2. 文档中所有仓库地址一律使用小写 path。
3. 本地目录名如果需要保持大写，可以在 `git clone` 时手工指定，不影响远端仓库路径。

## 6. 常见问题排查

### 6.1 ping 不通 tokamak-4-rocky.local

* 先确认服务器 Tokamak-4 已经运行 `avahi-daemon`；
* 在客户端运行对应的 hosts 更新脚本；
* 同一网段下优先测试 `ping tokamak-4-rocky.local`，如果仍不通，再检查：

    * 是否同一 WiFi / VLAN；
    * 客户端本机防火墙是否过度拦截 mDNS。

### 6.2 ssh [git@tokamak-4-rocky.local](mailto:git@tokamak-4-rocky.local) 提示 `Permission denied (publickey)`

* 确认当前环境（Windows / WSL / Linux / macOS）是否已经生成 SSH key；
* 对应环境的公钥是否已经添加到 GitLab；
* 是否使用了默认路径 `~/.ssh/id_ed25519`；
* 如仍有问题，可加 `-v` 查看详细日志：

  ```bash
  ssh -vT git@tokamak-4-rocky.local
  ```

### 6.3 clone 报错 `Could not resolve hostname` 或地址里出现奇怪主机名

* 确认使用的仓库地址是本手册约定形式：

  ```text
  git@tokamak-4-rocky.local:<group>/<project_path>.git
  ```

* 不要使用 GitLab 旧配置产生的 `git@gitlab.xxx.local:...` 地址；

* 如网页上的 “Clone with SSH” 仍然是旧主机名，说明服务器 `gitlab_ssh_host` 未按部署手册更新，应在 Tokamak-4 上修正后重启 GitLab。

---

本手册的目标是让新机器在 10 分钟内完成接入：
能 ping 通、能 ssh 登录、能访问 GitLab、能 clone 仓库。
如果在执行过程中遇到新的问题，可以在本仓库的 `docs/` 目录中补充 FAQ 条目，逐步完善。
