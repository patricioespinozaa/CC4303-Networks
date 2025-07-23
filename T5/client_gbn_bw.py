#!/usr/bin/python3
import jsockets
import sys, threading
import time

PACK_SZ = 1500
MAX_SEQ = 1000
HDR = 3

# Convertir numero de secuencia a bytes con 3 caracteres
# Numeros de secuencia: 000-999 como caracteres de largo fijo (3) y se
# reciclan cuando se acaban (el siguiente a 999 es 000).
def to_seq(n):
    return format(n % MAX_SEQ, '03d').encode()

def from_seq(b):
    return int(b.decode())

class Packet:
    def __init__(self, seq, data):
        self.seq = seq
        self.data = data
        self.sent_time = None
        self.retransmitted = False
        self.acked = False

if len(sys.argv) != 8:
    print('Uso: client_sr_bw.py size timeout win IN OUT host port', file=sys.stderr)
    sys.exit(1)

PACK_SZ = int(sys.argv[1])
TIMEOUT = float(sys.argv[2])
WIN_SZ = int(sys.argv[3])
fin = open(sys.argv[4], 'rb', 0)
fout = open(sys.argv[5], 'wb')
s = jsockets.socket_udp_connect(sys.argv[6], sys.argv[7])
if s is None:
    print('Error al abrir socket', file=sys.stderr)
    sys.exit(1)

lock = threading.Condition()
base = 0
next_seq = 0
recv_base = 0
window = [None for _ in range(MAX_SEQ)]
recv_buf = [None for _ in range(MAX_SEQ)]
acked = [False for _ in range(MAX_SEQ)]
recv_flags = [False for _ in range(MAX_SEQ)]
total_sent = 0
retrans_count = 0
error_count = 0
max_win = 0
est_rtt = None
EOF = False
recv_EOF = False

# Hacer un promedio ponderado en el tiempo, donde la ultima medicion
# vale un 50% y el promedio acumulado un 50%
def update_rtt(sample):
    global est_rtt
    if est_rtt is None:
        est_rtt = sample
    else:
        est_rtt = 0.5 * est_rtt + 0.5 * sample

# Receptor

def between(seq, start, end):
    if start <= end:
        return start <= seq < end
    else:
        return start <= seq or seq < end

def Rds():
    global recv_base, recv_EOF
    # Definir el timeout de 15s
    s.settimeout(15.0)
    while True:
        try:
            pkt = s.recv(PACK_SZ)
        # Manejar el timeout con un error de excepción
        except Exception as e:
            print(f"Error en recepción: {e}", file=sys.stderr)
            sys.exit(1)
        if len(pkt) < HDR:
            continue
        try:
            seq = from_seq(pkt[:HDR]) # obtener el número de secuencia del paquete que se recibe
        except ValueError:
            # Paquete invalido
            continue
        
        now = time.time()

        with lock:
            # Actualizacion del RTT si el paquete recibido es un ACK (solo se mide si no es retransmitido)
            if window[seq] is not None and not window[seq].retransmitted:
                update_rtt(now - window[seq].sent_time)
            acked[seq] = True # Marcar el paquete como recibido (ack sin enviar de forma explicita)
            lock.notify_all()

            if between(seq, recv_base, (recv_base + WIN_SZ) % MAX_SEQ):
                if len(pkt) == HDR: # Detectar el paquete de EOF
                    recv_EOF = True
                    recv_flags[seq] = True
                    lock.notify_all()
                    continue
                recv_buf[seq] = pkt[HDR:]
                recv_flags[seq] = True

                while recv_flags[recv_base]:
                    fout.write(recv_buf[recv_base])
                    recv_buf[recv_base] = None
                    recv_flags[recv_base] = False
                    recv_base = (recv_base + 1) % MAX_SEQ

threading.Thread(target=Rds, daemon=True).start()

start_time = time.time()

while not EOF or any(window[i] is not None for i in range(MAX_SEQ)):
    with lock:
        while (next_seq - base + MAX_SEQ) % MAX_SEQ < WIN_SZ and not EOF:
            data = fin.read(PACK_SZ - HDR)
            # terminar el envío con un paquete UDP vacío (cero bytes) que hace de EOF
            if not data:
                EOF = True
                pkt_data = to_seq(next_seq)
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
            # escribir el tamano maximo que tuvo la ventana de envıo
            max_win = max(max_win, (next_seq - base + MAX_SEQ) % MAX_SEQ)
            next_seq = (next_seq + 1) % MAX_SEQ

        now = time.time()
        min_tout = None
        for i in range(MAX_SEQ):
            p = window[i]
            if p and not acked[i]:
                # BONUS:  timeout variable, que sea 1,5 ∗ rtt usando la estimacion de RTT implementada.
                #         El valor de timeout recibido de argumento solo sirve para inicializar el
                #         timeout antes de lograr un calculo de RTT
                remaining = TIMEOUT if est_rtt is None else 1.5 * est_rtt
                time_left = remaining - (now - p.sent_time)
                if min_tout is None or time_left < min_tout:
                    min_tout = max(time_left, 0)

        if min_tout is None:
            lock.wait()
        else:
            lock.wait(timeout=min_tout)

        now = time.time()
        for i in range(MAX_SEQ):
            p = window[i]
            # El enviador no manda toda la ventana al retransmitir, solo los paquetes cuyo timeout ha expirado.
            if p and not acked[i] and (now - p.sent_time >= (TIMEOUT if est_rtt is None else 1.5 * est_rtt)):
                try:
                    s.send(p.data)
                except:
                    pass
                p.sent_time = now
                p.retransmitted = True
                # Calculo de perdidas: al retransmitir un paquete, incrementamos un
                # contador de errores.
                retrans_count += 1
                error_count += 1

        while acked[base]:
            window[base] = None
            acked[base] = False
            base = (base + 1) % MAX_SEQ

fin.close()
fout.close()
s.close()
end_time = time.time()
total_transmitted = total_sent + retrans_count

# Al terminar el proceso, imprimimos un mensaje con el total de 
# paquetes del archivo, los errores, el total de paquetes transmitidos en total
# (buenos m´as retransmisiones) y el porcentaje de error

print(f'sent {total_sent} packets, retrans {retrans_count}, tot packs {total_transmitted}, {100*retrans_count/total_transmitted:.6f}%')
print(f'Max_win: {max_win}')
print(f'rtt est = {est_rtt}')
print(f"{end_time - start_time:.2f} real")
