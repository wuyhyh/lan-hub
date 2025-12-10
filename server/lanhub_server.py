#!/usr/bin/env python3
import socket
import json
import sys

DISCOVER_PORT = 58000
MAGIC = b"LANHUB_DISCOVER_V1"


def get_ip_for_peer(peer_ip: str) -> str:
    """
    根据对端 IP 反推本机用于到达该对端的出接口 IP。
    处理多网卡场景，比 gethostbyname(hostname) 稳定。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 随便 connect 一下，不真正发包，只是让内核选路由
        s.connect((peer_ip, 1))
        return s.getsockname()[0]
    finally:
        s.close()


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 允许重启时快速复用端口
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVER_PORT))

    hostname = socket.gethostname()
    try:
        fqdn = socket.getfqdn()
    except Exception:
        fqdn = hostname

    print(f"[lanhub_server] listening on 0.0.0.0:{DISCOVER_PORT}, hostname={hostname}", flush=True)

    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[lanhub_server] recv error: {e}", file=sys.stderr, flush=True)
            continue

        if not data.startswith(MAGIC):
            # 忽略其它无关报文
            continue

        peer_ip, peer_port = addr
        try:
            local_ip = get_ip_for_peer(peer_ip)
        except Exception:
            # 兜底：实在算不到时，退回 fqdn 解析
            try:
                local_ip = socket.gethostbyname(hostname)
            except Exception:
                continue

        resp = {
            "version": "1",
            "hostname": hostname,
            "fqdn": fqdn,
            "ip": local_ip,
        }
        payload = json.dumps(resp).encode("utf-8")

        try:
            sock.sendto(payload, addr)
        except Exception as e:
            print(f"[lanhub_server] send error to {addr}: {e}", file=sys.stderr, flush=True)

    print("[lanhub_server] exiting.")


if __name__ == "__main__":
    main()

