#!/usr/bin/env python3
import argparse
import json
import socket
import sys
from typing import Optional, List, Tuple

DEFAULT_PORT = 58000
MAGIC = b"LANHUB_DISCOVER_V1"


def guess_local_ipv4() -> Optional[str]:
    """通过连接 8.8.8.8 反推本机出接口 IPv4"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def build_targets(port: int, debug: bool = False) -> List[Tuple[str, int]]:
    """
    构造一组要尝试的广播地址：
    1) 255.255.255.255
    2) <local_A.B.C>.255 （假设 /24 网段）
    """
    targets = [("255.255.255.255", port)]

    local_ip = guess_local_ipv4()
    if local_ip:
        parts = local_ip.split(".")
        if len(parts) == 4:
            bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
            if bcast not in [t[0] for t in targets]:
                targets.append((bcast, port))

    if debug:
        print("[lanhub_discover] targets:", ", ".join(f"{ip}:{port}" for ip, port in targets))

    return targets


def discover(port: int, timeout: float, expect_hostname: Optional[str], debug: bool = False) -> Optional[dict]:
    """
    通过 UDP 广播发现 lan-hub 服务器，返回 JSON dict：
    {"ip": "...", "hostname": "...", "fqdn": "...", "version": "..."}
    找不到时返回 None。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)

    targets = build_targets(port, debug=debug)

    # 给每个目标都发一次
    for addr in targets:
        try:
            if debug:
                print(f"[lanhub_discover] sendto {addr}")
            s.sendto(MAGIC, addr)
        except OSError as e:
            if debug:
                print(f"[lanhub_discover] sendto {addr} failed: {e}", file=sys.stderr)

    while True:
        try:
            data, addr = s.recvfrom(2048)
        except socket.timeout:
            if debug:
                print("[lanhub_discover] timeout waiting for response")
            return None
        except OSError as e:
            if debug:
                print(f"[lanhub_discover] recv error: {e}", file=sys.stderr)
            return None

        if debug:
            print(f"[lanhub_discover] got {len(data)} bytes from {addr}")

        try:
            info = json.loads(data.decode("utf-8"))
        except Exception:
            if debug:
                print("[lanhub_discover] invalid JSON, ignore")
            continue

        if not isinstance(info, dict):
            continue

        if expect_hostname and info.get("hostname") != expect_hostname:
            if debug:
                print(f"[lanhub_discover] hostname mismatch {info.get('hostname')}, ignore")
            continue

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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="打印调试信息（发送目标、收到的报文等）",
    )
    args = parser.parse_args()

    info = discover(args.port, args.timeout, args.hostname, debug=args.debug)
    if not info:
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
