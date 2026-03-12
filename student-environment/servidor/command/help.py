def handle_help():
    """Handles the 'help' command by returning the help text."""
    return (
        "[AJUDA] Comandos disponíveis no Servidor:\n"
        "  - catalogo             : Lista todos os filmes disponíveis.\n"
        "  - stream <nome_filme>  : Inicia a transmissão do filme escolhido.\n"
        "  - help                 : Mostra este menu de ajuda."
    )