import os

def generar_archivo_binario(nombre_archivo, tamaño_kb, patron_bytes=None):
    tamaño_bytes = tamaño_kb * 1024
    
    if patron_bytes is None:
        import random
        with open(nombre_archivo, 'wb') as f:
            f.write(bytes(random.getrandbits(8) for _ in range(tamaño_bytes)))
    else:
        repeticiones = tamaño_bytes // len(patron_bytes)
        resto = tamaño_bytes % len(patron_bytes)
        
        with open(nombre_archivo, 'wb') as f:
            for _ in range(repeticiones):
                f.write(patron_bytes)

            if resto > 0:
                f.write(patron_bytes[:resto])
    
    tamaño_real = os.path.getsize(nombre_archivo)
    print(f"Archivo generado: {nombre_archivo}")
    print(f"Tamaño solicitado: {tamaño_kb} KB")
    print(f"Tamaño real: {tamaño_real/1024:.2f} KB\n")
    
    return nombre_archivo

# localhost
generar_archivo_binario("files_localhost/big_file.bin", 500)

# anakena
generar_archivo_binario("files_anakena/big_file.bin", 500)

