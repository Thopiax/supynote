import socket
import ipaddress
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List

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


def get_active_networks() -> List[ipaddress.IPv4Network]:
    """Get active network interfaces from the system routing table."""
    networks = []
    try:
        # macOS/Linux route command
        result = subprocess.run(['route', '-n'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                # Look for local network routes (not default gateway)
                if re.search(r'192\.168\.|10\.', line) and 'U' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        # Extract network/interface info
                        network_part = parts[0] if '/' in parts[0] else parts[0] + '/24'
                        try:
                            network = ipaddress.IPv4Network(network_part, strict=False)
                            if network not in networks:
                                networks.append(network)
                        except:
                            continue
    except:
        pass
    
    # Fallback to common networks if route parsing fails
    if not networks:
        local_ip = get_local_ip()
        networks.append(ipaddress.IPv4Network(local_ip + "/24", strict=False))
        for net_str in ["192.168.1.0/24", "192.168.0.0/24"]:
            network = ipaddress.IPv4Network(net_str)
            if network not in networks:
                networks.append(network)
    
    return networks


def scan_host(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(TIMEOUT)
            sock.connect((ip, PORT))
            return ip
    except:
        return None


def find_device():
    networks_to_scan = get_active_networks()
    
    # Sort networks to prioritize 192.168.x ranges
    def network_priority(network):
        network_str = str(network.network_address)
        if network_str.startswith('192.168.'):
            return 0  # Highest priority
        elif network_str.startswith('10.'):
            return 1  # Lower priority
        else:
            return 2  # Lowest priority
    
    networks_to_scan.sort(key=network_priority)
    
    for network in networks_to_scan:
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