# 客户端接入手册（Client 端）

本文档描述如何在不同类型的客户端上接入“Rocky 开发中心”，包括：

* Linux / macOS / 物理 Rocky / 虚拟机
* Windows
* WSL（Windows Subsystem for Linux）

统一的访问入口：

* 主机名（mDNS）：`Tokamak-4-rocky.local`
* 服务列表：

    * SSH：`ssh <user>@Tokamak-4-rocky.local`
    * Git：`ssh://git@Tokamak-4-rocky.local/home/git/repos/<repo>.git`
    * 文件共享：`\\Tokamak-4-rocky.local\devshare`
    * 文档：`http://Tokamak-4-rocky.local:8000/`

## 1. 环境前提

* 客户端与 Rocky 必须在同一个局域网 / WiFi 下；
* Rocky 端已经按照《Rocky 开发中心部署手册》完成部署，并正常运行；
* 客户端具备访问内网的权限（未被路由器隔离）。

## 2. Linux / macOS 客户端接入（含 WSL 的“完整模式”）

对普通 Linux / macOS 客户端，可以使用 `client/setup_unix_client.sh` 脚本进行半自动配置。

### 2.1 执行脚本

将项目拷贝到客户端，例如：

```bash
~/lan-hub/
  client/
    setup_unix_client.sh
```

以 root 执行：

```bash
cd ~/lan-hub/client
chmod +x setup_unix_client.sh
sudo ./setup_unix_client.sh
```

脚本主要步骤：

1. 检测系统类型（RHEL/Fedora 系或 Debian/Ubuntu 系）；
2. 安装 mDNS 相关组件：

    * RHEL/Fedora/Rocky：`avahi`, `avahi-tools`, `nss-mdns`
    * Debian/Ubuntu：`avahi-daemon`, `libnss-mdns`
3. 修改 `/etc/nsswitch.conf` 的 `hosts:` 行，加入 `mdns4_minimal`：

   ```text
   hosts:      files mdns4_minimal [NOTFOUND=return] dns myhostname
   ```
4. 启动 `avahi-daemon`（如有 systemd）；
5. 测试名字解析与连通性：

    * `getent hosts Tokamak-4-rocky.local`
    * `ping Tokamak-4-rocky.local`

若脚本执行过程中出现安装失败或服务启动失败，按提示检查包管理器、网络或 systemd 状态。

### 2.2 手工连通性测试

脚本执行完成后，在客户端上手工测试：

```bash
ping Tokamak-4-rocky.local
ssh wuyuhang@Tokamak-4-rocky.local
```

如能成功：

* 可以将 Git 仓库的 remote 设置为：

  ```bash
  git remote add origin ssh://git@Tokamak-4-rocky.local/home/git/repos/demo.git
  ```

* 浏览器打开文档：

  ```text
  http://Tokamak-4-rocky.local:8000/
  ```

* 需要挂载 Samba 共享时（Linux）：

  ```bash
  sudo mount -t cifs //Tokamak-4-rocky.local/devshare /mnt \
      -o username=wuyuhang
  ```

macOS 上可在 Finder 中：

* 菜单“前往”→“连接服务器…”
* 输入：`smb://Tokamak-4-rocky.local/devshare`

### 2.3 关于 WSL

WSL2 的网络实现比较特殊，多播 / mDNS 在某些环境下表现不佳，可能导致：

* `Tokamak-4-rocky.local` 解析延迟大；
* 每次 SSH 前会卡很久。

建议两套方案选其一：

1. **轻量方案（推荐）**：

    * 在 WSL 中不启用 mDNS，只在 `/etc/hosts` 中写死 Rocky 当前 IP 和域名：

      ```text
      192.168.1.6  Tokamak-4-rocky.local Tokamak-4-rocky
      ```
    * `hosts` 写死之后，访问速度与直连 IP 一样，不再受 mDNS 影响；
    * 每次换局域网 / Rocky IP 变更时，可以在 WSL 中手工更新这一行，或参考 Windows 脚本自动写入。

2. **完整模式**：

    * 在 WSL 中尝试使用 `setup_unix_client.sh` 安装 Avahi 与 nss-mdns；
    * 这种方式依赖宿主网络对多播的支持，实测有时会偏慢或不稳定，只建议在你确认表现可接受时使用。

## 3. Windows 客户端接入

### 3.1 最简单的方式：直接用 mDNS 解析结果

在许多环境下，Windows 已经可以解析 `Tokamak-4-rocky.local`：

1. 打开 PowerShell 或 CMD，执行：

   ```bat
   ping Tokamak-4-rocky.local
   ```

2. 若能得到类似输出：

   ```text
   正在 Ping Tokamak-4-rocky.local [192.168.1.6] 具有 32 字节的数据:
   ...
   ```

   则可直接使用：

   ```bat
   ssh wuyuhang@Tokamak-4-rocky.local
   ```

3. 访问 Samba 共享：

    * 在资源管理器地址栏输入：

      ```text
      \\Tokamak-4-rocky.local\devshare
      ```

    * 使用 Samba 中为 `wuyuhang` 设置的密码登录。

4. 访问文档：

    * 浏览器中输入：`http://Tokamak-4-rocky.local:8000/`

如果你的网络环境中 `.local` 解析不稳定，或者希望在 hosts 中“固化”当前地址，可使用项目提供的 Python 脚本。

### 3.2 使用 `win_update_rocky_hosts.py` 固化 hosts 映射（可选）

脚本路径：`client/win_update_rocky_hosts.py`。

功能：

1. 调用系统 DNS/mDNS 解析 `Tokamak-4-rocky.local`；
2. 将解析得到的 IP 写入 `C:\Windows\System32\drivers\etc\hosts`，删除旧的 `Tokamak-4-rocky` 记录；
3. 确保无论解析链路如何变化，Windows 始终可以快速访问 Rocky。

使用步骤：

1. 确保已安装 Python 3，并可在 PowerShell 中使用 `python` 命令；

2. 以“管理员身份”运行 PowerShell；

3. 执行：

   ```powershell
   cd C:\path\to\lan-hub\client
   python win_update_rocky_hosts.py
   ```

4. 正常输出类似：

   ```text
   [INFO] Tokamak-4-rocky.local 当前解析为: 192.168.1.6
   [INFO] 正在更新 hosts: C:\Windows\System32\drivers\etc\hosts
   [INFO] 已写入: 192.168.1.6    Tokamak-4-rocky.local Tokamak-4-rocky
   [INFO] 完成。现在可以使用：
     ping Tokamak-4-rocky.local
     ssh root@Tokamak-4-rocky.local
     \\Tokamak-4-rocky.local\devshare
   ```

5. 之后即可在任何终端使用上述域名访问 Rocky。

在迁移到新的局域网时，只需再次运行该脚本，即可更新 hosts 中的 IP。

## 4. 常见问题与排查

### 4.1 无法 ping `Tokamak-4-rocky.local`

请按顺序检查：

1. 客户端与 Rocky 是否在同一网段 / WiFi；

2. 在 Rocky 上检查 Avahi 状态：

   ```bash
   systemctl status avahi-daemon
   ```

3. 在客户端上检查 `nsswitch.conf` 是否包含 `mdns4_minimal`（Linux）；

4. Windows 上可以先尝试手工在 `hosts` 中添加一行映射，确认网络自身是否通畅。

### 4.2 SSH 很慢 / 连接前卡住

* 在 WSL 中通常是 mDNS / 多播导致，优先考虑改用 `/etc/hosts` 静态映射；
* 在 Linux/WSL 上检查 `/etc/hosts` 中是否把主机名写在 `127.0.1.1`，必要时改为真实 IP 或删除多余映射。

### 4.3 Samba 访问失败

* 确认 Samba 服务状态：

  ```bash
  systemctl status smb nmb
  ```

* 确认 `smbpasswd -a <username>` 是否已执行；

* Windows 访问时注意使用 `WORKGROUP` 域或留空，用户名填 `wuyuhang`（或 `share_user`），密码为 Samba 设置的密码。

