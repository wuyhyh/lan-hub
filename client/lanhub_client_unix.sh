#!/usr/bin/env bash
set -euo pipefail

HOST_FQDN="tokamak-4-rocky.local"
HOST_SHORT="tokamak-4-rocky"
HOSTS_FILE="/etc/hosts"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISCOVER_PY="${SCRIPT_DIR}/lanhub_discover.py"

if [[ "$EUID" -ne 0 ]]; then
    echo "本脚本需要 root 权限，请使用：sudo $0"
    exit 1
fi

if [[ ! -x "${DISCOVER_PY}" ]]; then
    echo "找不到 ${DISCOVER_PY}，请确认路径正确并给予可执行权限。"
    exit 1
fi

echo "[1/3] 通过 lan-hub 协议发现服务器 IP ..."
IP="$(python3 "${DISCOVER_PY}" --hostname "${HOST_SHORT}" --ip-only || true)"

if [[ -z "${IP}" ]]; then
    echo "错误：无法通过广播发现服务器 IP。"
    echo "请确认："
    echo "  - 服务器上 lanhub_server.py 正在运行；"
    echo "  - 防火墙放通 58000/udp；"
    echo "  - 本机与服务器在同一网段。"
    exit 1
fi

echo "发现服务器：${HOST_SHORT} -> ${IP}"

echo "[2/3] 备份 ${HOSTS_FILE} ..."
cp "${HOSTS_FILE}" "${HOSTS_FILE}.bak.$(date +%s)"

TMP_FILE="$(mktemp)"

echo "[3/3] 更新 ${HOSTS_FILE} ..."
# 删除旧的 tokamak-4-rocky 记录
grep -vE 'tokamak-4-rocky(\s|$)' "${HOSTS_FILE}" > "${TMP_FILE}" || true

{
    cat "${TMP_FILE}"
    echo "${IP} ${HOST_SHORT} ${HOST_FQDN}"
} > "${HOSTS_FILE}"

rm -f "${TMP_FILE}"

echo
echo "已写入："
echo "  ${IP} ${HOST_SHORT} ${HOST_FQDN}"
echo
echo "现在可以使用以下方式访问服务器："
echo "  ping ${HOST_FQDN}"
echo "  ssh <user>@${HOST_FQDN}"
echo "  git clone git@${HOST_FQDN}:aerospacecenter/hpc_project.git"

