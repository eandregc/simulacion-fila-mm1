"""
Parámetros del proceso modelado: un cajero automático (ATM) del campus con una
sola máquina. Todas las tasas están en clientes por minuto y los tiempos en minutos.
"""

# Escenarios de demanda. El servicio es el mismo en todos (1.5 min en promedio por
# cliente, μ = 40 clientes/hora); lo que cambia es la tasa de llegadas λ.
ESCENARIOS = {
    "normal": {
        "descripcion": "Horario normal entre clases",
        "lam": 30 / 60,   # 30 clientes/hora
        "mu": 40 / 60,    # 40 clientes/hora
    },
    "pico": {
        "descripcion": "Hora pico (quincena, salida de clases)",
        "lam": 36 / 60,   # 36 clientes/hora
        "mu": 40 / 60,
    },
    "tranquilo": {
        "descripcion": "Horario con poca gente (noche, vacaciones)",
        "lam": 20 / 60,   # 20 clientes/hora
        "mu": 40 / 60,
    },
}

# Horizonte de cada corrida: una semana de operación continua del cajero.
DURACION_MIN = 7 * 24 * 60

# Los primeros minutos se descartan para medir el estado estable y no el arranque
# con la fila vacía.
CALENTAMIENTO_MIN = 500

# Utilizaciones ρ = λ/μ que se recorren en el modo --barrido.
RHO_BARRIDO = [0.10, 0.30, 0.50, 0.70, 0.80, 0.90, 0.95]
