import socket
from receiver import Receiver
from replier import Replier
import utils
from command.catalog import handle_catalog
from command.help import handle_help
from command.stream import handle_stream

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
                continue

            # Chama a função extraída para imprimir os detalhes
            utils.print_packet_info(received_pkt)

            # 1. Extrai o texto do payload e remove espaços/quebras de linha extras
            payload_str = received_pkt.payload.decode(errors='ignore').strip()
            
            # 2. Converte para minúsculas apenas para facilitar a verificação do comando
            command_lower = payload_str.lower()
            
            # --- LÓGICA DE ROTEAMENTO DE COMANDOS ---
            
            if command_lower == "catalogo":
                reply_text = handle_catalog()

            elif command_lower.startswith("stream"):
                # Passamos os parâmetros necessários para a função no módulo
                response_text = handle_stream(payload_str, server_ip, received_pkt, replier)
                
                # Se a função retornar texto (ex: erro de arquivo não encontrado), nós enviamos
                if response_text:
                    reply_data = response_text.encode('utf-8')
                    replier.send_reply(server_ip, received_pkt, reply_data)
                
                # O comando stream controla seu próprio envio de bytes, então voltamos ao início do loop
                continue
            
            elif command_lower == "help":
                reply_text = handle_help()
                    
            else:
                # Nova resposta padrão orientando o usuário a usar o 'help'
                reply_text = f"[ERRO] Comando incorreto: '{payload_str}'. Digite 'help' para ver os comandos disponíveis do servidor."
                
            # --- FIM DA LÓGICA ---

            # 3. Codifica a resposta final e envia de volta ao cliente
            reply_data = reply_text.encode('utf-8')
            replier.send_reply(server_ip, received_pkt, reply_data)

        except KeyboardInterrupt:
            print("\n[!] Encerrando o servidor raw socket...")
            break
        except Exception as e:
            print(f"[-] Ocorreu um erro ao processar o pacote: {e}")

if __name__ == "__main__":
    start_server()