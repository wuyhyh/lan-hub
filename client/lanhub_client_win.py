#!/usr/bin/env python3
import os
import re
import subprocess
from pathlib import Path
import sys

HOST_FQDN = "tokamak-4-rocky.local"
HOST_SHORT = "tokamak-4-rocky"
HOSTS_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")


def discover_ip() -> str:
    """
    调用同目录下的 lanhub_discover.py，获取服务器 IP。
    """
    here = Path(__file__).resolve().parent
    discover_py = here / "lanhub_discover.py"

    if not discover_py.exists():
        print(f"找不到 {discover_py}", file=sys.stderr)
        return ""

    try:
        out = subprocess.check_output(
            [sys.executable, str(discover_py), "--hostname", HOST_SHORT, "--ip-only"],
            encoding="utf-8",
            errors="ignore",
        )
    except subprocess.CalledProcessError:
        return ""

    return out.strip()


def clear_old_hosts():
    """
    删除 hosts 中所有 tokamak-4-rocky 相关记录。
    """
    if not HOSTS_PATH.exists():
        print(f"找不到 hosts 文件：{HOSTS_PATH}")
        sys.exit(1)

    try:
        lines = HOSTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    except PermissionError:
        print("无法读取 hosts 文件，请以管理员身份运行本脚本。")
        sys.exit(1)

    new_lines = []
    removed = False
    for line in lines:
        if HOST_SHORT in line or HOST_FQDN in line:
            removed = True
            continue
        new_lines.append(line)

    if removed:
        print("已从 hosts 中删除旧的 tokamak-4-rocky 映射。")

    try:
        HOSTS_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except PermissionError:
        print("无法写入 hosts 文件，请以管理员身份运行本脚本。")
        sys.exit(1)


def append_mapping(ip: str):
    """
    在 hosts 中追加一条 IP -> tokamak-4-rocky 映射。
    """
    try:
        lines = HOSTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    except PermissionError:
        print("无法读取 hosts 文件，请以管理员身份运行本脚本。")
        sys.exit(1)

    names = [HOST_SHORT, HOST_FQDN]
    lines.append(f"{ip} " + " ".join(names))

    try:
        HOSTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except PermissionError:
        print("无法写入 hosts 文件，请以管理员身份运行本脚本。")
        sys.exit(1)

    print("已写入 hosts：")
    print(f"  {ip} {' '.join(names)}")


def main():
    clear_old_hosts()

    ip = discover_ip()
    if not ip:
        print("错误：无法通过 lan-hub 协议发现服务器 IP。", file=sys.stderr)
        print("请确认：")
        print("  - 服务器上 lanhub_server.py 正在运行；")
        print("  - 防火墙允许 58000/udp；")
        print("  - 本机在同一网段；")
        sys.exit(1)

    if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
        print(f"发现到的 IP 格式不合法：{ip}", file=sys.stderr)
        sys.exit(1)

    append_mapping(ip)

    print()
    print("现在可以使用以下方式访问服务器：")
    print(f"  ping {HOST_FQDN}")
    print(f"  ssh <user>@{HOST_FQDN}")
    print(f"  git clone git@{HOST_FQDN}:aerospacecenter/hpc_project.git")


if __name__ == "__main__":
    main()
