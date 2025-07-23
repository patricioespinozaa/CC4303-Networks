#!/usr/bin/python3
# Echo client program que mide ancho de banda usando UDP
# Version con dos threads: uno lee de un archivo hacia el socket y el otro al revés
# Esta vez recibimos un argumento con el nombre de entrada y otro con el de salida
# Además del tamaño a usar para lectura/escritura en bytes
# Debe soportar binarios cualquiera.
# Implementa stop-and-wait
# Incluye header 'XXX' con número de secuencia de 000 a 999
# EOF es paquete vacío
# client_udp_bw SZ in out host port
import jsockets
import sys, threading
import time

PACK_SZ=1500
MAX_SEQ = 1000
HDR = 3 # 000-999

def to_seq(n):
    if n < 0 or n > 999:
        print("invalid seq", file=sys.stderr)
        sys.exit(1)
    return format(n,'03d').encode()

def from_seq(s):
    return int(s.decode())

def Rdr(s, fout, rcvrok):
    global PACK_SZ, recv_seq
    expected_seq = 0
    s.settimeout(3)
    while True:
        try:
            data=s.recv(PACK_SZ)
        except:
            data = None

        if not data:
            print("Rdr(): socket error!", file=sys.stderr)
            sys.exit(1)

        seq = from_seq(data[0:HDR])
        # print(f"Rdr: {seq}, {data[0:HDR]}")
        with rcvrok:
            if seq == expected_seq:
                recv_seq = seq
                expected_seq = (expected_seq+1)%MAX_SEQ
                # print(f"recv_seq = {recv_seq}")
                recvrok.notify()

        if len(data) == HDR:  # EOF
            break

        fout.write(data[HDR:])

    fout.close()

# Main
if len(sys.argv) != 7:
    print('Use: '+sys.argv[0]+' sz timeout in out host port', file=sys.stderr)
    sys.exit(1)


PACK_SZ = int(sys.argv[1])
TIMEOUT = float(sys.argv[2])
fin = open(sys.argv[3], 'rb', 0)
fout = open(sys.argv[4], 'wb' )
s = jsockets.socket_udp_connect(sys.argv[5], sys.argv[6])
if s is None:
    print('could not open socket', file=sys.stderr)
    sys.exit(1)

# condicion para que el Rdr() avise que llegó un paquete al enviador
# es equivalente a un ACK
recvrok = threading.Condition()

# Creo thread que lee desde el socket hacia stdout:
newthread = threading.Thread(target=Rdr, args=(s,fout,recvrok))
newthread.start()

# En este otro thread leo desde stdin hacia socket:
packs = 0
errs = 0
seq = 0
# esta es una variable compartida con Rdr() que indica el último paquete recibido OK
recv_seq = -1
while True:
    data = fin.read(PACK_SZ-HDR)
    hdr = to_seq(seq)
    # print(f"send: {hdr}")
    while True:
        if not data:
            # print(f"send eof: {hdr}")
            s.send(hdr+b'')
        else:
            s.send(hdr+data)
        with recvrok:
            if recv_seq != seq:
                # print(f"recv wait: {seq}, {recv_seq}")
                if not recvrok.wait(TIMEOUT):  # fue timeout
                    errs += 1
                    continue
        break

    if not data:
        break

    packs += 1
    seq = (seq+1)%MAX_SEQ

newthread.join()
s.close()
print(f'sent {packs} packets, lost {errs}, {errs*100/packs}%')
