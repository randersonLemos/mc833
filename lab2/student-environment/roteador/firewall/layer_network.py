from scapy.all import IP

def filter_packet(pkt):
    """
    Filters packets based on network layer rules (Layer 3 - IP Addresses).
    Returns True if the packet is allowed, False if it should be dropped.
    """
    # Allow non-IP traffic to pass (e.g., ARP).
    # Blocking ARP here would break the network since the OS relies on it for MAC resolution.
    if IP not in pkt:
        return True

    src_ip = pkt[IP].src
    dst_ip = pkt[IP].dst

    # ==========================================
    # RULE 1: LATERAL / NON-SERVER TRAFFIC
    # ==========================================
    # Security Rationale: In this specific lab environment, the router is designed
    # to act as a strict gateway protecting a single server (10.0.1.2).
    # If a client attempts to communicate with another client (e.g., 10.0.2.10 talking to 10.0.2.20)
    # or attempts to route out to the internet, it is a violation of the isolation policy.
    # Dropping lateral traffic prevents an infected client machine from scanning or attacking
    # its neighbors on the same network.
    if dst_ip != '10.0.1.2' and src_ip != '10.0.1.2':
        print(f"[L3 FIREWALL] DROPPED Lateral/Non-Server Traffic!")
        print(f"   Reason: Packet is strictly isolated. It is not destined for or coming from the Server.")
        print(f"   Details: {src_ip} -> {dst_ip}")
        print("-" * 60)
        return False

    # ==========================================
    # RULE 2: UNAUTHORIZED SUBNET / IP SPOOFING
    # ==========================================
    # Security Rationale: The firewall trusts that legitimate requests to the server
    # will only come from the physically designated client subnet (10.0.2.x).
    # If a packet arrives destined for the server, but its source IP claims to be
    # from a completely different network (e.g., 8.8.8.8, or 10.0.5.x), it strongly indicates
    # IP Spoofing. An attacker is manipulating their packet headers to disguise their origin,
    # often to bypass IP-based authentication or conduct a Denial of Service (DoS) attack.
    if dst_ip == '10.0.1.2' and not src_ip.startswith('10.0.2.'):
        print(f"[L3 FIREWALL] DROPPED Unauthorized Subnet / Spoofed IP!")
        print(f"   Reason: Incoming request to the Server is NOT from the allowed 10.0.2.x client network.")
        print(f"   Details: {src_ip} -> {dst_ip}")
        print("-" * 60)
        return False

    # If the packet passes all Layer 3 security checks, allow it to proceed to Transport Layer inspection.
    return True