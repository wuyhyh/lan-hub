#!/usr/bin/env bash
set -euo pipefail

ROCKY_HOST="Tokamak-4-rocky.local"

echo "[INFO] 配置 Unix 客户端以访问 ${ROCKY_HOST}"

if [[ $EUID -ne 0 ]]; then
    echo "[ERROR] 请用 root 运行 setup_unix_client.sh"
    exit 1
fi

ID_LIKE="$(. /etc/os-release 2>/dev/null; echo "${ID_LIKE:-$ID}")"

install_pkgs() {
    if [[ "${ID_LIKE}" =~ (rhel|fedora|centos|rocky) ]]; then
        dnf install -y avahi avahi-tools nss-mdns
        systemctl enable --now avahi-daemon || true
    elif [[ "${ID_LIKE}" =~ (debian|ubuntu) ]]; then
        apt update
        apt install -y avahi-daemon libnss-mdns
        systemctl enable --now avahi-daemon || true
    else
        echo "[WARN] 未知发行版 ${ID_LIKE}，请手工安装 mDNS 组件"
    fi
}

echo "[STEP] 安装 mDNS 组件 (avahi / nss-mdns)"
install_pkgs

if grep -q '^hosts:' /etc/nsswitch.conf; then
    echo "[STEP] 配置 /etc/nsswitch.conf 使用 mdns4_minimal"
    sed -i 's/^hosts:.*/hosts:      files mdns4_minimal [NOTFOUND=return] dns myhostname/' /etc/nsswitch.conf
fi

echo "[STEP] 测试名字解析与连通性"
getent hosts "${ROCKY_HOST}" || echo "[WARN] getent 解析失败，请确认在同一局域网"

ping -c1 "${ROCKY_HOST}" || echo "[WARN] ping 失败，请检查网络与防火墙"

echo "[INFO] 尝试 ssh 连接（可能要求输入密码或密钥）："
echo "  ssh ${USER}@${ROCKY_HOST}"
