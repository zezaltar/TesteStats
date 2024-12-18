from waitress import serve
from app import app, pre_carregar_dados
import multiprocessing
import threading

def iniciar_pre_carregamento():
    """Inicia o pré-carregamento em uma thread separada"""
    thread = threading.Thread(target=pre_carregar_dados)
    thread.start()

if __name__ == '__main__':
    # Iniciar pré-carregamento em background
    iniciar_pre_carregamento()
    
    # Configurar número de threads baseado no número de CPUs
    num_threads = multiprocessing.cpu_count() * 2
    
    print("Iniciando servidor... (O pré-carregamento está acontecendo em background)")
    
    serve(
        app,
        host='0.0.0.0',
        port=5000,
        threads=num_threads,  # Número de threads para processar requisições
        channel_timeout=30,   # Timeout para conexões
        cleanup_interval=30,  # Intervalo para limpeza de conexões mortas
        connection_limit=1000,  # Limite de conexões simultâneas
        max_request_header_size=262144,  # Tamanho máximo do header (256KB)
        max_request_body_size=1073741824,  # Tamanho máximo do body (1GB)
        url_scheme='http'
    )
