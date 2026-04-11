from scapy.all import *
from package.content import get_content_info

def forward(pkt, MAC_ROUTER_S, MAC_SERVER, ETH_SERVER):
    # Print the detailed packet information table
    print(get_content_info(pkt, direction=">>> REQUEST (Client -> Server)"))

    # Manually rebuild the Ethernet Frame for the Server
    pkt[Ether].src = MAC_ROUTER_S
    pkt[Ether].dst = MAC_SERVER
    
    # Use sendp (Layer 2) to force it out the correct interface
    sendp(pkt, iface=ETH_SERVER, verbose=False)
