import socket
import struct
import fcntl


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip_bytes = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15].encode('utf-8')))[20:24]
        return socket.inet_ntoa(ip_bytes)
    except OSError:
        return None

def get_mac_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15].encode('utf-8')))
        mac_bytes = info[18:24]
        return ':'.join(f'{b:02x}' for b in mac_bytes).upper()
    except OSError:
        return "Desconhecido"


def print_packet_info(received_pkt):
    """Imprime de forma organizada os detalhes do pacote validado."""
    print("\n" + "!"*50)
    print(f" [+] PACOTE UDP VALIDADO DE {received_pkt.src_ip}:{received_pkt.src_port}")
    print("!"*50)
    
    received_pkt.eth_frame.print()
    received_pkt.ip_packet.print()
    received_pkt.udp_segment.print()
    
    payload_str = received_pkt.payload.decode(errors='ignore')
    print("\n[ Payload ]")
    print(f"  |- Dados       : {repr(payload_str)}")
    print("="*50)