from scapy.all import *
from package.content import get_content_info

def forward(pkt, MAC_ROUTER_C, MAC_CLIENT, ETH_CLIENT):
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

    print(f"[<<<] {pkt[IP].src}:{sport} -> {pkt[IP].dst}:{dport} ({proto})")
    print(get_content_info(pkt))
    
    # Manually rebuild the Ethernet Frame for the Client
    pkt[Ether].src = MAC_ROUTER_C  # Coming out of the router
    pkt[Ether].dst = MAC_CLIENT    # Heading directly to the Client
    
    sendp(pkt, iface=ETH_CLIENT, verbose=False)
