from scapy.all import *


def get_content_info(pkt, direction="", pkt_num=1):
    """
    Inspects a Scapy packet and returns a formatted, table-like string with its details,
    incorporating OSI/TCP/IP layers, relative packet numbers, and strict alignment.
    """
    info = []

    # Define strict column widths for perfect alignment
    W_LAYER = 15
    W_LABEL = 5
    W_VAL = 17
    W_EXTRA = 15

    # Inner width calculation:
    # Layer(15) + " | "(3) + Label(5) + " "(1) + Src(17) + " -> "(4) + Dst(17) + " | "(3) + Extra(15) = 80
    INNER_WIDTH = W_LAYER + 3 + W_LABEL + 1 + W_VAL + 4 + W_VAL + 3 + W_EXTRA
    FULL_WIDTH = INNER_WIDTH + 2  # +2 for left/right padding inside the border

    # --- Table Header ---
    info.append("  ┌" + "─" * FULL_WIDTH + "┐")

    # Combine the Relative Packet Number, Sequence Number (if TCP), and Direction
    header_text = f"PACKET #{pkt_num} | {direction}"
    if TCP in pkt:
        header_text = f"PACKET #{pkt_num} | SEQ #{pkt[TCP].seq} | {direction}"

    info.append(f"  │ {header_text:^{FULL_WIDTH - 2}} │")
    info.append("  ├" + "─" * FULL_WIDTH + "┤")

    # --- L2: Data Link Layer ---
    if Ether in pkt:
        desc = "L2 (Data Link)"
        label = "MAC:"
        src = pkt[Ether].src
        dst = pkt[Ether].dst
        extra = ""
        line = f"{desc:<{W_LAYER}} | {label:<{W_LABEL}} {src:<{W_VAL}} -> {dst:<{W_VAL}} | {extra:<{W_EXTRA}}"
        info.append(f"  │ {line} │")

    # --- L3: Network Layer ---
    if IP in pkt:
        desc = "L3 (Network)"
        label = "IP:"
        src = pkt[IP].src
        dst = pkt[IP].dst
        extra = f"TTL: {pkt[IP].ttl}"
        line = f"{desc:<{W_LAYER}} | {label:<{W_LABEL}} {src:<{W_VAL}} -> {dst:<{W_VAL}} | {extra:<{W_EXTRA}}"
        info.append(f"  │ {line} │")

    # --- L4: Transport Layer ---
    if TCP in pkt:
        # Line 1: Ports and Flags
        desc = "L4 (Transport)"
        label = "Port:"
        src = str(pkt[TCP].sport)
        dst = str(pkt[TCP].dport)
        extra = f"Flags: {pkt[TCP].flags}"
        line1 = f"{desc:<{W_LAYER}} | {label:<{W_LABEL}} {src:<{W_VAL}} -> {dst:<{W_VAL}} | {extra:<{W_EXTRA}}"
        info.append(f"  │ {line1} │")

        # Line 2: TCP Details (Ack, Win, Len) mapped directly under the columns
        desc_pad = ""
        label_ack = "Ack:"
        ack_val = str(pkt[TCP].ack)
        win_val = f"Win: {pkt[TCP].window}"  # Uses the destination column for Window alignment
        extra_len = f"Len: {len(pkt[TCP].payload)}"
        line2 = f"{desc_pad:<{W_LAYER}} | {label_ack:<{W_LABEL}} {ack_val:<{W_VAL}} -> {win_val:<{W_VAL}} | {extra_len:<{W_EXTRA}}"
        info.append(f"  │ {line2} │")

    elif UDP in pkt:
        desc = "L4 (Transport)"
        label = "Port:"
        src = str(pkt[UDP].sport)
        dst = str(pkt[UDP].dport)
        extra = ""
        line = f"{desc:<{W_LAYER}} | {label:<{W_LABEL}} {src:<{W_VAL}} -> {dst:<{W_VAL}} | {extra:<{W_EXTRA}}"
        info.append(f"  │ {line} │")

    # --- L7: Application Layer (Payload Section) ---
    if Raw in pkt and pkt[Raw].load:
        info.append("  ├" + "─" * FULL_WIDTH + "┤")
        info.append(f"  │ {'L7 (Application) - PAYLOAD':^{FULL_WIDTH - 2}} │")
        info.append("  ├" + "─" * FULL_WIDTH + "┤")
        try:
            payload_repr = repr(pkt[Raw].load)
            max_payload_width = FULL_WIDTH - 2
            # Split the payload string into lines that perfectly fit the table width
            payload_lines = [payload_repr[i:i + max_payload_width] for i in
                             range(0, len(payload_repr), max_payload_width)]
            for p_line in payload_lines:
                info.append(f"  │ {p_line:<{max_payload_width}} │")
        except Exception:
            info.append(f"  │ {'[Could not decode or display payload]':<{FULL_WIDTH - 2}} │")

    # --- Table Footer ---
    info.append("  └" + "─" * FULL_WIDTH + "┘")

    return "\n".join(info)