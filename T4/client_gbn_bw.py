#!/usr/bin/python3
import jsockets
import sys, threading
import time

PACK_SZ = 1500 # Tamaño por defecto del paquete
MAX_SEQ = 1000 # Máximo número de secuencia
HDR = 3        # Tamaño del encabezado de secuencia (3 dígitos)

# Convertir numero de secuencia a bytes con 3 caracteres
def to_seq(n):
    if n < 0 or n > 999:
        print("invalid seq", file=sys.stderr)
        sys.exit(1)
    return format(n, '03d').encode()

# Convertir header de secuencia a int
def from_seq(b):
    return int(b.decode())

# Clase para manejar paquetes con secuencia y datos
class Packet:
    def __init__(self, seq, data):
        self.seq = seq                   # Número de secuencia del paquete
        self.data = data                 # Datos del paquete (incluye header)
        self.sent_time = None            # Tiempo en que se envió el paquete
        self.retransmitted = False       # Indica si el paquete ha sido retransmitido

# Argumentos
if len(sys.argv) != 8:
    print('Uso: client_gbn_bw.py size timeout win IN OUT host port', file=sys.stderr)
    sys.exit(1)

# Extracción de argumentos
PACK_SZ = int(sys.argv[1])
TIMEOUT = float(sys.argv[2])
WIN_SZ = int(sys.argv[3])
fin = open(sys.argv[4], 'rb', 0)
fout = open(sys.argv[5], 'wb')
s = jsockets.socket_udp_connect(sys.argv[6], sys.argv[7])


if s is None:
    print('Error al abrir socket', file=sys.stderr)
    sys.exit(1)


# Variables compartidas
lock = threading.Condition()
recv_ok = -1
base = 0
next_seq = 0
window = [None for _ in range(MAX_SEQ)]
total_sent = 0
retrans_count = 0
error_count = 0
max_win = 0
est_rtt = None

def update_rtt(new_sample):
    global est_rtt
    if est_rtt is None:
        est_rtt = new_sample
    else:
        est_rtt = 0.5 * est_rtt + 0.5 * new_sample

# Thread lector: recibe paquetes del servidor y notifica ACK implícito
def Rds():
    global recv_ok, base, est_rtt, max_win
    s.settimeout(15.0)
    while True:
        try:
            pkt = s.recv(PACK_SZ)
        except:
            print("Timeout de recepción - error", file=sys.stderr)
            sys.exit(1)

        if len(pkt) < HDR:
            continue

        seq = from_seq(pkt[:HDR])

        with lock:
            if window[seq] is not None and not window[seq].retransmitted:
                now = time.time()
                rtt_sample = now - window[seq].sent_time
                update_rtt(rtt_sample)

            if (base <= seq < base + WIN_SZ) or (base + WIN_SZ >= MAX_SEQ and seq < (base + WIN_SZ) % MAX_SEQ):
                recv_ok = seq
                while window[base] is None and base != next_seq:
                    base = (base + 1) % MAX_SEQ
                while window[base] is not None and from_seq(window[base].data[:HDR]) == base:
                    # ACK implícito
                    base = (base + 1) % MAX_SEQ
                lock.notify()

        if len(pkt) == HDR:
            break

        fout.write(pkt[HDR:])

    fout.close()

# Lanzar thread lector
threading.Thread(target=Rds, daemon=True).start()

# Main: enviador
EOF = False
start_time = time.time()

while not EOF or base != next_seq:
    with lock:
        while (next_seq - base + MAX_SEQ) % MAX_SEQ < WIN_SZ and not EOF:
            data = fin.read(PACK_SZ - HDR)

            # ENVIO DE EOF  
            if not data:
                EOF = True
                pkt_data = to_seq(next_seq)  # EOF packet con solo secuencia
            else:
                pkt_data = to_seq(next_seq) + data

            pkt = Packet(next_seq, pkt_data)
            pkt.sent_time = time.time()
            window[next_seq] = pkt

            try:
                s.send(pkt_data)
            except:
                pass

            total_sent += 1
            max_win = max(max_win, (next_seq - base + MAX_SEQ) % MAX_SEQ)
            next_seq = (next_seq + 1) % MAX_SEQ

        # Verificar timeout
        if window[base] is not None:
            wait_time = TIMEOUT - (time.time() - window[base].sent_time)
        else:
            wait_time = TIMEOUT

        if wait_time < 0:
            wait_time = 0

        triggered = lock.wait(timeout=wait_time)

        # Timeout - retransmitir ventana
        if not triggered:
            i = base
            while i != next_seq:
                if window[i] is not None:
                    try:
                        s.send(window[i].data)
                    except:
                        pass
                    window[i].sent_time = time.time()
                    window[i].retransmitted = True
                    retrans_count += 1
                    error_count += 1
                i = (i + 1) % MAX_SEQ

fin.close()
s.close()
end_time = time.time()

total_data_pkts = total_sent

# Total transmitido
total_transmitted = total_sent + retrans_count
print(f'sent {total_data_pkts} packets, retrans {retrans_count}, {error_count*100/total_data_pkts}%')
print(f'tot packs {total_transmitted}, {total_sent*100/total_data_pkts}%')
print(f'Max_win: {max_win}')
print(f'rtt est = {est_rtt}')
print(f"{end_time - start_time:.2f} real")
