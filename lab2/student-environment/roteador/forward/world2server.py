from scapy.all import *
from package.content import get_content_info

def forward(pkt, MAC_ROUTER_S, MAC_SERVER, ETH_SERVER):
    if TCP in pkt:
        sport = pkt[TCP].sport
        dport = pkt[TCP].dport
        proto = "TCP"
    elif UDP in pkt:
        sport = pkt[UDP].sport
        dport = pkt[UDP].dport
        proto = "UDP"
    else:
        sport = 'N/A'
        dport = 'N/A'
        proto = "IP"
    
    print(f"\n[>>>] {pkt[IP].src}:{sport} -> {pkt[IP].dst}:{dport} ({proto})")
    print(get_content_info(pkt))
    
    # Manually rebuild the Ethernet Frame for the Server
    pkt[Ether].src = MAC_ROUTER_S  # Coming out of the router
    pkt[Ether].dst = MAC_SERVER    # Heading directly to the Server
    
    # Use sendp (Layer 2) to force it out the correct interface
    sendp(pkt, iface=ETH_SERVER, verbose=False)
