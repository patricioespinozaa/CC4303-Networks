#!/usr/bin/python3
import jsockets
import sys, threading
import socket

def Rdr(s, output_file):
    """
    Thread receptor:
    Escribe todo lo que recibe hasta que detecta el EOF o el timeout.
    """
    print("[RECV] Iniciando thread receptor...")
    s.settimeout(3.0)  # timeout de 3 segundos
    with open(output_file, "wb") as f:
        while True:
            try:
                data = s.recv(1024 * 1024)
            except socket.timeout:
                print("[RECV] Timeout al esperar datos. Terminando receptor.")
                return
            except Exception as e:
                print(f"[RECV] Excepción durante recepción: {e}")
                return
            if not data:
                print("[RECV] Paquete EOF recibido. Terminando receptor.")
                return
            f.write(data)

# Argumentos
if len(sys.argv) != 6:
    print('Use: ' + sys.argv[0] + ' size IN OUT host port')
    sys.exit(1)

size = int(sys.argv[1])
input_file = sys.argv[2]
output_file = sys.argv[3]
host = sys.argv[4]
port = sys.argv[5]

print(f"[INIT] Cliente UDP iniciado con size={size}, host={host}, port={port}")

# Conexión del socket UDP
s = jsockets.socket_udp_connect(host, port)
if s is None:
    print('[INIT] No se pudo abrir el socket UDP')
    sys.exit(1)


# Inicializar el canal UDP
try:
    print("[INIT] Enviando saludo inicial...")
    s.send(b'hello')
    s.recv(1024)
    print("[INIT] Comunicación UDP establecida.")
except Exception as e:
    print(f'[INIT] ERROR: No se pudo inicializar comunicación UDP: {e}')
    sys.exit(1)

# Crear e iniciar thread receptor
receiver_thread = threading.Thread(target=Rdr, args=(s, output_file))
receiver_thread.start()

# Envío de datos
with open(input_file, "rb") as f:
    print(f"[SEND] Iniciando envío de datos desde {input_file}...")
    while True:
        chunk = f.read(size)
        if not chunk:
            print("[SEND] Fin del archivo alcanzado.")
            break
        s.send(chunk)

# Enviar paquete vacío como EOF
try:
    s.send(b'')
    print("[SEND] Paquete EOF enviado.")
except:
    print("[SEND] Error al enviar paquete de fin.")
    sys.exit(1)

# Esperar al thread receptor
receiver_thread.join()
s.close()
print("[EXIT] Cliente finalizado correctamente.")
