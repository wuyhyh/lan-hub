#!/usr/bin/env python3
import argparse
import json
import socket
import sys
from typing import Optional

DEFAULT_PORT = 58000
MAGIC = b"LANHUB_DISCOVER_V1"


def discover(port: int, timeout: float, expect_hostname: Optional[str]) -> Optional[dict]:
    """
    通过 UDP 广播发现 lan-hub 服务器，返回 JSON dict：
    {"ip": "...", "hostname": "...", "fqdn": "...", "version": "..."}
    找不到时返回 None。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)

    try:
        s.sendto(MAGIC, ("255.255.255.255", port))
    except OSError as e:
        print(f"[lanhub_discover] broadcast failed: {e}", file=sys.stderr)
        return None

    while True:
        try:
            data, addr = s.recvfrom(2048)
        except socket.timeout:
            return None
        except OSError as e:
            print(f"[lanhub_discover] recv error: {e}", file=sys.stderr)
            return None

        try:
            info = json.loads(data.decode("utf-8"))
        except Exception:
            # 非 JSON 报文，丢弃
            continue

        if not isinstance(info, dict):
            continue

        # 可选：按 hostname 过滤，只接受 tokamak-4-rocky
        if expect_hostname and info.get("hostname") != expect_hostname:
            continue

        # 附带真实来源 IP，便于调试
        info["from"] = addr[0]
        return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--hostname", help="只接受该主机名的响应，例如 tokamak-4-rocky")
    parser.add_argument(
        "--ip-only",
        action="store_true",
        help="只输出 IP，不输出 JSON，给 shell/脚本调用用",
    )
    args = parser.parse_args()

    info = discover(args.port, args.timeout, args.hostname)
    if not info:
        # 给脚本用：空输出 + 非 0 退出码
        if args.ip_only:
            sys.exit(1)
        print("lanhub_discover: no response", file=sys.stderr)
        sys.exit(1)

    if args.ip_only:
        print(info["ip"], end="")
    else:
        print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
