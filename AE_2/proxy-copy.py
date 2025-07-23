#!/usr/bin/python3
# proxy-copy.py
import select
import sys
import jsockets

def proxy(conn, host, portout, logfile):
    conn2 = jsockets.socket_tcp_connect(host, portout)
    if conn2 is None:
        print(f'Conexión rechazada por {host}:{portout}')
        conn.close()
        return

    print('Cliente conectado')
    inputs = [conn, conn2]

    while inputs:
        readable, writable, exceptional = select.select(inputs, [], inputs)
        
        for s in exceptional:  # Cerramos sockets con error
            print('Cliente con error')
            conn.close()
            conn2.close()
            return
            
        for s in readable:  # Sockets con datos para mí
            if s is conn:
                data = conn.recv(1024*1024)
                if not data:  # EOF
                    conn.close()
                    conn2.close()
                    return
                    
                # Escribir datos al log con tag
                logfile.write(b"\n\n>>> to server\n")
                logfile.write(data)
                logfile.flush()
                
                # Enviar datos al servidor
                conn2.send(data)
                
            if s is conn2:
                data = conn2.recv(1024*1024)
                if not data:  # EOF
                    conn.close()
                    conn2.close()
                    return
                    
                # Escribir datos al log con tag
                logfile.write(b"\n\n<<< from server\n")
                logfile.write(data)
                logfile.flush()
                
                # Enviar datos al cliente
                conn.send(data)

# Main:
if len(sys.argv) != 5:
    print('Uso: '+sys.argv[0]+' port-in host port-out file')
    sys.exit(1)

portin = sys.argv[1]
host = sys.argv[2]
portout = sys.argv[3]
filename = sys.argv[4]

s = jsockets.socket_tcp_bind(portin)
if s is None:
    print('Bind falló')
    sys.exit(1)

print(f"Proxy escuchando en puerto {portin}, conectando a {host}:{portout}")
print(f"Guardando log en {filename}")

try:
    # Abrir el archivo de log en modo binario
    with open(filename, 'wb') as logfile:
        while True:
            conn, addr = s.accept()
            print(f'Cliente conectado desde: {addr}')
            proxy(conn, host, portout, logfile)
            print('Cliente desconectado')
except KeyboardInterrupt:
    print("\nCerrando proxy...")
finally:
    s.close()