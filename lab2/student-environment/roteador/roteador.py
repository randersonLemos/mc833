from scapy.all import *
import sys
from forward import world2server, server2world

# 1. Interface mapping based on your 'ip addr'
ETH_SERVER = 'eth0'  # 10.0.1.x network
ETH_CLIENT = 'eth1' # 10.0.2.x network

# 2. Get the router's own MACs to prevent infinite loops
MAC_ROUTER_C = get_if_hwaddr(ETH_CLIENT)
MAC_ROUTER_S = get_if_hwaddr(ETH_SERVER)

print("[*] Resolving target MAC addresses.")
# 3. Discover target MACs so we can build valid Ethernet frames
MAC_SERVER = getmacbyip('10.0.1.2')
MAC_CLIENT = getmacbyip('10.0.2.2')

def roteamento(pkt):
    # Ignore non-IP packets and packets the router just sent
    if IP not in pkt or pkt[Ether].src in [MAC_ROUTER_C, MAC_ROUTER_S]:
        return

    # ==========================================
    # 🚨 THE CHECKSUM FIX (CRITICAL FOR DOCKER)
    # ==========================================
    # Deleting the checksums forces Scapy to recalculate valid ones.
    # Without this, the kernel will drop the packets because the 
    # math is corrupted when we change the MAC addresses!
    del pkt[IP].chksum
    if TCP in pkt:
        del pkt[TCP].chksum
    elif UDP in pkt:
        del pkt[UDP].chksum
    # ==========================================

    ip_layer = pkt[IP]
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst

    # --- DIRECTION A: REQUEST (Client -> Server) ---
    if dst_ip == '10.0.1.2':
        world2server.forward(pkt, MAC_ROUTER_S, MAC_SERVER, ETH_SERVER)

    # --- DIRECTION B: REPLY (Server -> Client) ---
    elif src_ip == '10.0.1.2' and dst_ip == '10.0.2.2':
        server2world.forward(pkt, MAC_ROUTER_C, MAC_CLIENT, ETH_CLIENT)
    
    # --- EVERYTHING ELSE ---
    else:
        # Filter out multicast/broadcast noise (239.x and 224.x) to keep logs clean
        if not dst_ip.startswith("239.") and not dst_ip.startswith("224."):
            print(f"[.] Passing: {src_ip} -> {dst_ip}")

def main():
    global MAC_SERVER, MAC_CLIENT
    
    if not MAC_SERVER or not MAC_CLIENT:
        print("[-] WARNING: Could not resolve MACs automatically.")
        print("[-] If traffic doesn't flow, try pinging the router from the client and server first.")

    print(f"[*] Software Router ACTIVE.")
    print(f"[*] Routing between {ETH_CLIENT} and {ETH_SERVER}.")
    print("-" * 50)
    
    # Filter only for your lab subnet to ignore external internet updates
    sniff(prn=roteamento, store=0, iface=[ETH_CLIENT, ETH_SERVER], filter="net 10.0.0.0/16")

if __name__ == "__main__":
    main()