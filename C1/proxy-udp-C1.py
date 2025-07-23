import jsockets
import threading

# Configuración del proxy
PROXY_PORT = 9999  # Puerto en que escucha el proxy
TARGET_HOST = "anakena.dcc.uchile.cl" # Direcci´on del servidor de destino
TARGET_PORT = 1818 # Puerto del servidor de destino

# Socket para recibir desde clientes
proxy_socket = jsockets.socket_udp_bind(PROXY_PORT)

# Socket para enviar/recibir del servidor
server_socket = jsockets.socket_udp_bind(0)  
server_socket.settimeout(2)  # Prevenir un bloqueo por tiempo de espera

def handle_packet(data, client_address):
    try:
        # Enviar al servidor real
        server_socket.sendto(data, (TARGET_HOST, TARGET_PORT))

        # Recibir respuesta del servidor
        response, server_addr = server_socket.recvfrom(1024*1024)

        # Reenviar al cliente original
        proxy_socket.sendto(response, client_address)
    except Exception as e:
        print(f"Error con {client_address}: {e}")

def handle_clients():
    while True:
        try:
            data, client_address = proxy_socket.recvfrom(1024*1024)
            print(f"Paquete de {client_address}: {data.decode(errors='ignore')}")
            threading.Thread(target=handle_packet, args=(data, client_address), daemon=True).start()
        except Exception as e:
            print(f"Error al recibir datos: {e}")

# Hilo principal de escucha
threading.Thread(target=handle_clients, daemon=True).start()
print(f"Proxy UDP escuchando en puerto {PROXY_PORT}, redirigiendo a {TARGET_HOST}:{TARGET_PORT}")
# Mantener el proxy en ejecuci´on
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Proxy UDP detenido.")
    proxy_socket.close()
    server_socket.close()
