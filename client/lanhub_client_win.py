#!/usr/bin/env python3
import subprocess
import re
from pathlib import Path
import sys

HOSTNAME = "tokamak-4-rocky.local"
ALIASES = ["tokamak-4-rocky", "gitlab.local"]  # 你想额外用的别名

def resolve_ip():
    print(f"解析 {HOSTNAME} ...")
    try:
        out = subprocess.check_output(
            ["ping", "-n", "1", HOSTNAME],
            encoding="utf-8",
            errors="ignore"
        )
    except subprocess.CalledProcessError as e:
        print("ping 失败，无法解析 IP")
        print(e)
        sys.exit(1)

    # 找第一个 IPv4 地址
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
    if not m:
        print("未在 ping 输出中找到 IPv4 地址：")
        print(out)
        sys.exit(1)

    ip = m.group(1)
    print(f"解析到 {HOSTNAME} = {ip}")
    return ip

def update_hosts(ip: str):
    hosts_path = Path(r"C:\Windows\System32\drivers\etc\hosts")
    if not hosts_path.exists():
        print(f"找不到 hosts 文件：{hosts_path}")
        sys.exit(1)

    print(f"更新 {hosts_path} ...")

    try:
        text = hosts_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except PermissionError:
        print("无法读取 hosts 文件，请以管理员身份运行本脚本。")
        sys.exit(1)

    new_lines = []
    for line in text:
        if any(name in line for name in [HOSTNAME] + ALIASES):
            # 丢弃旧记录
            continue
        new_lines.append(line)

    names = [HOSTNAME.rstrip(".local"), HOSTNAME] + ALIASES
    new_lines.append(f"{ip} " + " ".join(names))

    try:
        hosts_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except PermissionError:
        print("无法写入 hosts 文件，请以管理员身份运行本脚本。")
        sys.exit(1)

    print("hosts 更新完成。")

def main():
    ip = resolve_ip()
    update_hosts(ip)
    print("完成。现在可以用这些域名访问：")
    print("  - tokamak-4-rocky.local")
    print("  - tokamak-4-rocky")
    print("  - gitlab.local")

if __name__ == "__main__":
    main()

