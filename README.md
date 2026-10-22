# Trabajo Práctico 2 – Programación Orientada a Datos (Individual)
## Diseño, implementación y documentación de una aplicación de datos en Python: Reporte operativo de movimientos de Ecobici

- **Autor:** Tomás Velles Aguirre (`tomasvelles@gmail.com`)
- **Asignatura:** Programación Orientada a Datos – Licenciatura en Ciencia de Datos (UCA, 2026)
- **Modalidad:** Individual (Apéndice A – Opción 7)
- **Entorno:** Python 3.9+ (`csv`, `json`, `re`, `datetime`, `pathlib`, `abc`, `argparse`, `unittest`), Visual Studio Code y GitHub.

## 1. Problema, usuario, solución y alcance

> **Resumen:** Aplicación de línea de comandos que consolida salidas, llegadas y balance neto por estación en una franja horaria para analistas operativos de Ecobici, validando y limpiando los registros antes del cálculo.

- **Problema y necesidad:** Quien supervisa la operación diaria de la red [Ecobici](https://buenosaires.gob.ar/gcaba_historico/jefedegobierno/secretariageneral/historias-con-datos) recibe archivos de viajes en distintos formatos (`.csv` y `.json`) con errores de registro (fechas inexistentes, tiempos de llegada anteriores a la salida, identificadores repetidos o estaciones faltantes) que alteran los conteos si no se depuran de forma reproducible.
- **Usuario destinatario y finalidad:** Analistas operativos y coordinadores de logística del sistema de bicicletas públicas, quienes utilizan el reporte para identificar estaciones receptoras netas (saturación de anclajes) y emisoras netas (faltante de bicicletas) en una ventana temporal.
- **Solución y operaciones disponibles:** El programa importa archivos CSV o JSON sin modificar los archivos originales, inspecciona y valida el esquema, limpia los recorridos descartando registros inválidos, filtra por fecha de inicio dentro del período `[inicio, fin]`, calcula salidas, llegadas y balance neto (`llegadas - salidas`) por estación y exporta tanto el reporte final como la bitácora de rechazos.
- **Alcance y exclusiones:** Esta primera versión selecciona viajes por `fecha_inicio` y contabiliza ambos extremos (origen y destino) de cada viaje válido. El balance mide el **flujo neto de viajes** y **no representa el stock físico disponible en tiempo real**, ya que quedan fuera del alcance el inventario inicial de cada estación, la capacidad de anclajes y las reposiciones con camiones.

## 2. Fuente de datos, justificación de fiabilidad y diagnóstico inicial

> **Resumen:** Muestra estructurada y equivalente en CSV y JSON de 65 observaciones (55 viajes válidos y 10 con fallas controladas) basada en el esquema oficial de [BA Data — Bicicletas Públicas (Ecobici)](https://data.buenosaires.gob.ar/dataset/bicicletas-publicas).

- **Fuente, responsable y acceso:** Portal de Datos Abiertos del [Gobierno de la Ciudad Autónoma de Buenos Aires](https://buenosaires.gob.ar/gcaba_historico/jefedegobierno/secretariageneral/historias-con-datos) (Secretaría de Transporte y Obras Públicas), dataset [Bicicletas Públicas / Recorridos Ecobici](https://data.buenosaires.gob.ar/dataset/bicicletas-publicas), consultado el `2026-10-15` bajo licencia [Creative Commons CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es).
- **Justificación de fiabilidad y pertinencia:** La fuente es fiable y adecuada porque proviene del registro administrativo primario de telemetría de anclajes del sistema público de bicicletas de CABA, con codificación estandarizada de estaciones y marcas temporales de extracción y devolución, lo que permite reconstruir de forma exacta los flujos origen-destino.
- **Unidad de análisis y variables (6 campos):** Cada fila u objeto representa **un viaje individual** (`id_viaje`: texto `^ECO-\d{4,}$`; `fecha_inicio` y `fecha_fin`: fecha/hora ISO `YYYY-MM-DD HH:MM:SS`; `estacion_origen` y `estacion_destino`: texto con código y nombre de estación; `duracion_min`: entero en minutos).
- **Diagnóstico previo a la limpieza (distinción entre ausentes, duplicados y erróneos):** Sobre los **65 registros brutos** (`data/viajes_ecobici.csv` y `.json`), la inspección inicial detecta **10 observaciones inválidas** agrupadas en cuatro tipologías:
  1. **Valores ausentes o en blanco (4 filas):** `id_viaje` vacío (1), `fecha_fin` vacía (1), `estacion_origen` vacía (1) y `estacion_destino` compuesta solo por espacios `"   "` (1).
  2. **Duplicados de clave (1 fila):** repetición del identificador `ECO-1001`.
  3. **Valores erróneos de formato o calendario (4 filas):** `id_viaje` fuera de patrón (`VIAJE-99`), fecha no ISO (`01/10/2026`) y fechas inexistentes en el calendario gregoriano (`2026-09-31` y `2026-02-29`).
  4. **Valores extremos/incompatibles (1 fila):** duración negativa (`-20 min`) por `fecha_fin < fecha_inicio` (`ECO-9004`).
- **Limitaciones y sesgos de los datos:** La muestra acota la red a 10 estaciones representativas para permitir verificaciones deterministas de conteo y registra únicamente viajes de usuarios (sin movimientos de mantenimiento).

## 3. Arquitectura del código, clases y expresiones regulares

> **Resumen:** Diseño modular en 4 componentes desacoplados: lectura polimórfica (`fuentes.py`), modelo de dominio (`modelo.py`), flujo de validación y cálculo (`pipeline.py`) e interfaz CLI (`main.py`).

```text
data/viajes_ecobici.csv ─┐
                         ├─► FuenteDatos.cargar() ──► normalizar_campos() / validar_esquema()
data/viajes_ecobici.json ┘                                      │
                                                                ▼
outputs/viajes_rechazados.csv ◄── [Rechazos] ── validar_recorridos() (Regex + datetime)
                                                                │ [Viajes válidos]
                                                                ▼
                                                seleccionar_periodo() ──► registrar_movimientos() (BalanceEstacion)
                                                                                  │
                                                                                  ▼
outputs/balance_estaciones.csv ◄───────────────────────────── generar_balance() + verificar_resultado()
```

- **Abstracción de fuentes (`src/fuentes.py`):** La clase base abstracta `FuenteDatos` define el contrato `.cargar(ruta) -> list[dict[str, str]]`, implementado por `FuenteCSV` y `FuenteJSON` para entregar una representación tabular común sin alterar los archivos de entrada.
- **Clase de dominio (`src/modelo.py`):** `BalanceEstacion` modela cada estación con sus atributos (`estacion`, `salidas`, `llegadas`) y métodos cohesivos (`registrar_salida()`, `registrar_llegada()`, `obtener_balance()` y `movimientos_totales()`).
- **Expresiones regulares y validación semántica (`src/pipeline.py`):**
  - `PATRON_ID_VIAJE = r"^ECO-\d{4,}$"`: comprueba que el identificador comience con `ECO-` seguido de al menos cuatro dígitos numéricos.
  - `PATRON_FECHA_ISO = r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$"`: valida la estructura sintáctica `YYYY-MM-DD HH:MM(:SS)`. Como una expresión regular no distingue días inexistentes en el calendario (como `2026-02-29` en año no bisiesto o `2026-09-31`), se complementa con `datetime.strptime()` y con la regla `fecha_fin >= fecha_inicio`.

## 4. Reglas de limpieza y trazabilidad (`outputs/viajes_rechazados.csv`)

> **Resumen:** Se aplican 6 reglas secuenciales (`R1` a `R6`) justificadas por el diagnóstico inicial. Los 10 registros inválidos se excluyen del cálculo y se exportan en `outputs/viajes_rechazados.csv` con su fila de origen y motivo explícito.

| Regla | Campo auditado | Condición detectada en la muestra | Acción aplicada | Filas antes | Rechazadas | Válidas |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: |
| **R1** | `id_viaje` | Vacío (fila 65) o patrón inválido `VIAJE-99` (fila 57) | Validar con regex `^ECO-\d{4,}$` y rechazar | 65 | 2 | 63 |
| **R2** | `id_viaje` | Identificador duplicado `ECO-1001` (fila 56) | Conservar primera aparición y rechazar repetición | 63 | 1 | 62 |
| **R3** | Extremos | `estacion_origen` vacía (fila 62) o `estacion_destino` en blanco (fila 63) | Limpiar espacios (`strip()`) y rechazar extremos vacíos | 62 | 2 | 60 |
| **R4** | Fechas | Formato no ISO `01/10/2026` (fila 58), `fecha_fin` vacía (fila 64) o fechas inexistentes `2026-09-31` y `2026-02-29` (filas 59–60) | Validar patrón ISO con regex y calendario real con `datetime.strptime()` | 60 | 4 | 56 |
| **R5** | Tiempos | `fecha_fin < fecha_inicio` en `ECO-9004` (fila 61) | Rechazar recorridos con duración negativa | 56 | 1 | 55 |
| **R6** | Período | Filtro temporal `2026-10-01 00:00:00` a `2026-10-03 23:59:59` | Seleccionar los 41 viajes iniciados en el período (14 viajes del 4–5 de octubre quedan fuera del corte) | 55 | 0 | 41 |

- **Comparación cuantitativa antes vs. después:** Antes de limpiar, el lote bruto (65 filas) incluía 2 estaciones sin nombre que habrían creado una categoría vacía artificial, 1 viaje duplicado que inflaba las salidas de `001 - Retiro` y 1 duración negativa (`-20 min`). Tras la limpieza quedan **55 viajes válidos** (41 en el período consultado), con duración media consistente de **`20.34` minutos** (rango `15` a `25` min) y suma de balances de red exactamente igual a **`0`**.

## 5. Ejemplo de resultado, interpretación y limitaciones

> **Resumen:** En el período `2026-10-01` al `2026-10-03` (41 viajes válidos), la red mantiene suma de balances igual a `0`. `008 - Congreso` (`+2`) y `061 - Constitución` (`+1`) son receptoras netas, mientras que `001 - Retiro`, `005 - Plaza Italia` y `030 - Aduana` (`-1` cada una) son emisoras netas.

| Estación | Salidas | Llegadas | Balance Neto (`llegadas - salidas`) | Total Movimientos | Interpretación operativa |
| :--- | ---: | ---: | ---: | ---: | :--- |
| `008 - Congreso` | 3 | 5 | **+2** | 8 | Receptora neta (ingresan más bicicletas de las que salen) |
| `061 - Constitución` | 3 | 4 | **+1** | 7 | Receptora neta (ingresan más bicicletas de las que salen) |
| `014 - Pacífico` | 3 | 3 | **0** | 6 | Flujo equilibrado |
| `022 - Facultad de Medicina` | 5 | 5 | **0** | 10 | Flujo equilibrado |
| `045 - Tribunales` | 4 | 4 | **0** | 8 | Flujo equilibrado |
| `052 - Parque Patricios` | 2 | 2 | **0** | 4 | Flujo equilibrado |
| `073 - Obelisco` | 6 | 6 | **0** | 12 | Flujo equilibrado (mayor rotación de la red) |
| `001 - Retiro` | 6 | 5 | **-1** | 11 | Emisora neta (salen más bicicletas de las que ingresan) |
| `005 - Plaza Italia` | 5 | 4 | **-1** | 9 | Emisora neta (salen más bicicletas de las que ingresan) |
| `030 - Aduana` | 4 | 3 | **-1** | 7 | Emisora neta (salen más bicicletas de las que ingresan) |
| **Total Red (10 estaciones)** | **41** | **41** | **0** | **82** | **Propiedad invariante verificada (Suma = 0)** |

- **Interpretación y propiedad invariante:** Todo viaje válido de una estación `A` a una estación `B` suma `1` salida en `A` (`-1`) y `1` llegada en `B` (`+1`). Por consiguiente, la suma de `balance_neto` en el conjunto completo de estaciones es siempre **`0`**, y los viajes rechazados no alteran los conteos.
- **Limitaciones de interpretación:** Un balance negativo indica emisión neta de viajes pero no implica necesariamente falta de bicicletas si la estación contaba con stock inicial alto o recibió reposición vehicular.

## 6. Verificaciones, estructura del repositorio y ejecución

> **Resumen:** Proyecto ejecutable con la biblioteca estándar de Python 3.9+ sin dependencias externas. Incluye 5 pruebas automatizadas con `unittest` que evalúan lotes sintéticos independientes y la muestra real.

- **Estrategia de verificación (`tests/test_pipeline.py`):** Cumple con la separación entre lotes de prueba y muestra de datos:
  1. *Caso normal conocido (lote independiente):* verifica que 1 viaje de Retiro a Obelisco genere balances `-1` y `+1` con suma `0`.
  2. *Entradas inválidas y límites (lote independiente):* comprueba por separado el rechazo de duplicados, fechas inexistentes (`2026-02-29`), tiempos invertidos, extremos en blanco, períodos vacíos e intervalos mal definidos.
  3. *Reconciliación y equivalencia en la muestra:* verifica que `viajes_ecobici.csv` y `viajes_ecobici.json` produzcan exactamente los mismos 55 válidos, 10 rechazos, 41 viajes en el período y suma de balances igual a `0`.

```text
tp2-velles/
|-- README.md                # Documentación integral del proyecto
|-- requirements.txt         # Especificación de entorno (biblioteca estándar Python 3.9+)
|-- .gitignore               # Exclusión de entornos virtuales, cachés y archivos temporales
|-- src/
|   |-- __init__.py
|   |-- main.py              # Punto de entrada CLI y coordinación del flujo reproducible
|   |-- fuentes.py           # Interfaz FuenteDatos (ABC) e implementaciones FuenteCSV y FuenteJSON
|   |-- modelo.py            # Clase de dominio BalanceEstacion
|   `-- pipeline.py          # Validación regex/calendario, limpieza, filtro y exportación
|-- tests/
|   |-- __init__.py
|   `-- test_pipeline.py     # Pruebas unitarias (caso normal, bordes/inválidos, suma cero y CSV=JSON)
|-- data/
|   |-- README.md            # Diccionario de variables, procedencia y detalle de la muestra
|   |-- viajes_ecobici.csv   # Muestra tabular en formato CSV (65 registros)
|   `-- viajes_ecobici.json  # Muestra equivalente en formato JSON (65 registros)
`-- outputs/
    |-- balance_estaciones.csv
    `-- viajes_rechazados.csv
```

### Instalación y comandos exactos de ejecución

No se requiere instalar paquetes externos (`pip`). Ubicado en la carpeta raíz `tp2-velles`:

```powershell
# 1. Ejecutar el flujo completo con la entrada CSV por defecto (período 2026-10-01 a 2026-10-03)
python -m src.main

# 2. Ejecutar el mismo análisis sobre la entrada JSON equivalente
python -m src.main --entrada data/viajes_ecobici.json

# 3. Ejecutar especificando parámetros personalizados de entrada, período y salidas
python -m src.main --entrada data/viajes_ecobici.csv --inicio "2026-10-01 00:00:00" --fin "2026-10-05 23:59:59" --salida outputs/balance_estaciones.csv --rechazos outputs/viajes_rechazados.csv

# 4. Ejecutar la suite completa de pruebas automatizadas (5 tests)
python -m unittest discover -s tests -v
```

*(En sistemas Linux o macOS, reemplazar `python` por `python3`).*