#!/usr/bin/python3
import jsockets
import sys
import threading
import time
import random
from datetime import datetime

"""
un cliente que env´ ıe paquetes UDP con
el id del computador, id de la cpu, la carga CPU (es un n´ umero entre 0 a
100) y la fecha en formato aaaammddhhMMSS (ej 20250407160000) a un
servidor cada M minutos.
"""

# python3 new_client.py host port
# A mi me funciona python3 new_client.py 127.0.0.1 1818
# Al probar con un host incorrecto se ven los intentos fallidos

# Parametros
M = 1   # Minutos entre mediciones
S = 10  # Segundos entre reintentos
R = 10  # Numero de reintentos

# Infomracion del paquete
COMPUTER_ID = "00000000-0000-0000-0000-000000000002"     # Key to DB
CPU_IDS = ["cpu0", "cpu1", "cpu2"]                       # Key to DB

def send_measurement(s, cpu_id):
    cpu_load = random.randint(0, 100)
    time_stamp = datetime.now().strftime("%Y%m%d%H%M%S") # Key to DB
    message = f"{COMPUTER_ID},{cpu_id},{cpu_load},{time_stamp}"

    print("CPU load:", cpu_load)
    print("Timestamp:", time_stamp)

    for attempt in range(R):
        try:
            s.send(message.encode())
            s.settimeout(S)
            data = s.recv(1024).decode()
            if data.startswith("ACK"):
                print(f"[PACKAGE RECEIVED] {data.strip()}")
                return
        except Exception as e:
            print(f"[RETRY {attempt+1}] No answer 'ACK' received from the server, retrying...")
    print(f"[FAILED] Measurement discarded after {R} retries: {message}")

if len(sys.argv) != 3:
    print("Use: " + sys.argv[0] + " host port")
    sys.exit(1)

s = jsockets.socket_udp_connect(sys.argv[1], sys.argv[2])
if s is None:
    print("could not open socket")
    sys.exit(1)

while True:
    for cpu_id in CPU_IDS:
        send_measurement(s, cpu_id)
    time.sleep(M * 60) # Esperar M minutos entre mediciones

# s.close() -> no se ejecutará ya que el bucle no termina