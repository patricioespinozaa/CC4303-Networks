#!/usr/bin/python3
# Echo server UDP program - version of server_echo_udp.c, mono-cliente
import jsockets
import sys

s = jsockets.socket_udp_bind(1818)
if s is None:
    print('could not open socket')
    sys.exit(1)
while True:
    try:
        data, addr = s.recvfrom(1024*1024)
        print(f'pack: {addr}')
        # aceptamos paquetes vacios e incluso errores
        s.sendto(data, addr)
    except:
        continue

print('no debi morir nunca!')
