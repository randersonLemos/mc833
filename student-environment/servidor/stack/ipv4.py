import struct
import socket

class IPv4:
    """
    Represents an IPv4 packet.
    """
    def __init__(self, raw_data: bytes):
        # Unpack the first 20 bytes for the fixed part of the header
        iph = struct.unpack('!BBHHHBBH4s4s', raw_data[:20])
        
        version_ihl = iph[0]
        self.version = version_ihl >> 4
        # IHL is the number of 32-bit words, so multiply by 4 for bytes
        self.ihl = (version_ihl & 0xF) * 4
        
        self.ttl = iph[5]
        self.protocol = iph[6]
        self.src_ip = socket.inet_ntoa(iph[8])
        self.dest_ip = socket.inet_ntoa(iph[9])
        self.header = raw_data[:self.ihl]
        
        # The payload is after the header, using the calculated header length
        self.payload = raw_data[self.ihl:]

    def is_udp(self) -> bool:
        """Checks if the payload is a UDP segment."""
        return self.protocol == 17

    def get_header(self) -> bytes:
        """Returns the raw header of the IPv4 packet."""
        return self.header

    def get_payload(self) -> bytes:
        """Returns the payload of the IPv4 packet."""
        return self.payload

    def print(self):
        """Prints the formatted IPv4 header."""
        print("\n[ Cabeçalho IPv4 ]")
        print(f"  |- IP Origem   : {self.src_ip}")
        print(f"  |- IP Destino  : {self.dest_ip}")
        print(f"  |- Versão      : {self.version}")
        print(f"  |- Tamanho HDR : {self.ihl} bytes")
        print(f"  |- TTL         : {self.ttl}")
        print(f"  |- Protocolo   : {self.protocol} (UDP)")