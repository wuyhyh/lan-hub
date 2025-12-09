# Rocky 开发中心部署手册（Tokamak-4）

本文档描述如何在 Tokamak-4（Rocky Linux Server）上部署内部开发中心，包括：

- 统一主机名 / 域名：`tokamak-4-rocky.local` 与 `tokamak-4-rocky`
- mDNS + `/etc/hosts` 支持
- GitLab CE 安装与配置
- GitLab 项目命名和小写路径说明

## 1. 目标与约定

- 服务器：Tokamak-4，操作系统 Rocky Linux（Server）
- 主机名统一为：`tokamak-4-rocky`
- 局域网访问统一使用：
  - FQDN：`tokamak-4-rocky.local`
  - 短名：`tokamak-4-rocky`
- 所有 Git SSH 访问统一使用：
  - `git@tokamak-4-rocky.local:<group>/<project_path>.git`

> 注意：`project_path` 在 GitLab 中会被自动转换为小写，例如  
> 项目显示名是 `HPC_project`，路径会变成 `hpc_project`，仓库地址为  
> `git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git`。  
> 这是 GitLab 的设计，并不是配置错误。

## 2. 基础系统配置

### 2.1 设置主机名

```bash
sudo hostnamectl set-hostname tokamak-4-rocky
````

验证：

```bash
hostname
hostname -f
```

预期输出中应包含 `tokamak-4-rocky`。

### 2.2 关闭合盖休眠（可选）

如果 Tokamak-4 作为“移动机柜”长期运行，需要关闭合盖休眠。
这部分根据你现有的 systemd-logind 配置执行，这里不再展开，只需在最终状态确认：

* 合上屏幕后 SSH 仍然可用；
* `systemctl status` 中没有因 suspend 导致的频繁唤醒。

## 3. 配置 Avahi + mDNS

为了在局域网中使用 `tokamak-4-rocky.local` 访问，需要安装 Avahi 和 `nss-mdns`。

推荐直接使用仓库中的脚本 `server/setup_lanhub_server.sh`：

```bash
sudo bash server/setup_lanhub_server.sh
```

脚本主要做了三件事：

1. 安装 `avahi`、`avahi-tools`、`nss-mdns`；
2. 修改 `/etc/nsswitch.conf`，在 `hosts:` 行加入
   `mdns4_minimal [NOTFOUND=return]`，让 mDNS 生效；
3. 启用 `avahi-daemon` 并在 firewalld 中放通 `mdns` 服务。

完成后，在同一局域网其他机器上应能成功：

```bash
ping tokamak-4-rocky.local
```

## 4. 防火墙与 SELinux 建议

### 4.1 防火墙

在 Tokamak-4 上放通：

* `ssh`（22/tcp）
* `http`（80/tcp）
* `https`（443/tcp，若启用 HTTPS）
* `mdns`（5353/udp）

示例（使用 firewalld）：

```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=mdns
sudo firewall-cmd --reload
```

### 4.2 SELinux

在 GitLab/SSH 调通之前，SELinux 可能会拦截 GitLab 通过 `git` 用户进行的 SSH 登录。

开发阶段，可以暂时设置为 Permissive 以降低干扰：

```bash
getenforce          # 查看当前状态
sudo setenforce 0   # 临时 Permissive
```

后续如果需要重新启用 Enforcing，再根据审计日志逐步加策略。

## 5. GitLab CE 安装与初始化

### 5.1 安装 GitLab CE

以下仅为示意，实际安装流程可根据 Rocky 版本调整：

```bash
# 1. 添加 GitLab 仓库（示例）
curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.rpm.sh | sudo bash

# 2. 安装时指定 external_url
sudo EXTERNAL_URL="http://tokamak-4-rocky.local" \
     dnf install -y gitlab-ce
```

第一次安装完成后，GitLab 会自动初始化数据库和目录。

### 5.2 核心配置项

编辑 `/etc/gitlab/gitlab.rb`，重点确认以下配置：

```ruby
external_url 'http://tokamak-4-rocky.local'

# 统一 SSH 地址为 tokamak-4-rocky.local:22
gitlab_rails['gitlab_ssh_host'] = 'tokamak-4-rocky.local'
gitlab_rails['gitlab_ssh_port'] = 22
```

保存后执行：

```bash
sudo gitlab-ctl reconfigure
sudo gitlab-ctl restart
```

此后，GitLab 网页上的 “Clone with SSH” 会统一显示为：

```text
git@tokamak-4-rocky.local:<group>/<project_path>.git
```

而不会出现 `git@gitlab.xxx.local` 这种历史遗留主机名。

### 5.3 初始化管理员账号

安装完成后，浏览器访问：

```text
http://tokamak-4-rocky.local
```

按照 GitLab 提示设置 root 密码，然后：

1. 登录 `root` 账号；
2. 创建实际使用的管理员账号（例如 `wuyuhang`）；
3. 降低 root 账号的日常使用频率，仅在需要时登录。

## 6. GitLab 项目命名规范与小写路径说明

GitLab 中“项目”有两个字段：

* **Project name（显示名）**：例如 `HPC_project`，保留大小写，仅用于页面展示；
* **Project path（路径）**：用于 URL、SSH 地址，例如 `hpc_project`。

GitLab 自动对 Project path 做规范化：

* 自动转为小写；
* 空格替换为 `-`；
* 不允许仅大小写不同的路径并存。

因此，本项目约定：

1. 允许项目 **显示名** 带大写，例如：

    * `HPC_project`
    * `LAN-hub`
2. 但访问地址一律使用小写路径，例如：

    * `git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git`
    * `git@tokamak-4-rocky.local:aerospacecenter/lan-hub.git`
3. 在文档和脚本中出现仓库地址时，一律使用小写 `project_path`。

如果希望本地目录名保持大写，可以在 clone 时手动指定：

```bash
git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git HPC_project
```

## 7. 部署后自检清单

在完成上述步骤后，至少要在一台 Windows 机器和一台 WSL/Ubuntu 上验证：

1. `ping tokamak-4-rocky.local` 正常；
2. `ssh root@tokamak-4-rocky.local` 能登录；
3. 浏览器访问 `http://tokamak-4-rocky.local` 正常；
4. 为当前客户端生成 SSH key 并导入 GitLab 后：

   ```bash
   ssh -T git@tokamak-4-rocky.local
   ```

   返回 `Welcome to GitLab, @用户名!`；
5. 能成功克隆示例仓库：

   ```bash
   git clone git@tokamak-4-rocky.local:aerospacecenter/hpc_project.git
   ```
