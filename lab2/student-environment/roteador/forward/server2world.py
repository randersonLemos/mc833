from scapy.all import *
from package.content import get_content_info

def forward(pkt, MAC_ROUTER_C, MAC_CLIENT, ETH_CLIENT):
    # Print the detailed packet information table
    print(get_content_info(pkt, direction="<<< REPLY (Server -> Client)"))
    
    # Manually rebuild the Ethernet Frame for the Client
    pkt[Ether].src = MAC_ROUTER_C
    pkt[Ether].dst = MAC_CLIENT
    
    sendp(pkt, iface=ETH_CLIENT, verbose=False)
