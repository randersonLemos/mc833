from scapy.all import *
import sys
from forward import world2server, server2world
from firewall import layer_network, layer_transport, rate_limiter
# 1. Interface mapping based on your 'ip addr'
ETH_SERVER = 'eth0'  # 10.0.1.x network
ETH_CLIENT = 'eth1'  # 10.0.2.x network

# 2. Get the router's own MACs to prevent infinite loops
MAC_ROUTER_C = get_if_hwaddr(ETH_CLIENT)
MAC_ROUTER_S = get_if_hwaddr(ETH_SERVER)

# ==========================================
# DYNAMIC ARP CACHE (MAC LEARNING)
# ==========================================
arp_cache = {}

print("[*] Resolving Server MAC address (Static).")
MAC_SERVER = getmacbyip('10.0.1.2')


def roteamento(pkt):
    # Ignore non-IP packets and packets the router just sent
    if IP not in pkt or pkt[Ether].src in [MAC_ROUTER_C, MAC_ROUTER_S]:
        return

    ip_layer = pkt[IP]
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst

    # ==========================================
    # LEARN THE MAC ADDRESS dynamically
    # ==========================================
    if Ether in pkt:
        arp_cache[src_ip] = pkt[Ether].src

    # ==========================================
    # FIREWALL INTEGRATION
    # ==========================================
    if not layer_network.filter_packet(pkt) or \
            not layer_transport.filter_packet(pkt) or \
            not rate_limiter.filter_packet(pkt):
        return  # Packet dropped by firewall

    # ==========================================
    # THE CHECKSUM FIX (CRITICAL FOR DOCKER)
    # ==========================================
    del pkt[IP].chksum
    if TCP in pkt:
        del pkt[TCP].chksum
    elif UDP in pkt:
        del pkt[UDP].chksum
    # ==========================================

    # --- DIRECTION A: REQUEST (Client -> Server) ---
    if dst_ip == '10.0.1.2':
        world2server.forward(pkt, MAC_ROUTER_S, MAC_SERVER, ETH_SERVER)

    # --- DIRECTION B: REPLY (Server -> Client) ---
    elif src_ip == '10.0.1.2':
        # 1. Check our learned memory for the client's MAC
        dynamic_client_mac = arp_cache.get(dst_ip)

        # 2. Fallback to Scapy's ARP resolution
        if not dynamic_client_mac:
            dynamic_client_mac = getmacbyip(dst_ip)

        # 3. Forward or drop
        if dynamic_client_mac:
            server2world.forward(pkt, MAC_ROUTER_C, dynamic_client_mac, ETH_CLIENT)
        else:
            print(f"[-] Dropped packet: Could not resolve MAC for dynamic IP {dst_ip}")


def main():
    global MAC_SERVER

    if not MAC_SERVER:
        print("[-] WARNING: Could not resolve Server MAC automatically.")
        print("[-] If traffic doesn't flow, try pinging the router from the server first.")

    print(f"[*] Software Router & Firewall ACTIVE.")
    print(f"[*] Routing between {ETH_CLIENT} and {ETH_SERVER} (Dynamic Client IPs Supported).")
    print("-" * 65)

    # Filter only for your lab subnet
    sniff(prn=roteamento, store=0, iface=[ETH_CLIENT, ETH_SERVER], filter="net 10.0.0.0/16")


if __name__ == "__main__":
    main()