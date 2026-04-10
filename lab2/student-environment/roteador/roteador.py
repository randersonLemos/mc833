from scapy.all import *

# 1. Interface mapping
ETH_SERVER = 'eth0'  # 10.0.1.x network
ETH_CLIENTS = 'eth1' # 10.0.2.x network

def roteamento(pkt):
    # Ignore non-IP packets
    if IP not in pkt:
        return

    # 🚨 CRITICAL: We MUST keep the checksum deletion.
    # Even without manual MACs, Scapy needs to recalculate 
    # the math because the TTL changes and we are re-sending.
    del pkt[IP].chksum
    if TCP in pkt:
        del pkt[TCP].chksum
    elif UDP in pkt:
        del pkt[UDP].chksum

    ip_layer = pkt[IP]
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst

    # --- DIRECTION A: REQUEST (Client -> Server) ---
    if dst_ip == '10.0.1.2':
        print(f"🚀 [>>>] {src_ip} -> {dst_ip} (Layer 3 Forward)")
        # We send ONLY the IP layer. Scapy builds the Ethernet header automatically.
        send(ip_layer, iface=ETH_SERVER, verbose=False)

    # --- DIRECTION B: REPLY (Server -> Client) ---
    elif src_ip == '10.0.1.2' and dst_ip == '10.0.2.2':
        print(f"✅ [<<<] {src_ip} -> {dst_ip} (Layer 3 Forward)")
        # Again, just the IP layer out of the client interface.
        send(ip_layer, iface=ETH_CLIENTS, verbose=False)

def main():
    print(f"[*] Simplified L3 Router ACTIVE")
    print(f"[*] Routing between {ETH_CLIENTS} and {ETH_SERVER}")
    print("-" * 50)
    
    # We sniff everything, but our 'send' logic handles the rest.
    sniff(prn=roteamento, store=0, iface=[ETH_CLIENTS, ETH_SERVER], filter="net 10.0.0.0/16")

if __name__ == "__main__":
    main()