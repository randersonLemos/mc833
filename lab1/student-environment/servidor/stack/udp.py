import struct

class UDP:
    """
    Represents a UDP segment.
    """
    # Dicionário de portas UDP comuns e seus serviços
    COMMON_PORTS = {
        53: "DNS (Domain Name System)",
        67: "DHCP Server",
        68: "DHCP Client",
        69: "TFTP (Trivial File Transfer Protocol)",
        123: "NTP (Network Time Protocol)",
        161: "SNMP (Simple Network Management Protocol)",
        1900: "SSDP (Simple Service Discovery Protocol)",
        5353: "mDNS (Multicast DNS)",
        9999: "Servidor Customizado (Lab)"
    }

    def __init__(self, raw_data: bytes):
        # Unpack the 8-byte UDP header
        udph = struct.unpack('!HHHH', raw_data[:8])
        
        self.src_port = udph[0]
        self.dest_port = udph[1]
        self.length = udph[2]
        self.checksum = udph[3]
        self.header = raw_data[:8]
        
        self.payload = raw_data[8:]

    def get_service_name(self, port: int) -> str:
        """Retorna o nome do serviço associado à porta, se conhecido."""
        return self.COMMON_PORTS.get(port, "Desconhecido")

    def get_header(self) -> bytes:
        """Returns the raw header of the UDP segment."""
        return self.header

    def get_payload(self) -> bytes:
        """Returns the payload of the UDP segment."""
        return self.payload

    def print(self):
        """Prints the formatted UDP header with service names."""
        src_service = self.get_service_name(self.src_port)
        dest_service = self.get_service_name(self.dest_port)

        print("\n[ Cabeçalho UDP ]")
        print(f"  |- Porta Origem: {self.src_port} ({src_service})")
        print(f"  |- Porta Dest  : {self.dest_port} ({dest_service})")
        print(f"  |- Tamanho UDP : {self.length}")
        print(f"  |- Checksum    : {hex(self.checksum)}")