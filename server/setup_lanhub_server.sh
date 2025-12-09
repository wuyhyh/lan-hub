#!/usr/bin/env bash
set -euo pipefail

HOSTNAME="tokamak-4-rocky"

echo "[1/4] 设置主机名为 ${HOSTNAME}"
hostnamectl set-hostname "${HOSTNAME}"

echo "[2/4] 安装 Avahi 和 mDNS 组件"
dnf install -y avahi avahi-tools nss-mdns

echo "[3/4] 配置 /etc/nsswitch.conf 启用 mdns4_minimal"
cp /etc/nsswitch.conf /etc/nsswitch.conf.bak.$(date +%s)

# 如果 hosts: 行中没有 mdns4_minimal，则替换为标准配置
awk '
/^hosts:/ && $0 !~ /mdns4_minimal/ {
    print "hosts: files mdns4_minimal [NOTFOUND=return] dns myhostname";
    next
}
{ print }
' /etc/nsswitch.conf.bak.* | tee /etc/nsswitch.conf >/dev/null

echo "[4/4] 启用 Avahi 服务并开放 mDNS"
systemctl enable --now avahi-daemon.service

# 防火墙允许 mDNS（有的环境默认就开了，这里做一次显式设置）
if command -v firewall-cmd >/dev/null 2>&1; then
    firewall-cmd --add-service=mdns --permanent || true
    firewall-cmd --reload || true
fi

echo "完成。现在在局域网内应该可以 ping tokamak-4-rocky.local 了。"
