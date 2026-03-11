from stack import Ethernet, IPv4, UDP

class ReceivedPacket:
    """Objeto estruturado contendo todos os dados do pacote validado."""
    def __init__(self, src_mac, dest_mac, src_ip, dest_ip, src_port, dest_port, payload, eth_frame, ip_packet, udp_segment):
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.src_port = src_port
        self.dest_port = dest_port
        self.payload = payload
        
        # Guardamos as instâncias do stack.py para poder printar depois
        self.eth_frame = eth_frame
        self.ip_packet = ip_packet
        self.udp_segment = udp_segment

class Receiver:
    def __init__(self, server_ip):
        self.server_ip = server_ip

    def process(self, packet):
        """
        Processa pacotes brutos. 
        Retorna (ReceivedPacket, None) em caso de sucesso.
        Retorna (None, mensagem_de_erro) se o pacote for descartado.
        """
        # --- 1. Camada de Enlace (Ethernet) ---
        eth_frame = Ethernet(packet)

        if not eth_frame.is_ipv4():
            return None, f"Protocolo Ethernet não suportado: {hex(eth_frame.proto)}"

        # --- 2. Camada de Rede (IP) ---
        ip_packet = IPv4(eth_frame.get_payload())

        if ip_packet.dest_ip != self.server_ip:
            return None, f"Destino incorreto: {ip_packet.dest_ip} (Esperado: {self.server_ip})"

        if not ip_packet.is_udp():
            return None, f"Protocolo IP não é UDP: {ip_packet.protocol} (Origem: {ip_packet.src_ip})"

        # --- 3. Camada de Transporte (UDP) ---
        udp_segment = UDP(ip_packet.get_payload())

        # --- 4. Camada de Aplicação (Payload) ---
        payload_data = udp_segment.get_payload()

        # Cria o objeto de pacote recebido
        received_pkt = ReceivedPacket(
            src_mac=eth_frame.src_mac,
            dest_mac=eth_frame.dest_mac,
            src_ip=ip_packet.src_ip,
            dest_ip=ip_packet.dest_ip,
            src_port=udp_segment.src_port,
            dest_port=udp_segment.dest_port,
            payload=payload_data,
            eth_frame=eth_frame,
            ip_packet=ip_packet,
            udp_segment=udp_segment
        )
        
        return received_pkt, None