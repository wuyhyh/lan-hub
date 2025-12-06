# Rocky 开发中心部署手册（Server 端）

本文档描述如何在一台 Rocky Linux 服务器上快速部署“开发中心”，提供以下能力：

* 统一主机名访问：`Tokamak-4-rocky.local`
* SSH 登录与 Git 仓库托管
* Samba 文件共享
* HTTP 文档浏览服务（如 Notebook / Sphinx 输出）
* 支持在不同局域网迁移后快速恢复使用

假设你已经将本项目源码放在服务器上，例如：

```bash
/root/lan-hub/
  server/
    bootstrap_rocky.sh
    rocky-config.yaml
  client/
    ...
```

## 1. 环境与前提条件

* 操作系统：Rocky Linux 9 / 10（RHEL 系基本兼容）
* 已有 root 权限
* 服务器通过有线或 WiFi 接入某个局域网
* 系统使用 firewalld 管理防火墙（默认为开启）

本手册默认主机名为 `Tokamak-4-rocky`，如需修改，可在配置文件中调整。

## 2. 配置文件说明：`rocky-config.yaml`

`server/rocky-config.yaml` 用于集中配置部署参数。示例内容：

```yaml
hostname: Tokamak-4-rocky         # Rocky 的主机名（同时用于 mDNS 域名）
git_user: git
git_home: /home/git
git_repos_dir: /home/git/repos    # Git 裸仓库根目录

share_dir: /srv/share             # Samba 共享目录
share_user: wuyuhang              # 共享目录属主（通常是你常用账户）

docs_dir: /srv/docs               # 文档 HTTP 根目录
docs_http_port: 8000              # 文档服务端口
```

可根据实际情况修改：

* 如果你不想新建 `git` 用户，可改为其他用户名，但建议保留一个专用 Git 用户。
* `share_user` 通常设为平时登录用的账号，方便直接在 `/srv/share` 和 `/srv/docs` 下操作文件。

## 3. 一键部署脚本：`bootstrap_rocky.sh`

### 3.1 执行脚本

在 Rocky 上（建议以 root 登录）：

```bash
cd /root/lan-hub/server
chmod +x bootstrap_rocky.sh
sudo ./bootstrap_rocky.sh
```

脚本执行过程中会：

1. 读取 `rocky-config.yaml`；
2. 设置系统主机名与 `/etc/hosts`；
3. 安装所需软件包；
4. 配置 mDNS / Avahi，实现 `hostname.local` 访问；
5. 启用并开放 SSH；
6. 创建 Git 用户与仓库根目录；
7. 配置 Samba 共享；
8. 配置文档 HTTP 服务并开机自启。

### 3.2 脚本做的具体事情

**1）主机名与 `/etc/hosts`**

* `hostnamectl set-hostname <hostname>`
* 修改 `/etc/hosts` 中 `127.0.0.1` 行，加入 `<hostname>`，保证本机能解析自身主机名。

**2）安装软件包**

通过 `dnf` 安装以下组件：

* `avahi`, `avahi-tools`, `nss-mdns`：mDNS 自动发现；
* `openssh-server`, `git`：SSH 登录与 Git 仓库；
* `samba`, `samba-common`：Windows/Linux/macOS 文件共享；
* `python3`：文档 HTTP 服务依赖。

**3）配置名字解析使用 mDNS**

修改 `/etc/nsswitch.conf` 中 `hosts:` 行：

```text
hosts:      files mdns4_minimal [NOTFOUND=return] dns myhostname
```

使 `.local` 域名（例如 `Tokamak-4-rocky.local`）通过 Avahi/mDNS 解析。

**4）启用 Avahi**

```bash
systemctl enable --now avahi-daemon
```

用于在局域网中广播自己的主机名。

**5）防火墙配置**

脚本会开放以下服务/端口：

* `mdns`：mDNS（UDP 5353）
* `ssh`：SSH（TCP 22）
* `samba`：Samba（SMB/NetBIOS）
* `docs_http_port`：文档 HTTP 端口（默认 8000/TCP）

```bash
firewall-cmd --permanent --add-service=mdns
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=samba
firewall-cmd --permanent --add-port=${DOCS_PORT}/tcp
firewall-cmd --reload
```

**6）启用 SSH**

```bash
systemctl enable --now sshd
```

客户端可通过 `ssh <user>@Tokamak-4-rocky.local` 登录。

**7）Git 用户与仓库目录**

* 若 `git_user` 不存在，则创建用户，home 目录为 `git_home`；
* 创建 `git_repos_dir` 目录，属主为 `git_user`；
* 初始化示例 bare 仓库 `demo.git`：

```bash
sudo -u git git init --bare /home/git/repos/demo.git
```

客户端可使用：

```bash
git remote add origin ssh://git@Tokamak-4-rocky.local/home/git/repos/demo.git
```

**8）Samba 文件共享**

* 创建共享目录 `share_dir`，属主为 `share_user`；
* 在 `/etc/samba/smb.conf` 末尾追加配置：

```ini
[global]
workgroup = WORKGROUP
server string = Tokamak-4-rocky dev server
netbios name = TOKAMAK-4-ROCKY
security = user
map to guest = Bad User
smb encrypt = required

[devshare]
path = /srv/share
browseable = yes
writable = yes
guest ok = no
valid users = wuyuhang
```

* 启动 Samba：

```bash
systemctl enable --now smb nmb
```

* 需要手工为 `share_user` 设置 Samba 密码（只需一次）：

```bash
smbpasswd -a wuyuhang
```

**9）文档 HTTP 服务**

* 创建文档根目录 `docs_dir`，属主为 `share_user`；
* 生成 `/etc/systemd/system/docs-http.service`，内容大致为：

```ini
[Unit]
Description = Simple HTTP server for docs
After = network.target

[Service]
Type = simple
User = wuyuhang
WorkingDirectory = /srv/docs
ExecStart = /usr/bin/python3 -m http.server 8000
Restart = on-failure

[Install]
WantedBy = multi-user.target
```

* 启动并设为开机自启：

```bash
systemctl daemon-reload
systemctl enable --now docs-http.service
```

之后，只要将编译好的文档（HTML 等）放在 `/srv/docs` 目录下，即可通过浏览器访问。

## 4. 部署完成后的验证流程

在 Rocky 本机执行：

```bash
hostname
hostnamectl
systemctl status avahi-daemon
systemctl status sshd
systemctl status smb nmb
systemctl status docs-http.service
```

在同一局域网内的另一台 Linux/macOS/WSL 上测试：

```bash
ping Tokamak-4-rocky.local
ssh wuyuhang@Tokamak-4-rocky.local
ssh git@Tokamak-4-rocky.local   # 测试 Git 用户（可先只登录）
```

Windows 上测试：

* `cmd` 或 PowerShell 中执行：

  ```bat
  ping Tokamak-4-rocky.local
  ssh wuyuhang@Tokamak-4-rocky.local
  ```

* 访问 Samba 共享：

    * 资源管理器地址栏输入：`\\Tokamak-4-rocky.local\devshare`

* 访问文档服务：

    * 浏览器打开：`http://Tokamak-4-rocky.local:8000/`

## 5. 迁移到新的局域网时需要做什么

当你将这台 Rocky 搬到另一个物理环境（例如从办公室带回家）时：

1. 将 Rocky 接入新的 WiFi / 有线网络，确保可以获得 IP；
2. 不需要重新跑 `bootstrap_rocky.sh`，只需确认以下服务正常运行：

    * `avahi-daemon`
    * `sshd`
    * `smb`、`nmb`
    * `docs-http.service`
3. 在新的局域网中，客户端连接到同一个 WiFi 后：

    * 通过 `Tokamak-4-rocky.local` 访问；
    * 如有必要，在 Windows 上重新运行客户端脚本更新 hosts（见客户端手册）。

