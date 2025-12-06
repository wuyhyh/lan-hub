#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_DIR}/rocky-config.yaml"

# 简单解析 yaml（字段少，直接用 grep/sed）
cfg_get() {
    local key="$1"
    sed -n "s/^${key}:[[:space:]]*//p" "${CONFIG_FILE}" | head -n1
}

HOSTNAME_CFG="$(cfg_get hostname)"
GIT_USER="$(cfg_get git_user)"
GIT_HOME="$(cfg_get git_home)"
GIT_REPOS_DIR="$(cfg_get git_repos_dir)"
SHARE_DIR="$(cfg_get share_dir)"
SHARE_USER="$(cfg_get share_user)"
DOCS_DIR="$(cfg_get docs_dir)"
DOCS_PORT="$(cfg_get docs_http_port)"

echo "[INFO] 使用配置："
echo "  hostname      = ${HOSTNAME_CFG}"
echo "  git user      = ${GIT_USER}"
echo "  git repos dir = ${GIT_REPOS_DIR}"
echo "  share dir     = ${SHARE_DIR} (owner: ${SHARE_USER})"
echo "  docs dir      = ${DOCS_DIR} (port: ${DOCS_PORT})"
echo

if [[ $EUID -ne 0 ]]; then
    echo "[ERROR] 请用 root 运行 bootstrap_rocky.sh"
    exit 1
fi

echo "[STEP] 设置 hostname 和 /etc/hosts"
hostnamectl set-hostname "${HOSTNAME_CFG}"

if ! grep -q "${HOSTNAME_CFG}" /etc/hosts; then
    sed -i "s/^127\.0\.0\.1.*/127.0.0.1   localhost ${HOSTNAME_CFG}/" /etc/hosts
fi

echo "[STEP] 安装基本软件包"
dnf install -y avahi avahi-tools nss-mdns \
               openssh-server git \
               samba samba-common \
               python3

echo "[STEP] 配置 nss-mdns (hosts: files mdns4_minimal [NOTFOUND=return] dns myhostname)"
sed -i 's/^hosts:.*/hosts:      files mdns4_minimal [NOTFOUND=return] dns myhostname/' /etc/nsswitch.conf

echo "[STEP] 启用 avahi-daemon"
systemctl enable --now avahi-daemon

echo "[STEP] 开放防火墙端口: mDNS, SSH, Samba, docs_http"
firewall-cmd --permanent --add-service=mdns
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=samba
firewall-cmd --permanent --add-port=${DOCS_PORT}/tcp
firewall-cmd --reload

echo "[STEP] 启用 sshd"
systemctl enable --now sshd

echo "[STEP] 创建 git 用户和仓库目录"
if ! id "${GIT_USER}" &>/dev/null; then
    useradd -m -d "${GIT_HOME}" "${GIT_USER}"
fi
mkdir -p "${GIT_REPOS_DIR}"
chown -R "${GIT_USER}:${GIT_USER}" "${GIT_REPOS_DIR}"

echo "[STEP] 创建示例 bare 仓库 demo.git (如已存在则跳过)"
if [[ ! -d "${GIT_REPOS_DIR}/demo.git" ]]; then
    sudo -u "${GIT_USER}" git init --bare "${GIT_REPOS_DIR}/demo.git"
fi

echo "[STEP] 配置 Samba 共享"
mkdir -p "${SHARE_DIR}"
chown -R "${SHARE_USER}:${SHARE_USER}" "${SHARE_DIR}"

SMB_CONF=/etc/samba/smb.conf
if ! grep -q "Tokamak-4-rocky dev server" "${SMB_CONF}" 2>/dev/null; then
    cat >> "${SMB_CONF}" <<EOF

[global]
   workgroup = WORKGROUP
   server string = Tokamak-4-rocky dev server
   netbios name = TOKAMAK-4-ROCKY
   security = user
   map to guest = Bad User
   smb encrypt = required

[devshare]
   path = ${SHARE_DIR}
   browseable = yes
   writable = yes
   guest ok = no
   valid users = ${SHARE_USER}
EOF
fi

systemctl enable --now smb nmb

echo "[NOTE] 需要为用户 ${SHARE_USER} 设置 Samba 密码："
echo "  smbpasswd -a ${SHARE_USER}"

echo "[STEP] 配置 docs HTTP 服务"
mkdir -p "${DOCS_DIR}"
chown -R "${SHARE_USER}:${SHARE_USER}" "${DOCS_DIR}"

DOCS_SERVICE=/etc/systemd/system/docs-http.service
cat > "${DOCS_SERVICE}" <<EOF
[Unit]
Description=Simple HTTP server for docs
After=network.target

[Service]
Type=simple
User=${SHARE_USER}
WorkingDirectory=${DOCS_DIR}
ExecStart=/usr/bin/python3 -m http.server ${DOCS_PORT}
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now docs-http.service

echo
echo "[DONE] Rocky 部署完成。局域网内客户端应能通过以下方式访问："
echo "  SSH  : ssh ${SHARE_USER}@${HOSTNAME_CFG}.local"
echo "  Git  : ssh://git@${HOSTNAME_CFG}.local${GIT_REPOS_DIR}/demo.git"
echo "  Samba: \\\\${HOSTNAME_CFG}.local\\devshare"
echo "  Docs : http://${HOSTNAME_CFG}.local:${DOCS_PORT}/"
