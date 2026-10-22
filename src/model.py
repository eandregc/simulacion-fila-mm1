"""
Fila M/M/1 simulada con eventos discretos (SimPy).

Notación de Kendall  A / S / c / K / N / D  =  M / M / 1 / ∞ / ∞ / FIFO
    A = M   llegadas de Poisson: tiempos entre llegadas exponenciales con tasa λ
    S = M   tiempos de servicio exponenciales con tasa μ
    c = 1   un solo servidor
    K = ∞   capacidad ilimitada de la fila
    N = ∞   población de clientes ilimitada
    D = FIFO  se atiende en orden de llegada
"""

import numpy as np
import simpy


def teoria(lam, mu):
    """Medidas de desempeño en estado estable de la M/M/1 (requiere ρ = λ/μ < 1)."""
    rho = lam / mu
    if rho >= 1:
        raise ValueError(f"ρ = {rho:.3f} ≥ 1: la fila crece sin límite y no hay estado estable")
    return {
        "rho": rho,                       # utilización del servidor
        "P0": 1 - rho,                    # probabilidad de que el sistema esté vacío
        "L": rho / (1 - rho),             # clientes promedio en el sistema
        "Lq": rho ** 2 / (1 - rho),       # clientes promedio en la fila
        "W": 1 / (mu - lam),              # tiempo promedio en el sistema
        "Wq": rho / (mu - lam),           # tiempo promedio en la fila
        "P_espera": rho,                  # probabilidad de llegar y tener que esperar
    }


def prob_n(lam, mu, n):
    """P(n clientes en el sistema) = (1 − ρ) ρⁿ."""
    rho = lam / mu
    return (1 - rho) * rho ** n


class FilaMM1:
    def __init__(self, lam, mu, semilla=None):
        self.lam = lam
        self.mu = mu
        self.rng = np.random.default_rng(semilla)
        self.env = simpy.Environment()
        self.servidor = simpy.Resource(self.env, capacity=1)
        self.en_sistema = 0
        self.cambios = [(0.0, 0)]   # (tiempo, clientes en el sistema) tras cada evento
        self.eventos = []           # bitácora: (tiempo, cliente, evento, en sistema, en fila)
        self.clientes = []          # por cliente: llegada, inicio y fin de servicio

    # ---------------- Procesos de SimPy ----------------

    def llegadas(self):
        """Genera clientes separados por tiempos exponenciales con media 1/λ."""
        i = 0
        while True:
            yield self.env.timeout(self.rng.exponential(1 / self.lam))
            i += 1
            self.env.process(self.cliente(i))

    def cliente(self, i):
        """Un cliente llega, espera su turno, se atiende y se va."""
        llegada = self.env.now
        self._registrar(i, "llegada", +1)
        with self.servidor.request() as turno:
            yield turno
            inicio = self.env.now
            servicio = self.rng.exponential(1 / self.mu)
            self._registrar(i, "inicio servicio", 0)
            yield self.env.timeout(servicio)
        self._registrar(i, "salida", -1)
        self.clientes.append({"id": i, "llegada": llegada, "inicio": inicio,
                              "salida": self.env.now, "servicio": servicio})

    def _registrar(self, i, evento, cambio):
        self.en_sistema += cambio
        if cambio:
            self.cambios.append((self.env.now, self.en_sistema))
        en_fila = max(self.en_sistema - 1, 0)   # con un servidor, uno se atiende y el resto espera
        self.eventos.append((self.env.now, i, evento, self.en_sistema, en_fila))

    def correr(self, duracion):
        self.env.process(self.llegadas())
        self.env.run(until=duracion)
        return self

    # ---------------- Estadísticas ----------------

    def tiempo_por_estado(self, desde, hasta):
        """Minutos que el sistema pasó con n clientes, para cada n, dentro de [desde, hasta]."""
        tiempos = {}
        siguientes = self.cambios[1:] + [(hasta, None)]
        for (t0, n), (t1, _) in zip(self.cambios, siguientes):
            a, b = max(t0, desde), min(t1, hasta)
            if b > a:
                tiempos[n] = tiempos.get(n, 0.0) + (b - a)
        return tiempos

    def resultados(self, calentamiento, duracion):
        """
        L, Lq, ρ y Pn se promedian ponderando por el tiempo que duró cada estado.
        W y Wq se promedian sobre los clientes que llegaron después del calentamiento.
        """
        tiempos = self.tiempo_por_estado(calentamiento, duracion)
        total = sum(tiempos.values())
        atendidos = [c for c in self.clientes if c["llegada"] >= calentamiento]
        espera = np.array([c["inicio"] - c["llegada"] for c in atendidos])
        sistema = np.array([c["salida"] - c["llegada"] for c in atendidos])
        return {
            "rho": 1 - tiempos.get(0, 0.0) / total,
            "P0": tiempos.get(0, 0.0) / total,
            "L": sum(n * t for n, t in tiempos.items()) / total,
            "Lq": sum(max(n - 1, 0) * t for n, t in tiempos.items()) / total,
            "W": sistema.mean(),
            "Wq": espera.mean(),
            "P_espera": np.mean(espera > 0),
            "atendidos": len(atendidos),
            "max_sistema": max(tiempos),
            "Pn": {n: t / total for n, t in sorted(tiempos.items())},
        }

    def muestras_kendall(self):
        """Tiempos entre llegadas y de servicio observados, para revisar los supuestos M/M."""
        llegadas = np.sort([c["llegada"] for c in self.clientes])
        entre_llegadas = np.diff(np.concatenate([[0.0], llegadas]))
        servicios = np.array([c["servicio"] for c in self.clientes])
        return llegadas, entre_llegadas, servicios


def replicar(lam, mu, n_replicas, duracion, calentamiento, semilla=0):
    """Corre réplicas independientes y regresa la lista de resultados de cada una."""
    return [FilaMM1(lam, mu, semilla + r).correr(duracion).resultados(calentamiento, duracion)
            for r in range(n_replicas)]


def intervalo_confianza(valores, z=1.96):
    """Media e intervalo de confianza del 95 % (aproximación normal)."""
    valores = np.asarray(valores, dtype=float)
    media = valores.mean()
    margen = z * valores.std(ddof=1) / np.sqrt(len(valores))
    return media, media - margen, media + margen
