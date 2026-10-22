# Simulación de una Fila M/M/1 con Eventos Discretos
Una línea de espera aparece cuando los clientes llegan a pedir un servicio más rápido de lo que, en algunos momentos, se les puede atender. En este proyecto se modela la fila del **cajero automático del campus**, que tiene una sola máquina: las personas llegan al azar, esperan su turno si el cajero está ocupado, hacen su operación y se van. El número de clientes en el sistema, N(t), cambia solo cuando alguien llega o sale, por lo que es un **proceso estocástico de nacimiento y muerte** que se simula con **eventos discretos** usando [SimPy](https://simpy.readthedocs.io/).

## El cajero como fila M/M/1 (notación de Kendall)

La notación de Kendall describe una fila como **A / S / c / K / N / D**. El cajero cumple con **M/M/1/∞/∞/FIFO**, que se abrevia **M/M/1**:

| Símbolo | Significado | En el cajero |
|:---:|---|---|
| **A = M** | Llegadas de Poisson (tiempos entre llegadas exponenciales, sin memoria) | Las personas llegan de forma independiente; nadie se pone de acuerdo para ir al cajero. λ = 30 clientes/hora |
| **S = M** | Tiempos de servicio exponenciales | La mayoría de las operaciones son rápidas (retiro) y unas pocas tardan mucho (depósitos, consultas). μ = 40 clientes/hora (1.5 min en promedio) |
| **c = 1** | Un solo servidor | Hay una sola máquina |
| **K = ∞** | Capacidad de la fila ilimitada | La fila puede crecer en el pasillo sin que se rechace a nadie |
| **N = ∞** | Población ilimitada | Los clientes potenciales (toda la comunidad del campus) son muchos más que los que están en la fila |
| **D = FIFO** | Se atiende en orden de llegada | El primero en llegar es el primero en usar el cajero |

Además se cumple la condición de estabilidad **ρ = λ/μ = 30/40 = 0.75 < 1**: el cajero puede atender, en promedio, más gente de la que llega. Si ρ ≥ 1 la fila crece sin límite y el programa lo rechaza.

El programa no solo supone estas propiedades: también las **comprueba con los datos simulados** (coeficiente de variación ≈ 1 de los tiempos exponenciales, media ≈ varianza en el número de llegadas por intervalo como en una Poisson, y la falta de memoria `P(T > s + t | T > s) = P(T > t)`).

**Características clave:**

* **Eventos discretos:** Cada cliente es un proceso de SimPy. Hay tres eventos: *llegada*, *inicio de servicio* y *salida*. El reloj de la simulación salta directamente de un evento al siguiente, porque entre eventos el estado del sistema no cambia.
* **Servidor:** El cajero es un `simpy.Resource` con capacidad 1. Si está ocupado, el cliente queda formado (FIFO) hasta que se libera.
* **Generador de números aleatorios:** Los tiempos entre llegadas y de servicio se generan con `numpy.random.default_rng(semilla).exponential(1/tasa)`, con semilla fija para que los resultados sean reproducibles.
* **Estado estable:** Cada corrida simula una semana continua (10 080 min) y descarta los primeros 500 min de calentamiento, para no medir el arranque con la fila vacía.
* **Promedios ponderados en el tiempo:** L, Lq, ρ y Pn se calculan ponderando cada estado por el tiempo que duró; W y Wq se promedian sobre los clientes.
* **Réplicas e intervalos de confianza:** Se corren 30 réplicas independientes y se reporta la media con un intervalo de confianza del 95 %, que se compara contra la fórmula teórica.
* **Escenarios:** `normal` (λ = 30/h, ρ = 0.75), `pico` (λ = 36/h, ρ = 0.9) y `tranquilo` (λ = 20/h, ρ = 0.5). El modo `--barrido` recorre varios valores de ρ.

## Ecuaciones de la M/M/1

```
ρ  = λ / μ                       utilización del cajero
P0 = 1 − ρ                       probabilidad de que el cajero esté libre
Pn = (1 − ρ) ρⁿ                  probabilidad de que haya n clientes en el sistema

L  = ρ / (1 − ρ)                 clientes promedio en el sistema
Lq = ρ² / (1 − ρ)                clientes promedio en la fila
W  = 1 / (μ − λ)                 tiempo promedio en el sistema
Wq = ρ / (μ − λ)                 tiempo promedio en la fila

Ley de Little:   L = λ W        Lq = λ Wq
```

## Resultados (escenario normal, semilla 42)

Inicio de la bitácora de eventos discretos:

```
 reloj (min)  cliente  evento           en sistema  en fila
      21.287        6  llegada                   1        0
      21.287        6  inicio servicio           1        0
      23.465        7  llegada                   2        1
      23.884        6  salida                    1        0
      23.884        7  inicio servicio           1        0
```

Simulación (30 réplicas de una semana, ~4 800 clientes cada una) contra la teoría. En todas las medidas el valor teórico cae dentro del intervalo de confianza:

| Medida | Teoría | Simulación | IC 95 % |
|---|:---:|:---:|:---:|
| Utilización ρ | 0.7500 | 0.7515 | [0.7463, 0.7567] |
| P0 (cajero libre) | 0.2500 | 0.2485 | [0.2433, 0.2537] |
| L (clientes en el sistema) | 3.0000 | 3.0141 | [2.8958, 3.1323] |
| Lq (clientes en la fila) | 2.2500 | 2.2626 | [2.1473, 2.3778] |
| W (min en el sistema) | 6.0000 | 6.0074 | [5.7869, 6.2279] |
| Wq (min en la fila) | 4.5000 | 4.5080 | [4.2895, 4.7265] |
| P(tener que esperar) | 0.7500 | 0.7515 | [0.7453, 0.7578] |

Aunque en promedio hay solo 2.25 personas formadas, en alguna réplica llegó a haber **34 personas** en el sistema: el promedio esconde momentos de mucha congestión.

Efecto de la utilización (`python main.py --barrido`, μ = 40 clientes/hora):

| ρ | λ (cl/h) | W teoría (min) | W simulado (min) | Lq teoría | Lq simulado |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.10 | 4  | 1.67  | 1.67  | 0.01  | 0.01  |
| 0.50 | 20 | 3.00  | 3.03  | 0.50  | 0.51  |
| 0.70 | 28 | 5.00  | 5.04  | 1.63  | 1.66  |
| 0.80 | 32 | 7.50  | 7.45  | 3.20  | 3.19  |
| 0.90 | 36 | 15.00 | 15.90 | 8.10  | 8.69  |
| 0.95 | 38 | 30.00 | 28.44 | 18.05 | 17.10 |

Pasar de ρ = 0.8 a ρ = 0.9 (solo 12.5 % más clientes) **duplica** el tiempo de espera, porque W crece como 1/(1 − ρ). Con ρ alto la simulación también se aleja más de la teoría y varía mucho entre réplicas: el sistema tarda más en llegar al estado estable.

## Reflexión

**¿Qué ventajas ofrece usar eventos discretos?**

* **Eficiencia:** El reloj salta de un evento al siguiente en lugar de avanzar en pasos fijos de tiempo. No se gasta cómputo en los intervalos en los que no pasa nada, y no hay error por elegir un Δt demasiado grande (dos eventos nunca se "juntan" en el mismo paso). Una semana de operación con ~4 800 clientes se simula en una fracción de segundo.
* **Se modela el proceso como se describe en la realidad:** Cada cliente es un proceso (`llega → espera → se atiende → se va`) y el cajero es un recurso. El código se lee igual que la descripción del sistema, lo que facilita validarlo y cambiarlo.
* **No depende de los supuestos de la teoría:** Las fórmulas cerradas solo existen para modelos como M/M/1. Con eventos discretos se puede cambiar la distribución del servicio (por ejemplo, tiempos casi constantes), agregar un segundo cajero, limitar la fila, poner llegadas que cambian según la hora o clientes que se van si la fila es larga, sin tener que resolver ecuaciones nuevas.
* **Da información completa, no solo promedios:** Se obtiene la bitácora de cada evento, la trayectoria de la fila en el tiempo, el máximo observado y la distribución completa de tiempos de espera.
* **Permite validar:** Como la M/M/1 tiene solución analítica, la simulación se puede comparar contra la teoría (aquí la teoría cae dentro de todos los intervalos de confianza). Una vez validada, el mismo simulador se puede usar en variantes que no tienen fórmula.

**¿Qué información relevante podemos extraer de un proceso modelado como una fila?**

* **Utilización del servidor (ρ):** Qué fracción del tiempo el cajero está ocupado y cuánto está ocioso (P0).
* **Congestión:** Cuántas personas hay en promedio formadas (Lq) y en el sistema (L), y la probabilidad de encontrar n personas (Pn), útil para dimensionar el espacio de la fila.
* **Tiempos de espera:** Cuánto espera un cliente en la fila (Wq) y en total (W), y la probabilidad de tener que esperar. Son las medidas que percibe el usuario y con las que se definen niveles de servicio (por ejemplo, "que nadie espere más de 5 minutos").
* **Estabilidad y capacidad:** Si ρ < 1 el sistema es estable; si no, la fila crece sin límite. También muestra que el desempeño **no es lineal**: cerca de ρ = 1 un aumento pequeño en la demanda provoca un aumento enorme en la espera.
* **Toma de decisiones:** Con estas medidas se puede justificar si conviene instalar un segundo cajero, en qué horarios hace falta (el escenario `pico` duplica la espera del `normal`) o cuánto habría que acelerar el servicio para lograr una espera objetivo. Las mismas ideas aplican a servidores web, paquetes en una red, pacientes en una clínica o piezas en una línea de producción.

## Distribución del Proyecto
simulacion_mm1/
├── src/
│   ├── data.py       # Escenarios del cajero (λ, μ), horizonte de simulación, calentamiento y valores de ρ del barrido.
│   ├── model.py      # Clase FilaMM1 (procesos de SimPy, bitácora de eventos y estadísticas), fórmulas teóricas M/M/1 y réplicas.
│   └── main.py       # Script principal: bitácora, revisión de supuestos de Kendall, comparación simulación vs teoría y barrido de ρ.
├── .gitignore        # Excluye la caché de Python.
└── requirements.txt  # Dependencias del entorno virtual (numpy, simpy).

## Ejecución

```bash
pip install -r requirements.txt
cd src
python main.py                              # escenario normal (ρ = 0.75), 30 réplicas de una semana
python main.py --escenario pico             # hora pico (ρ = 0.9); también: tranquilo
python main.py --lam 0.5 --mu 0.8           # tasas propias en clientes/min
python main.py --replicas 50 --semilla 7    # más réplicas u otra semilla
python main.py --eventos 40                 # mostrar más eventos de la bitácora
python main.py --barrido                    # W, Wq y Lq simulados vs teóricos para varios ρ
```
