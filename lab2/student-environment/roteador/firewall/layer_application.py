from scapy.all import Raw, IP, TCP

# Define the malicious signature you are looking for.
# (Update this string based on what the attacker is sending in your specific lab)
MALICIOUS_SIGNATURE = b"rm -rf"  # Note the 'b' for byte-string


def filter_packet(pkt):
    """
    Filters packets based on Application Layer rules (Layer 7 - Payload Content).
    Returns True if the packet is clean, False if it contains the malicious signature.
    """
    # 1. Check if the packet actually contains a data payload
    if Raw in pkt:
        payload = pkt[Raw].load

        # 2. Search for the malicious string inside the payload
        if MALICIOUS_SIGNATURE in payload:
            print(f"[L7 FIREWALL] DROPPED Malicious Payload!")
            print(f"   Reason: Identified malicious signature '{MALICIOUS_SIGNATURE.decode(errors='ignore')}'.")

            # Print info just for logging, but DO NOT block the IP for future packets
            if IP in pkt and TCP in pkt:
                print(f"   Details: Packet dropped from dynamic IP {pkt[IP].src}:{pkt[TCP].sport}")
            print("-" * 60)

            # Drop the packet!
            return False

            # If the signature is not found, allow the packet to pass
    return True