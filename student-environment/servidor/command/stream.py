import os
import time
import random
import struct

def handle_stream(payload_str, server_ip, received_pkt, replier):
    """Handles the 'stream' command and transmits the RTP video."""
    # Divide a string no primeiro espaço.
    parts = payload_str.split(" ", 1)

    if len(parts) > 1:
        media_name = parts[1]
        video_path = os.path.join("videos", media_name)
        
        # 1. Valida se o arquivo existe na pasta videos
        if not os.path.exists(video_path):
             return f"[ERRO] Arquivo '{media_name}' não encontrado no catálogo."
        
        # 2. Envia a mensagem de texto confirmando o início (opcional, mas bom para o cliente)
        inicio_msg = f"[STREAM] Iniciando a transmissão de '{media_name}'..."
        replier.send_reply(server_ip, received_pkt, inicio_msg.encode('utf-8'))
        
        # 3. Inicia a lógica de encapsulamento e envio RTP
        print(f"[*] Preparando pacotes RTP para o vídeo: {video_path}")
        
        version_padding_extension_csrc = 0x80
        marker_payloadtype = 0x21
        seq_num = random.randint(1, 10000)
        timestamp = 0
        ssrc = 12345678
        
        try:
            with open(video_path, "rb") as video_file:
                while True:
                    # Lê 1316 bytes (7 pacotes MPEG-TS)
                    chunk = video_file.read(1316)
                    if not chunk:
                        print("[*] Fim do arquivo de vídeo atingido.")
                        break
                    
                    # Monta o cabeçalho RTP de 12 bytes
                    rtp_header = struct.pack('!BBHII', 
                                             version_padding_extension_csrc, 
                                             marker_payloadtype, 
                                             seq_num, 
                                             timestamp, 
                                             ssrc)
                    
                    # Concatena cabeçalho com o vídeo e envia
                    rtp_packet = rtp_header + chunk
                    replier.send_reply(server_ip, received_pkt, rtp_packet, seq_num)
                    
                    # Atualiza os contadores
                    seq_num = (seq_num + 1) & 0xFFFF
                    timestamp = (timestamp + 3000) & 0xFFFFFFFF
                    
                    # Pausa para simular o bitrate e não travar a rede
                    time.sleep(0.005) 
                    
            # Retorna None para indicar que o stream acabou e o servidor não precisa enviar mais nada
            return None 
            
        except Exception as e:
            print(f"[-] Erro durante o streaming: {e}")
            return None
            
    else:
        return f"[ERRO] Comando incorreto: '{payload_str}'. Digite 'help' para ver os comandos disponíveis."