"""
Simulación de una fila M/M/1 (cajero automático) con eventos discretos.

Uso:
    python main.py                              # escenario normal, 30 réplicas de una semana
    python main.py --escenario pico
    python main.py --lam 0.5 --mu 0.8           # tasas propias (clientes/min)
    python main.py --replicas 50 --semilla 7
    python main.py --barrido                    # W simulado vs teórico para varios ρ
"""

import argparse
import sys

import numpy as np

from data import CALENTAMIENTO_MIN, DURACION_MIN, ESCENARIOS, RHO_BARRIDO
from model import FilaMM1, intervalo_confianza, prob_n, replicar, teoria

MEDIDAS = [
    ("rho", "Utilización ρ", ""),
    ("P0", "P0 (cajero libre)", ""),
    ("L", "L  (en el sistema)", "clientes"),
    ("Lq", "Lq (en la fila)", "clientes"),
    ("W", "W  (en el sistema)", "min"),
    ("Wq", "Wq (en la fila)", "min"),
    ("P_espera", "P(tener que esperar)", ""),
]


def titulo(texto):
    print(f"\n{'=' * 72}\n{texto}\n{'=' * 72}")


def revisar_kendall(fila, lam, mu):
    """Comprueba con los datos simulados que el proceso se comporta como M/M/1."""
    llegadas, entre, servicios = fila.muestras_kendall()
    titulo("Supuestos de Kendall (M/M/1/∞/∞/FIFO) en la corrida simulada")
    print(f"{'':32}{'esperado':>12}{'observado':>12}")
    print(f"{'Media entre llegadas (min)':32}{1 / lam:12.3f}{entre.mean():12.3f}")
    print(f"{'CV entre llegadas (σ/media)':32}{1.0:12.3f}{entre.std() / entre.mean():12.3f}")
    print(f"{'Media de servicio (min)':32}{1 / mu:12.3f}{servicios.mean():12.3f}")
    print(f"{'CV de servicio (σ/media)':32}{1.0:12.3f}{servicios.std() / servicios.mean():12.3f}")

    # En un proceso de Poisson el número de llegadas en un intervalo tiene media = varianza.
    conteos = np.histogram(llegadas, bins=np.arange(0, llegadas[-1], 10))[0]
    print(f"{'Llegadas en 10 min: media':32}{10 * lam:12.3f}{conteos.mean():12.3f}")
    print(f"{'Llegadas en 10 min: varianza':32}{10 * lam:12.3f}{conteos.var():12.3f}")

    # Falta de memoria: P(T > s + t | T > s) = P(T > t)
    s, t = 1 / lam, 1 / lam
    sin_memoria = np.mean(entre[entre > s] > s + t)
    print(f"{'P(T > 2/λ | T > 1/λ)':32}{np.exp(-lam * t):12.3f}{sin_memoria:12.3f}")
    print("\nUn coeficiente de variación ≈ 1, media ≈ varianza en los conteos y la falta de")
    print("memoria confirman llegadas de Poisson y servicios exponenciales.")


def bitacora(fila, n_eventos):
    titulo(f"Bitácora de eventos discretos (primeros {n_eventos})")
    print(f"{'reloj (min)':>12}  {'cliente':>7}  {'evento':<16} {'en sistema':>10} {'en fila':>8}")
    for reloj, i, evento, n, q in fila.eventos[:n_eventos]:
        print(f"{reloj:12.3f}  {i:>7}  {evento:<16} {n:>10} {q:>8}")
    print("\nEl reloj salta de un evento al siguiente; entre eventos el estado no cambia.")


def comparar(lam, mu, replicas):
    teo = teoria(lam, mu)
    titulo(f"Simulación ({len(replicas)} réplicas) vs teoría M/M/1")
    print(f"{'Medida':<24}{'teoría':>10}{'simulación':>12}   {'IC 95 %':<22}{'¿teoría dentro?'}")
    for clave, nombre, unidad in MEDIDAS:
        media, bajo, alto = intervalo_confianza([r[clave] for r in replicas])
        dentro = "sí" if bajo <= teo[clave] <= alto else "no"
        ic = f"[{bajo:.4f}, {alto:.4f}]"
        print(f"{nombre:<24}{teo[clave]:10.4f}{media:12.4f}   {ic:<22}{dentro:<6}{unidad}")

    atendidos = np.mean([r["atendidos"] for r in replicas])
    maximo = max(r["max_sistema"] for r in replicas)
    print(f"\nClientes atendidos por réplica: {atendidos:.0f}   "
          f"Máximo de clientes en el sistema observado: {maximo}")

    titulo("Distribución del número de clientes en el sistema  Pn = (1 − ρ) ρⁿ")
    print(f"{'n':>3}{'teoría':>10}{'simulación':>12}")
    for n in range(11):
        sim = np.mean([r["Pn"].get(n, 0.0) for r in replicas])
        barra = "█" * int(round(sim * 100))
        print(f"{n:>3}{prob_n(lam, mu, n):10.4f}{sim:12.4f}  {barra}")
    cola = np.mean([sum(p for n, p in r["Pn"].items() if n > 10) for r in replicas])
    print(f"{'>10':>3}{teo['rho'] ** 11:10.4f}{cola:12.4f}")


def barrido(mu, n_replicas, semilla):
    titulo(f"Efecto de la utilización ρ = λ/μ  (μ = {mu * 60:.0f} clientes/hora)")
    print(f"{'ρ':>5}{'λ (cl/h)':>10}{'W teoría':>11}{'W sim':>9}{'Wq teoría':>11}{'Wq sim':>9}"
          f"{'Lq teoría':>11}{'Lq sim':>9}")
    for rho in RHO_BARRIDO:
        lam = rho * mu
        teo = teoria(lam, mu)
        reps = replicar(lam, mu, n_replicas, DURACION_MIN, CALENTAMIENTO_MIN, semilla)
        sim = {k: np.mean([r[k] for r in reps]) for k in ("W", "Wq", "Lq")}
        print(f"{rho:5.2f}{lam * 60:10.1f}{teo['W']:11.2f}{sim['W']:9.2f}{teo['Wq']:11.2f}"
              f"{sim['Wq']:9.2f}{teo['Lq']:11.2f}{sim['Lq']:9.2f}")
    print("\nCuando ρ se acerca a 1 la espera crece como 1/(1 − ρ): pasar de ρ = 0.8 a 0.9")
    print("duplica la espera, aunque la demanda solo aumentó 12.5 %. Además la variabilidad")
    print("entre réplicas se dispara, así que con ρ alto se necesitan corridas más largas.")


def main():
    parser = argparse.ArgumentParser(description="Simulación de una fila M/M/1 con SimPy")
    parser.add_argument("--escenario", choices=list(ESCENARIOS), default="normal")
    parser.add_argument("--lam", type=float, default=None, help="tasa de llegadas (clientes/min)")
    parser.add_argument("--mu", type=float, default=None, help="tasa de servicio (clientes/min)")
    parser.add_argument("--replicas", type=int, default=30)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--eventos", type=int, default=20, help="eventos a mostrar en la bitácora")
    parser.add_argument("--barrido", action="store_true", help="comparar varios valores de ρ")
    args = parser.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    escenario = ESCENARIOS[args.escenario]
    lam = args.lam if args.lam is not None else escenario["lam"]
    mu = args.mu if args.mu is not None else escenario["mu"]
    descripcion = escenario["descripcion"] if args.lam is None and args.mu is None else "Tasas propias"

    if args.barrido:
        barrido(mu, args.replicas, args.semilla)
        return

    if lam >= mu:
        parser.error(f"ρ = λ/μ = {lam / mu:.3f} ≥ 1: la fila crece sin límite y no hay estado estable")

    teo = teoria(lam, mu)
    titulo("Fila M/M/1: cajero automático del campus")
    print(f"Escenario: {descripcion}")
    print(f"λ = {lam:.4f} clientes/min ({lam * 60:.1f}/hora)   "
          f"→ un cliente cada {1 / lam:.2f} min en promedio")
    print(f"μ = {mu:.4f} clientes/min ({mu * 60:.1f}/hora)   "
          f"→ {1 / mu:.2f} min de servicio en promedio")
    print(f"ρ = λ/μ = {teo['rho']:.3f} < 1  → la fila es estable")
    print(f"Horizonte: {DURACION_MIN} min ({DURACION_MIN / 1440:.0f} días), "
          f"calentamiento: {CALENTAMIENTO_MIN} min, réplicas: {args.replicas}")

    fila = FilaMM1(lam, mu, args.semilla).correr(DURACION_MIN)
    bitacora(fila, args.eventos)
    revisar_kendall(fila, lam, mu)

    replicas = replicar(lam, mu, args.replicas, DURACION_MIN, CALENTAMIENTO_MIN, args.semilla)
    comparar(lam, mu, replicas)


if __name__ == "__main__":
    main()
