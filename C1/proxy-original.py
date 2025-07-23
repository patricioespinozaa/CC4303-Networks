import jsockets
import threading

# Configuraci´on del proxy
PROXY_PORT = 9999 # Puerto del proxy
TARGET_HOST = "anakena.dcc.uchile.cl" # Direcci´on del servidor de destino
TARGET_PORT = 1818 # Puerto del servidor de destino

# Diccionario para mapear clientes a servidores
client_map = {}

# Crear socket UDP
proxy_socket = jsockets.socket_udp_bind(PROXY_PORT)

def handle_client():
    while True:
        data, client_address = proxy_socket.recvfrom(1024*1024)
        
        if client_address not in client_map:
            client_map[client_address] = (TARGET_HOST, TARGET_PORT)
        
        target_address = client_map[client_address]
        
        # Reenviar el paquete al servidor de destino
        proxy_socket.sendto(data, target_address)
        
        # Recibir respuesta del servidor de destino
        response, _ = proxy_socket.recvfrom(1024*1024)
        
        # Enviar respuesta de vuelta al cliente
        proxy_socket.sendto(response, client_address)

# Iniciar el hilo para manejar clientes
threading.Thread(target=handle_client, daemon=True).start()
print(f"Proxy UDP escuchando en {PROXY_PORT}, redirigiendo a {TARGET_HOST}:{TARGET_PORT}")
# Mantener el proxy en ejecuci´on
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Proxy UDP detenido.")
    proxy_socket.close()