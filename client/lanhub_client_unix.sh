#!/usr/bin/env bash
set -euo pipefail

HOSTNAME="tokamak-4-rocky.local"
ALIASES=("tokamak-4-rocky")

HOSTS_FILE="/etc/hosts"

if [[ "$EUID" -ne 0 ]]; then
    echo "本脚本需要 root 权限，请使用：sudo $0"
    exit 1
fi

echo "[1/2] 解析 ${HOSTNAME} ..."
IP=$(getent hosts "${HOSTNAME}" | awk '{print $1}' || true)

if [[ -z "${IP}" ]]; then
    echo "getent 解析失败，尝试 ping ..."
    IP=$(ping -c 1 "${HOSTNAME}" 2>/dev/null \
        | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -n1 || true)
fi

if [[ -z "${IP}" ]]; then
    echo "无法解析 ${HOSTNAME}，退出。"
    exit 1
fi

echo "解析到 ${HOSTNAME} = ${IP}"

TMP_FILE=$(mktemp)

echo "[2/2] 更新 ${HOSTS_FILE} ..."
cp "${HOSTS_FILE}" "${HOSTS_FILE}.bak.$(date +%s)"

# 去掉旧记录（包含 tokamak-4-rocky 或 tokamak-4-rocky.local 的行）
grep -vE 'tokamak-4-rocky' "${HOSTS_FILE}" > "${TMP_FILE}" || true

# 写入新的映射：IP + 短主机名 + FQDN
echo "${IP} tokamak-4-rocky ${HOSTNAME}" >> "${TMP_FILE}"

mv "${TMP_FILE}" "${HOSTS_FILE}"

echo "完成。现在可以使用以下域名访问："
echo "  tokamak-4-rocky.local"
echo "  tokamak-4-rocky"
