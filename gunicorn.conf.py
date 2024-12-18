import multiprocessing

# Configurações de Workers
workers = multiprocessing.cpu_count() * 2 + 1  # Fórmula recomendada: (2 x NUM_CORES) + 1
worker_class = 'sync'  # Usando worker sync que é bom para aplicações Flask
worker_connections = 1000
timeout = 30
keepalive = 2

# Configurações de Performance
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30
preload_app = True

# Configurações de Buffer
forwarded_allow_ips = '*'
proxy_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Configurações de Log
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Configurações de Performance do Socket
backlog = 2048
