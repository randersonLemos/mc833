import socket
import struct
import threading
import sys

def checksum(msg):
    """Calcula o checksum (mantido da sua implementação original)."""
    s = 0
    if len(msg) % 2 != 0:
        msg += b'\x00'
    for i in range(0, len(msg), 2):
        w = (msg[i] << 8) + (msg[i+1])
        s = s + w
    s = (s >> 16) + (s & 0xffff)
    s = ~s & 0xffff
    return s

class RawClient:
    def __init__(self, src_ip="10.0.2.2", dest_ip="10.0.1.2", sport=12345, dport=9999):
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.sport = sport
        self.dport = dport

        # 1. Socket para ENVIO (Layer 3 - IPPROTO_RAW)
        try:
            self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        except PermissionError:
            print("[-] Erro: Requer privilégios de Root/Admin para enviar pacotes RAW.")
            sys.exit(1)
        
        # 2. Socket para RECEBIMENTO (Captura pacotes UDP inteiros com cabeçalho IP)
        try:
            self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        except PermissionError:
            print("[-] Erro: Requer privilégios de Root/Admin para escutar pacotes RAW.")
            sys.exit(1)

        # 3. TRUQUE DO KERNEL: Criar um socket UDP padrão apenas para "reservar" a porta no SO.
        # Isso evita que o kernel do cliente envie o erro ICMP "Port Unreachable" que vimos no tcpdump.
        try:
            self.dummy_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.dummy_sock.bind((self.src_ip, self.sport))
        except Exception as e:
            print(f"[!] Aviso: Não foi possível reservar a porta {self.sport} no SO ({e}).")

    def listen_for_responses(self):
        """Roda em uma thread separada para escutar pacotes de resposta."""
        while True:
            try:
                packet, addr = self.recv_sock.recvfrom(65535)
                
                # O pacote capturado via IPPROTO_UDP no Linux começa com o cabeçalho IPv4
                ip_header = packet[:20]
                iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
                protocol = iph[6]
                src_ip_addr = socket.inet_ntoa(iph[8])
                
                # Filtra apenas UDP (17) e apenas os que vêm do nosso Servidor
                if protocol == 17 and src_ip_addr == self.dest_ip:
                    udp_header = packet[20:28]
                    udph = struct.unpack('!HHHH', udp_header)
                    src_port = udph[0]
                    dest_port = udph[1]
                    
                    # Filtra para garantir que a resposta veio para a nossa porta de origem (12345)
                    if dest_port == self.sport:
                        payload = packet[28:]
                        # Quebra a linha e imprime a resposta do servidor por cima do input atual
                        print(f"\n\n [+] Resposta do Servidor: {payload.decode('utf-8', errors='ignore')}")
                        print("Cliente: ", end="", flush=True) # Restaura o prompt visualmente

            except Exception as e:
                print(f"\n[-] Erro na thread de escuta: {e}")
                break

    def send_message(self, msg_str):
        """Monta o pacote bruto (IP + UDP + Payload) e envia."""
        msg_bytes = msg_str.encode('utf-8')

        # --- CABEÇALHO IP (20 Bytes) ---
        ip_ver_ihl = (4 << 4) + 5 
        ip_tos = 0
        ip_tot_len = 20 + 8 + len(msg_bytes)
        ip_id = 54321
        ip_frag_off = 0
        ip_ttl = 255
        ip_proto = socket.IPPROTO_UDP
        ip_check = 0 
        ip_saddr = socket.inet_aton(self.src_ip)
        ip_daddr = socket.inet_aton(self.dest_ip)

        ip_header = struct.pack('!BBHHHBBH4s4s', ip_ver_ihl, ip_tos, ip_tot_len,
                                ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check,
                                ip_saddr, ip_daddr)

        # --- CABEÇALHO UDP (8 Bytes) ---
        udp_len = 8 + len(msg_bytes)
        udp_check = 0 

        udp_header = struct.pack('!HHHH', self.sport, self.dport, udp_len, udp_check)

        # Envio do pacote completo
        packet = ip_header + udp_header + msg_bytes
        self.send_sock.sendto(packet, (self.dest_ip, 0))

    def start(self):
        """Inicia a thread de escuta e o loop principal de input."""
        # Configura a thread de escuta como Daemon para que feche quando o programa principal fechar
        listener = threading.Thread(target=self.listen_for_responses, daemon=True)
        listener.start()

        print(f"[*] Cliente RAW iniciado. Origem: {self.src_ip}:{self.sport} | Destino: {self.dest_ip}:{self.dport}")
        print("[*] Digite 'sair' para encerrar.\n")

        while True:
            try:
                msg = input("Cliente: ")
                if msg.lower() == 'sair':
                    print("Encerrando cliente...")
                    break
                
                if msg.strip():
                    self.send_message(msg)
            except KeyboardInterrupt:
                print("\n[!] Encerrando cliente...")
                break

if __name__ == "__main__":
    client = RawClient()
    client.start()