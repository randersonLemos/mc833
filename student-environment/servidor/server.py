import socket
import struct
import fcntl
from receiver import Receiver
from replier import Replier
import utils


def start_server():
    interface = "eth0"
    
    server_ip  = utils.get_ip_address(interface)
    server_mac = utils.get_mac_address(interface)

    if server_ip is None:
        print(f"[-] Erro fatal: Interface {interface} não encontrada ou sem endereço IP.")
        return
    
    # Inicializa as classes de recebimento e envio
    receiver = Receiver(server_ip)
    replier  = Replier()

    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
    s.bind((interface, 0))

    print("="*50)
    print("           SERVIDOR RAW SOCKET INICIADO")
    print("="*50)
    print(f" [*] Interface      : {interface}")
    print(f" [*] MAC Local      : {server_mac}")
    print(f" [*] IP Local       : {server_ip}")
    print(f" [*] Nível de Escuta: Camada de Enlace (Layer 2)")
    print(f" [*] Filtros Ativos : IPv4 -> Destino {server_ip} -> UDP")
    print(f" [*] Status         : Aguardando pacotes...\n")
    print("="*50 + "\n")

    while True:
            try:
                packet, addr = s.recvfrom(9999)

                # Passa o pacote bruto para o Receiver analisar
                received_pkt, error_msg = receiver.process(packet)

                # Se error_msg existir, o pacote foi descartado
                if error_msg:
                    # print(f"[DESCARTADO] {error_msg}") # Opcional: comente se estiver poluindo muito o terminal
                    continue

                # Chama a função extraída para imprimir os detalhes
                utils.print_packet_info(received_pkt)

                # Responde cliente
                payload_str = received_pkt.payload.decode(errors='ignore')
                reply_data = f"Servidor recebeu: {payload_str}".encode('utf-8')
                
                replier.send_reply(server_ip, received_pkt, reply_data)

            except KeyboardInterrupt:
                print("\n[!] Encerrando o servidor raw socket...")
                break
            except Exception as e:
                print(f"[-] Ocorreu um erro ao processar o pacote: {e}")


if __name__ == "__main__":
    start_server()