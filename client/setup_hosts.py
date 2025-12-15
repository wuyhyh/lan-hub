#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ipaddress
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_HOST = "rocky-server"
WIN_HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        import ctypes  # noqa
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(argv: list[str]) -> None:
    # 用 UAC 重新以管理员权限启动同一条命令
    import ctypes

    params = " ".join([f'"{a}"' for a in argv[1:]])
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", argv[0], params, None, 1)
    if rc <= 32:
        print("ERROR: 无法触发管理员提权（UAC）。请手工用“以管理员身份运行”打开终端再执行。", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def remove_readonly_attr(path: str) -> None:
    # 去掉只读属性（有时被误设）
    run(["attrib", "-r", path])


def read_hosts_text(p: Path) -> str:
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "mbcs"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def write_hosts_text(p: Path, content: str) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\r\n")
    tmp.replace(p)


def update_hosts_file(p: Path, ip: str, host: str) -> Path:
    backup = p.with_name(f"hosts.bak.{int(time.time())}")
    shutil.copy2(p, backup)

    text = read_hosts_text(p)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # 删除所有“非注释行”里包含 host 的映射，避免污染
    new_lines = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            new_lines.append(line)
            continue
        tokens = s.split()
        if host in tokens[1:]:
            continue
        new_lines.append(line)

    # 追加新映射
    if new_lines and new_lines[-1].strip() != "":
        new_lines.append("")
    new_lines.append(f"{ip} {host}")

    new_text = "\r\n".join(new_lines).rstrip("\r\n") + "\r\n"
    write_hosts_text(p, new_text)
    return backup


def flush_windows_dns() -> None:
    r = run(["ipconfig", "/flushdns"])
    if r.returncode == 0:
        print("OK: ipconfig /flushdns")
    else:
        print("WARNING: 刷新 DNS 失败：", file=sys.stderr)
        if r.stdout:
            print(r.stdout, file=sys.stderr)
        if r.stderr:
            print(r.stderr, file=sys.stderr)


def wsl_available() -> bool:
    r = run(["wsl.exe", "-l", "-q"])
    return r.returncode == 0 and r.stdout.strip() != ""


def update_wsl_hosts(ip: str, host: str, distro: str | None) -> None:
    if not wsl_available():
        print("INFO: 未检测到 WSL，跳过。")
        return

    cmd = (
        "set -eu; "
        "TS=$(date +%s); "
        "cp /etc/hosts /etc/hosts.bak.$TS; "
        f"grep -vE '^[[:space:]]*[^#].*[[:space:]]{re.escape(host)}([[:space:]]|$)' /etc/hosts > /tmp/hosts.new; "
        "printf '\\n' >> /tmp/hosts.new; "
        f"printf '{ip} {host}\\n' >> /tmp/hosts.new; "
        "cat /tmp/hosts.new > /etc/hosts; "
        "rm -f /tmp/hosts.new; "
        "echo OK"
    )

    base = ["wsl.exe"]
    if distro:
        base += ["-d", distro]
    base += ["-u", "root", "--", "sh", "-lc", cmd]

    r = run(base)
    if r.returncode == 0:
        print("OK: WSL /etc/hosts 已更新")
    else:
        print("WARNING: WSL /etc/hosts 更新失败（不影响 Windows hosts）", file=sys.stderr)
        if r.stdout:
            print(r.stdout, file=sys.stderr)
        if r.stderr:
            print(r.stderr, file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="配置 Windows/WSL hosts：让 rocky-server 指向指定 IP")
    ap.add_argument("--ip", required=True, help="GitLab 服务器 IP，例如 192.168.1.102")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"主机名，默认 {DEFAULT_HOST}")
    ap.add_argument("--no-wsl", action="store_true", help="不修改 WSL 的 /etc/hosts")
    ap.add_argument("--wsl-distro", default=None, help="指定 WSL 发行版名称（可选）")
    args = ap.parse_args()

    try:
        ipaddress.ip_address(args.ip)
    except ValueError:
        print(f"ERROR: 非法 IP: {args.ip}", file=sys.stderr)
        return 1

    if not is_windows():
        print("ERROR: 这个脚本必须在 Windows 上运行。", file=sys.stderr)
        return 1

    if not is_admin():
        # 直接自提权
        relaunch_as_admin([sys.executable] + sys.argv)

    hosts = Path(WIN_HOSTS_PATH)
    remove_readonly_attr(str(hosts))

    try:
        backup = update_hosts_file(hosts, args.ip, args.host)
        print(f"OK: Windows hosts 已更新：{args.ip} {args.host}")
        print(f"OK: 备份：{backup}")
    except PermissionError as e:
        print("ERROR: 写 hosts 被拒绝。大概率是安全软件/受控文件夹访问拦截。", file=sys.stderr)
        print(f"DETAIL: {e}", file=sys.stderr)
        return 3

    flush_windows_dns()

    if not args.no_wsl:
        update_wsl_hosts(args.ip, args.host, args.wsl_distro)

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
