from scapy.all import TCP, Raw, IP

def filter_packet(pkt):
    """
    Filters packets based on transport layer rules (Layer 4 - TCP Flags & Payloads).
    Returns True if the packet is allowed, False if it should be dropped.
    """
    # If it is not a TCP packet (e.g., UDP or ICMP), this specific filter
    # does not apply, so we let it pass.
    if TCP not in pkt:
        return True

    flags = pkt[TCP].flags
    src_ip = pkt.getlayer(IP).src
    dst_ip = pkt.getlayer(IP).dst
    dport = pkt[TCP].dport

    # ==========================================
    # RULE 1: TCP NULL SCAN
    # ==========================================
    # Security Rationale: In the TCP protocol, every legitimate packet must have
    # at least one flag set to indicate its purpose (e.g., SYN to initiate, ACK to
    # acknowledge, FIN to close). A packet with zero flags is mathematically and
    # operationally unnatural. Attackers generate these "NULL" packets to sneak
    # past basic firewalls and observe how the target OS reacts, allowing them to
    # map out open and closed ports stealthily.
    if flags == 0 or flags == "":
        print(f"[L4 FIREWALL] DROPPED TCP NULL Scan!")
        print(f"   Reason: Packet has absolutely NO TCP flags set. This is an unnatural stealth probe.")
        print(f"   Details: {src_ip} -> {dst_ip}:{dport}")
        print("-" * 60)
        return False

    # ==========================================
    # RULE 2: TCP FIN SCAN
    # ==========================================
    # Security Rationale: The FIN flag is politely asking to close an existing,
    # active connection. Sending a standalone FIN packet to a server you have not
    # even established a connection with makes no sense. Attackers do this because
    # lazy firewalls often only block incoming "SYN" (start) packets. By sending
    # a "FIN" (stop) instead, the packet slips through the firewall, hits the server,
    # and the attacker maps the port based on the server's confused response.
    if flags == "F":
        print(f"[L4 FIREWALL] DROPPED TCP FIN Scan!")
        print(f"   Reason: Packet only has the FIN flag set but no connection exists. This is a scanner trick.")
        print(f"   Details: {src_ip} -> {dst_ip}:{dport}")
        print("-" * 60)
        return False

    # ==========================================
    # RULE 3: MALICIOUS SYN (DATA INJECTION)
    # ==========================================
    # Security Rationale: The SYN packet is strictly step one of the TCP 3-way handshake
    # ("Hello, can we open a connection?"). By protocol standards, it should only
    # contain TCP headers and setup options (like window size). It should NEVER carry
    # actual application payload data. Attackers attach data payloads to SYN packets
    # to attempt buffer overflows, test for protocol smuggling vulnerabilities, or
    # bypass poorly configured packet filters.
    if flags == "S" and Raw in pkt:
        payload_size = len(pkt[Raw].load)
        print(f"[L4 FIREWALL] DROPPED Suspicious SYN (Data Attached)!")
        print(f"   Reason: A standard TCP SYN handshake packet should NEVER carry a data payload.")
        print(f"   Details: {src_ip} -> {dst_ip}:{dport} | Payload Size: {payload_size} bytes")
        print("-" * 60)
        return False

    # ==========================================
    # RULE 4: TCP XMAS SCAN (Christmas Tree)
    # ==========================================
    # Security Rationale: This packet turns on the FIN (Finish), PSH (Push data),
    # and URG (Urgent) flags all at the exact same time. This is a complete logical
    # contradiction: it translates to "I am completely done talking to you, but also
    # process this emergency data immediately." Standard operating systems will never
    # naturally generate this combination. It is a signature technique used by tools
    # like Nmap to force target systems to generate anomalous error responses.
    if flags == "FPU":
        print(f"[L4 FIREWALL] DROPPED TCP XMAS Scan!")
        print(f"   Reason: Flags FIN, PSH, and URG are set simultaneously. This logically contradicts itself.")
        print(f"   Details: Flags: [{flags}] | {src_ip} -> {dst_ip}:{dport}")
        print("-" * 60)
        return False

    # If the packet passes all Transport Layer security checks, allow it to proceed.
    return True