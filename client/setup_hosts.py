#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ipaddress
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_HOST = "rocky-server"

WIN_HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


def is_windows() -> bool:
    return os.name == "nt"


def require_admin_windows() -> None:
    # 简单检测是否管理员权限：能否写 hosts 所在目录
    hosts = Path(WIN_HOSTS_PATH)
    try:
        with open(hosts, "a", encoding="utf-8"):
            pass
    except PermissionError:
        print("ERROR: 需要管理员权限运行。请用“以管理员身份运行”的终端执行脚本。", file=sys.stderr)
        sys.exit(2)


def read_text_best_effort(p: Path) -> str:
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "mbcs"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最后兜底：忽略错误
    return data.decode("utf-8", errors="ignore")


def write_text_atomic(p: Path, content: str) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    # Windows 下 replace 是原子性的
    tmp.replace(p)


def normalize_hosts_lines(text: str) -> list[str]:
    # 保留原始换行格式，统一按行处理
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def strip_existing_mapping(lines: list[str], host: str) -> list[str]:
    # 删除所有包含目标 host 的“非注释”行，避免重复/污染
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line)
            continue
        # 只要该行含有完整 host token 就剔除
        tokens = s.split()
        if host in tokens[1:]:
            continue
        out.append(line)
    return out


def ensure_mapping(lines: list[str], ip: str, host: str) -> list[str]:
    entry = f"{ip} {host}"
    # 追加到文件末尾，前面留一行空行更清晰
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append(entry)
    return lines


def update_windows_hosts(ip: str, host: str) -> None:
    hosts = Path(WIN_HOSTS_PATH)
    backup = hosts.with_name(f"hosts.bak.{int(time.time())}")
    shutil.copy2(hosts, backup)

    text = read_text_best_effort(hosts)
    lines = normalize_hosts_lines(text)
    lines = strip_existing_mapping(lines, host)
    lines = ensure_mapping(lines, ip, host)

    new_text = "\n".join(lines).rstrip("\n") + "\n"
    write_text_atomic(hosts, new_text)

    print(f"OK: Windows hosts 已更新：{ip} {host}")
    print(f"OK: 备份已保存：{backup}")


def flush_windows_dns() -> None:
    try:
        subprocess.run(["ipconfig", "/flushdns"], check=True)
        print("OK: Windows DNS 缓存已刷新 (ipconfig /flushdns)")
    except subprocess.CalledProcessError as e:
        print(f"WARNING: 刷新 DNS 失败：{e}", file=sys.stderr)


def wsl_available() -> bool:
    if not is_windows():
        return False
    try:
        r = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() != ""
    except FileNotFoundError:
        return False


def update_wsl_hosts(ip: str, host: str, distro: str | None) -> None:
    if not wsl_available():
        print("INFO: 未检测到 WSL，跳过 /etc/hosts 更新。")
        return

    # 这里用 root 用户直接改 /etc/hosts，避免要求 sudo 密码
    # 删除含 host 的行，然后追加 ip host
    # shell 里尽量少依赖复杂工具，只用 cp/grep/printf/cat
    cmd = (
        "set -eu; "
        "TS=$(date +%s); "
        "cp /etc/hosts /etc/hosts.bak.$TS; "
        f"grep -vE '^[[:space:]]*[^#].*[[:space:]]{host}([[:space:]]|$)' /etc/hosts > /tmp/hosts.new; "
        "printf '\\n' >> /tmp/hosts.new; "
        f"printf '{ip} {host}\\n' >> /tmp/hosts.new; "
        "cat /tmp/hosts.new > /etc/hosts; "
        "rm -f /tmp/hosts.new; "
        "echo OK: WSL /etc/hosts updated"
    )

    base = ["wsl.exe"]
    if distro:
        base += ["-d", distro]
    base += ["-u", "root", "--", "sh", "-lc", cmd]

    r = subprocess.run(base, capture_output=True, text=True)
    if r.returncode == 0:
        print("OK: WSL /etc/hosts 已更新")
    else:
        print("WARNING: WSL /etc/hosts 更新失败（不影响 Windows hosts 已生效）", file=sys.stderr)
        if r.stdout.strip():
            print(r.stdout, file=sys.stderr)
        if r.stderr.strip():
            print(r.stderr, file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="配置 Windows/WSL hosts，使 rocky-server 指向指定 IP")
    ap.add_argument("--ip", required=True, help="GitLab 服务器 IP，例如 192.168.1.102")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"主机名，默认 {DEFAULT_HOST}")
    ap.add_argument("--no-wsl", action="store_true", help="不修改 WSL 的 /etc/hosts")
    ap.add_argument("--wsl-distro", default=None, help="指定 WSL 发行版名称（可选），例如 Ubuntu-24.04")
    args = ap.parse_args()

    try:
        ipaddress.ip_address(args.ip)
    except ValueError:
        print(f"ERROR: 非法 IP: {args.ip}", file=sys.stderr)
        return 1

    if not is_windows():
        print("ERROR: 这个脚本设计为在 Windows 上运行（同时可自动配置 WSL）。", file=sys.stderr)
        return 1

    require_admin_windows()

    update_windows_hosts(args.ip, args.host)
    flush_windows_dns()

    if not args.no_wsl:
        update_wsl_hosts(args.ip, args.host, args.wsl_distro)

    print("DONE: 配置完成。你现在应该能通过 http://rocky-server/ 访问 GitLab。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
