#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
win_update_rocky_hosts.py

在 Windows 上运行：
  1. 使用系统 DNS/mDNS 解析 Tokamak-4-rocky.local
  2. 将解析出来的 IP 写入 hosts 文件（删除旧条目）
"""

import os
import socket
import sys
from typing import List

HOSTNAME = "Tokamak-4-rocky.local"
HOSTS_TAG = "Tokamak-4-rocky"


def get_hosts_path() -> str:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(system_root, r"System32\drivers\etc\hosts")


def resolve_ip() -> str:
    try:
        ip = socket.gethostbyname(HOSTNAME)
    except Exception as e:
        raise RuntimeError(f"解析 {HOSTNAME} 失败: {e}")
    return ip


def update_hosts(ip: str) -> None:
    hosts_path = get_hosts_path()
    if not os.path.exists(hosts_path):
        raise FileNotFoundError(f"找不到 hosts 文件: {hosts_path}")

    print(f"[INFO] 正在更新 hosts: {hosts_path}")

    try:
        with open(hosts_path, "r", encoding="ascii", errors="ignore") as f:
            lines = f.readlines()
    except PermissionError:
        raise PermissionError("没有权限读取 hosts，请以管理员身份运行")

    filtered: List[str] = []
    for line in lines:
        if HOSTS_TAG.lower() in line.lower():
            continue
        filtered.append(line.rstrip("\r\n"))

    new_line = f"{ip}\tTokamak-4-rocky.local Tokamak-4-rocky"
    filtered.append(new_line)

    text = "\r\n".join(filtered) + "\r\n"

    try:
        with open(hosts_path, "w", encoding="ascii", errors="ignore") as f:
            f.write(text)
    except PermissionError:
        raise PermissionError("没有权限写入 hosts，请以管理员身份运行")

    print(f"[INFO] 已写入: {new_line}")


def main() -> None:
    try:
        ip = resolve_ip()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] {HOSTNAME} 当前解析为: {ip}")

    try:
        update_hosts(ip)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    print("[INFO] 完成。现在可以使用：")
    print("  ping Tokamak-4-rocky.local")
    print("  ssh root@Tokamak-4-rocky.local")
    print("  \\\\Tokamak-4-rocky.local\\devshare")


if __name__ == "__main__":
    main()
