#!/usr/bin/python3
import jsockets
import sys
from datetime import datetime

"""
El servidor responder´a con un ACK y la fecha,
el id del computador y el id de la cpu cuando el paquete sea recibido, para
almacenarlo en una base de datos. Si no se recibe el paquete, el cliente debe
enviarlo cada S segundos por R intentos, luego descarta el paquete e intenta
con la siguiente medici´on. Implemente el cliente y el servidor en python,
teniendo en consideraci´on:
"""

# python3 new_server.py 1818

LOG_FILE = "cpu_log.txt"
RECEIVED_KEYS = set()

s = jsockets.socket_udp_bind(1818)
if s is None:
    print("Couldn't open socket.")
    sys.exit(1)

print("Server is active")

while True:
    try:
        data, addr = s.recvfrom(1024)
        if not data:
            continue
        decoded = data.decode().strip()
        parts = decoded.split(",")
        if len(parts) != 4:
            print("[ERROR] Packet has invalid construction:", decoded)
            continue

        computer_id, cpu_id, cpu_load, timestamp = parts
        key = f"{computer_id}_{cpu_id}_{timestamp}" # Keys to DB

        if key not in RECEIVED_KEYS:
            RECEIVED_KEYS.add(key)
            with open(LOG_FILE, "a") as f:
                f.write(f"{computer_id},{cpu_id},{cpu_load},{timestamp}\n")
            print(f"[RECEIVED] {decoded}")

        ack_msg = f"ACK,{timestamp},{computer_id},{cpu_id}" # ACK message from server to client
        print(f"[ACK] {ack_msg}")
        s.sendto(ack_msg.encode(), addr)
    except Exception as e:
        print("[ERROR]", e)
        continue
