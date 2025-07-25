import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

PORT = 8089
TIMEOUT = 1
MAX_THREADS = 100


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def scan_host(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(TIMEOUT)
            sock.connect((ip, PORT))
            return ip
    except:
        return None


def find_device():
    local_ip = get_local_ip()
    network = ipaddress.IPv4Network(local_ip + "/24", strict=False)
    print(f"🔍 Scanning {network} for port {PORT}...")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(scan_host, str(ip)): ip for ip in network.hosts()}
        for future in as_completed(futures):
            ip = future.result()
            if ip:
                print(f"✅ Found open port {PORT} on {ip}")
                return ip

    print("❌ No device found on port", PORT)
    return None