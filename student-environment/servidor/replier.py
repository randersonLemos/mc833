import socket
import struct

class Replier:
    def __init__(self):
        try:
            self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        except PermissionError:
            print("[-] Erro: Requer privilégios de Root/Admin para criar RAW socket de envio.")
            self.send_sock = None

    def send_reply(self, server_ip, received_pkt, message_bytes, chunk_stamp=None):
        """Constrói e envia um pacote UDP bruto de volta ao remetente."""
        if not self.send_sock:
            return

        # --- CABEÇALHO IP (20 Bytes) ---
        ip_ver_ihl = (4 << 4) + 5 
        ip_tos = 0
        ip_tot_len = 20 + 8 + len(message_bytes)
        ip_id = 54322
        ip_frag_off = 0
        ip_ttl = 255
        ip_proto = socket.IPPROTO_UDP
        ip_check = 0 
        ip_saddr = socket.inet_aton(server_ip)
        ip_daddr = socket.inet_aton(received_pkt.src_ip) # Inverte o destino

        ip_header = struct.pack('!BBHHHBBH4s4s', ip_ver_ihl, ip_tos, ip_tot_len,
                                ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check,
                                ip_saddr, ip_daddr)

        # --- CABEÇALHO UDP (8 Bytes) ---
        sport = received_pkt.dest_port 
        dport = received_pkt.src_port  
        udp_len = 8 + len(message_bytes)
        udp_check = 0 

        udp_header = struct.pack('!HHHH', sport, dport, udp_len, udp_check)

        # Envio do pacote completo: IP + UDP + MSG
        packet = ip_header + udp_header + message_bytes
        
        try:
            self.send_sock.sendto(packet, (received_pkt.src_ip, 0))
            
            # --- LÓGICA DO LOG ATUALIZADA ---
            if chunk_stamp is not None:
                print(f" [*] Replier: Chunk de vídeo [#{chunk_stamp}] enviado para {received_pkt.src_ip}:{dport}")
            else:
                print(f" [*] Replier: Resposta de texto enviada para {received_pkt.src_ip}:{dport}")
                
        except Exception as e:
            print(f" [-] Replier Erro ao enviar pacote: {e}")