import os

def handle_catalog():
    """Handles the 'catalogo' command by listing video files."""
    videos_dir = "videos"
    try:
        # Lista apenas os arquivos com extensão .ts no diretório de vídeos
        video_files = [f for f in os.listdir(videos_dir) if f.endswith('.ts') and os.path.isfile(os.path.join(videos_dir, f))]

        if not video_files:
            return "[CATALOGO] Nenhum vídeo disponível no momento."
        else:
            # Cria uma lista numerada e formatada dos vídeos
            catalog_list = [f"  {i + 1}. {filename}" for i, filename in enumerate(video_files)]
            return "[CATALOGO] Vídeos disponíveis:\n" + "\n".join(catalog_list)
    except FileNotFoundError:
        return f"[ERRO] O diretório de vídeos '{videos_dir}' não foi encontrado no servidor."
    except Exception as e:
        return f"[ERRO] Falha ao acessar o catálogo: {e}"