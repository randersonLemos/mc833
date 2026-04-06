import socket
import struct
import threading
import sys
import queue
import os

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
        self.src_ip  = src_ip
        self.dest_ip = dest_ip
        self.sport = sport
        self.dport = dport
        
        # Fila thread-safe para armazenar a resposta de texto do servidor
        self.response_queue = queue.Queue() 

        # Garante que a pasta stream exista para salvar os vídeos
        self.stream_dir = "output"
        os.makedirs(self.stream_dir, exist_ok=True)
        self.video_file_path = os.path.join(self.stream_dir, "video_stream.ts")
        
        # Limpa o arquivo de vídeo anterior ao iniciar o cliente
        with open(self.video_file_path, "wb") as f:
            pass 

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
                
                # O pacote capturado via IPPROTO_UDP no Linux começa com o cabeçalho IPv4 (20 bytes)
                ip_header = packet[:20]
                iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
                protocol = iph[6]
                src_ip_addr = socket.inet_ntoa(iph[8])
                
                # Filtra apenas UDP (17) e apenas os que vêm do IP do Servidor
                if protocol == 17 and src_ip_addr == self.dest_ip:
                    # Cabeçalho UDP ocupa os bytes 20 a 28
                    udp_header = packet[20:28]
                    udph = struct.unpack('!HHHH', udp_header)
                    dest_port = udph[1]
                    
                    # Filtra para garantir que a resposta veio para a nossa porta de origem
                    if dest_port == self.sport:
                        payload = packet[28:]
                        
                        if not payload:
                            continue

                        # Verifica se o pacote é RTP (Versão 2 -> Byte inicial começa com 0x80 = 128)
                        # E verifica se tem pelo menos o tamanho do cabeçalho RTP (12 bytes)
                        if payload[0] == 0x80 and len(payload) > 12:
                            
                            # --- NOVO: Extrai o Sequence Number (Bytes 2 e 3 do payload) ---
                            # O formato '!H' extrai 2 bytes (unsigned short) em Big-Endian
                            seq_num = struct.unpack('!H', payload[2:4])[0]
                            print(f" [*] Cliente: Chunk de vídeo [#{seq_num}] recebido e salvo.")
                            
                            # 1. É vídeo! Remove os 12 bytes do cabeçalho RTP
                            video_chunk = payload[12:]
                            
                            # 2. Salva o chunk bruto no arquivo .ts
                            with open(self.video_file_path, "ab") as f:
                                f.write(video_chunk)
                                
                        else:
                            # Se não for vídeo, é uma mensagem de texto. Decodifica e envia para a fila.
                            mensagem = payload.decode('utf-8', errors='ignore').strip()
                            self.response_queue.put(mensagem)

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
        listener = threading.Thread(target=self.listen_for_responses, daemon=True)
        listener.start()

        print(f"[*] Cliente RAW iniciado. Origem: {self.src_ip}:{self.sport} | Destino: {self.dest_ip}:{self.dport}")
        print(f"[*] Os streams de vídeo serão salvos em: ./{self.video_file_path}")
        print(f"[*] Digite 'sair' para encerrar.\n")

        # Define o tempo máximo de espera (em segundos)
        TIMEOUT_SEGUNDOS = 3.0 

        while True:
            try:
                msg = input("Cliente: ")
                if msg.lower() == 'sair':
                    print("Encerrando cliente...")
                    break
                
                if msg.strip():
                    # Limpa mensagens antigas da fila antes de enviar uma nova
                    while not self.response_queue.empty():
                        self.response_queue.get_nowait()

                    self.send_message(msg)
                    
                    # Bloqueia aguardando a resposta com um tempo limite
                    try:
                        mensagem_recebida = self.response_queue.get(timeout=TIMEOUT_SEGUNDOS)
                        
                        # Estilização em formato de tabela/caixa
                        largura = 70
                        borda = "-" * largura
                        print(f"\n{borda}")
                        print(f" [+] Resposta do Servidor:")
                        print(f"{borda}")
                        print(f" {mensagem_recebida}")
                        print(f"{borda}\n")
                        
                        # UX: Dica para o usuário abrir o player de vídeo quando iniciar o stream
                        if msg.lower().startswith("stream") and "[STREAM]" in mensagem_recebida:
                            print(f" [*] O vídeo começou a ser baixado!")
                            print(f" [*] Em outro terminal do contêiner cliente, execute:\n")
                            print(f"     vlc ./{self.video_file_path}\n")
                            print(f" [*] (Ou use 'mpv ./{self.video_file_path}')\n")
                            
                    except queue.Empty:
                        # Ocorre se o get() exceder o tempo de TIMEOUT_SEGUNDOS
                        if not msg.lower().startswith("stream"):
                            print(f"\n[-] Tempo limite esgotado ({TIMEOUT_SEGUNDOS}s). Nenhuma resposta de texto do servidor.\n")
                        
            except KeyboardInterrupt:
                print("\n[!] Encerrando cliente...")
                break

if __name__ == "__main__":
    client = RawClient()
    client.start()