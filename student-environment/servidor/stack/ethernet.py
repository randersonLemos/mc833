import struct

def get_mac_addr(bytes_addr: bytes) -> str:
    """Formats a MAC address from bytes to a readable string."""
    return ':'.join(f'{b:02x}' for b in bytes_addr).upper()

class Ethernet:
    """
    Represents an Ethernet II frame.
    """
    def __init__(self, raw_data: bytes):
        dest, src, proto = struct.unpack('!6s6sH', raw_data[:14])

        self.dest_mac = get_mac_addr(dest)
        self.src_mac = get_mac_addr(src)
        self.proto = proto
        self.header = raw_data[:14]
        self.payload = raw_data[14:]

    def is_ipv4(self) -> bool:
        """Checks if the payload is an IPv4 packet."""
        return self.proto == 0x0800

    def get_header(self) -> bytes:
        """Returns the raw header of the Ethernet frame."""
        return self.header

    def get_payload(self) -> bytes:
        """Returns the payload of the Ethernet frame."""
        return self.payload

    def print(self):
        """Prints the formatted Ethernet header."""
        print("[ Cabeçalho Ethernet ]")
        print(f"  |- MAC Destino : {self.dest_mac}")
        print(f"  |- MAC Origem  : {self.src_mac}")
        print(f"  |- Protocolo   : {hex(self.proto)}")