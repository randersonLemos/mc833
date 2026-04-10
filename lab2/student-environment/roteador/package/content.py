from scapy.all import *

def get_content_info(pkt):
    """
    Inspects a Scapy packet and returns a formatted, table-like string with its details.
    """
    info = []
    width = 80  # Total width of the table

    # --- Table Header ---
    info.append("  ┌" + "─" * (width - 2) + "┐")
    info.append(f"  │{'PACKET DETAILS'.center(width - 2)}│")
    info.append("  ├" + "─" * (width - 2) + "┤")

    # --- Layers ---
    if Ether in pkt:
        line = f"  L2 Ether | MAC: {pkt[Ether].src} -> {pkt[Ether].dst}"
        info.append(f"  │ {line:<{width - 4}} │")
    
    if IP in pkt:
        line = f"  L3 IP    | IP:  {pkt[IP].src:<21} -> {pkt[IP].dst:<21} | TTL: {pkt[IP].ttl}"
        info.append(f"  │ {line:<{width - 4}} │")

    if TCP in pkt:
        line = f"  L4 TCP   | Port: {str(pkt[TCP].sport):<20} -> {str(pkt[TCP].dport):<20} | Flags: {pkt[TCP].flags}"
        info.append(f"  │ {line:<{width - 4}} │")
    elif UDP in pkt:
        line = f"  L4 UDP   | Port: {str(pkt[UDP].sport):<20} -> {str(pkt[UDP].dport):<20}"
        info.append(f"  │ {line:<{width - 4}} │")

    # --- Payload Section ---
    if Raw in pkt and pkt[Raw].load:
        info.append("  ├" + "─" * (width - 2) + "┤")
        info.append(f"  │{'PAYLOAD'.center(width - 2)}│")
        info.append("  ├" + "─" * (width - 2) + "┤")
        try:
            payload_repr = repr(pkt[Raw].load)
            # Wrap payload content to fit inside the table
            max_payload_width = width - 6
            payload_lines = [payload_repr[i:i+max_payload_width] for i in range(0, len(payload_repr), max_payload_width)]
            for line in payload_lines:
                info.append(f"  │ {line:<{width-4}} │")
        except Exception:
            info.append(f"  │ {'[Could not decode or display payload]':<{width-4}} │")

    # --- Table Footer ---
    info.append("  └" + "─" * (width - 2) + "┘")

    return "\n".join(info)
