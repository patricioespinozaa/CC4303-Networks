#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time

def Rdr(s, output_file, total_bytes):
    """
    Thread receptor:
    El thread enviador debe contar los bytes enviados
    hasta el EOF, y el receptor debe esperar todos esos bytes hasta terminar, y
    ahi termina el programa."
    """
    with open(output_file, "wb") as f:
        received_bytes = 0
        while received_bytes < total_bytes:
            try:
                data = s.recv(1024 * 1024) 
            except:
                data = None
            if not data:
                break
            f.write(data)
            received_bytes += len(data)

# Ahora se reciben 5 argumentos: 
# tamaño de chunk, archivo de entrada, archivo de salida, host y puerto TCP
if len(sys.argv) != 6:
    print('Use: '+sys.argv[0]+'size IN OUT host port')
    sys.exit(1)

# Argumentos
size = int(sys.argv[1])
input_file = sys.argv[2]
output_file = sys.argv[3]
host = sys.argv[4]
port = sys.argv[5]

# Conexión del socket
s = jsockets.socket_tcp_connect(host, int(port))
if s is None:
    print('could not open socket')
    sys.exit(1)

with open(input_file, "rb") as f:
    data = f.read()
    total_bytes = len(data)
    newthread = threading.Thread(target=Rdr, args=(s, output_file, total_bytes,))
    newthread.start()
    
    # Envío de datos
    # El thread enviador debe contar los bytes enviados hasta el EOF haciendo uso de size para definir el tamaño de los chunks
    sent_bytes = 0
    while sent_bytes < total_bytes:
        chunk = data[sent_bytes:sent_bytes + size] # Es un bytearray
        s.send(chunk)
        sent_bytes += len(chunk)

# Se cambia time.sleep(3) para asegurar que se reciba todo antes del cierre del thread
newthread.join()
s.close()