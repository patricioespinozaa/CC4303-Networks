#!/usr/bin/python3
import jsockets
import sys
import threading
import socket
import time

# Cantidad de argumentos
if len(sys.argv) != 7:
    print('Uso: ' + sys.argv[0] + ' size timeout IN OUT host port')
    sys.exit(1)

# Argumentos
size = int(sys.argv[1])
retransmit_timeout = float(sys.argv[2])
input_file = sys.argv[3]
output_file = sys.argv[4]
host = sys.argv[5]
port = sys.argv[6]

# Estado compartido entre ambos threads
lock = threading.Lock()
cond = threading.Condition(lock)
ack_received = False
expected_seq = 0
last_ack = -1
eof_received = False
current_packet = b''
packet_stats = {
    'sent': 0,
    'retransmitted': 0
}

# Convertir entero a número de secuencia de 3 dígitos
# Por ejemplo, 0 -> b'000', 1 -> b'001', ..., 999 -> b'999
def seq_str(n):
    return f"{n % 1000:03}".encode()

# Enviar y recibir paquetes
# El emisor envía paquetes y espera confirmaciones
def Sender(s):
    global ack_received, current_packet, last_ack, packet_stats

    with open(input_file, "rb") as f:
        seq = 0
        while True:
            chunk = f.read(size)
            header = seq_str(seq)
            packet = header + chunk
            if not chunk:
                packet = header  # EOF: solo del header

            with cond:
                ack_received = False
                current_packet = packet
                send_time = time.time()

                # Envio del paquete
                s.send(packet)
                packet_stats['sent'] += 1

                # Esperar confirmación
                while not ack_received:
                    remaining = retransmit_timeout - (time.time() - send_time)
                    if remaining <= 0:
                        # Timeout, retransmitir
                        s.send(packet)
                        send_time = time.time()
                        packet_stats['retransmitted'] += 1
                        packet_stats['sent'] += 1
                    else:
                        cond.wait(timeout=remaining)

            if not chunk:
                break  # EOF enviado

            seq = (seq + 1) % 1000  # Reciclaje de números de secuencia: 0-999


# El receptor recibe paquetes y envía confirmaciones
def Receiver(s):
    global ack_received, expected_seq, eof_received

    # Timeout máximo en socket
    s.settimeout(3.0)  
    with open(output_file, "wb") as f:
        while True:
            try:
                data = s.recv(3 + size)
            except socket.timeout:
                print("[RECV] Timeout de socket. Terminando cliente con error.")
                sys.exit(1)

            if len(data) < 3:
                continue  # Paquete inválido

            header = data[:3]
            body = data[3:]
            try:
                seq = int(header.decode())
            except ValueError:
                continue  # Encabezado inválido

            with cond:
                if seq == expected_seq:
                    if len(body) == 0:
                        eof_received = True
                        ack_received = True
                        cond.notify()
                        break  # EOF recibido

                    f.write(body)
                    ack_received = True
                    expected_seq = (expected_seq + 1) % 1000
                    cond.notify()
                else:
                    # Retransmisión: reenviar confirmación al emisor
                    cond.notify()

# Conexión del socket UDP
s = jsockets.socket_udp_connect(host, port)
if s is None:
    print('[INIT] No se pudo abrir el socket UDP')
    sys.exit(1)

# Inicializar el canal UDP
try:
    s.send(b'hello')
    s.recv(1024)
except Exception as e:
    print(f'[INIT] Error de comunicación UDP: {e}')
    sys.exit(1)

# Lanzar hilos 
recv_thread = threading.Thread(target=Receiver, args=(s,))
send_thread = threading.Thread(target=Sender, args=(s,))

start_time = time.time()
recv_thread.start()
send_thread.start()
send_thread.join()
recv_thread.join()
end_time = time.time()

# Cierre y datos obtenidos
s.close()
total = packet_stats['sent']
retrans = packet_stats['retransmitted']
error_rate = (retrans / total) * 100 if total > 0 else 0.0

print(f"sent {total} packets, lost {retrans}, {error_rate:.6f}%")
print(f"{end_time - start_time:.2f} seconds total")
