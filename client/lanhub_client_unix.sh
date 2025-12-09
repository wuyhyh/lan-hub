#!/usr/bin/env bash
set -euo pipefail

HOSTNAME="tokamak-4-rocky.local"
ALIASES=("tokamak-4-rocky" "gitlab.local")

echo "[1/2] 解析 ${HOSTNAME} ..."
IP=$(getent hosts "${HOSTNAME}" | awk '{print $1}' || true)

if [[ -z "${IP}" ]]; then
    echo "通过 getent 无法解析，尝试使用 ping ..."
    IP=$(ping -c 1 "${HOSTNAME}" 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -n1 || true)
fi

if [[ -z "${IP}" ]]; then
    echo "解析失败，退出。"
    exit 1
fi

echo "解析到 ${HOSTNAME} = ${IP}"

HOSTS_FILE="/etc/hosts"
TMP_FILE=$(mktemp)

echo "[2/2] 更新 ${HOSTS_FILE} ..."
sudo cp "${HOSTS_FILE}" "${HOSTS_FILE}.bak.$(date +%s)"

# 过滤掉已有的相关记录
grep -vE "tokamak-4-rocky|gitlab.local" "${HOSTS_FILE}" > "${TMP_FILE}" || true

{
    echo "${IP} tokamak-4-rocky ${HOSTNAME} gitlab.local"
} | sudo tee -a "${TMP_FILE}" >/dev/null

sudo mv "${TMP_FILE}" "${HOSTS_FILE}"

echo "完成。现在可以用 tokamak-4-rocky / tokamak-4-rocky.local / gitlab.local 访问。"
