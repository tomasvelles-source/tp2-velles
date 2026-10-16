# Documentación de los Datos (`data/`)

## 1. Fuente, licencia y procedencia
- **Fuente de referencia:** Portal de Datos Abiertos del Gobierno de la Ciudad Autónoma de Buenos Aires ([BA Data — Bicicletas Públicas / Recorridos Ecobici](https://data.buenosaires.gob.ar/dataset/bicicletas-publicas)).
- **Organismo responsable:** Secretaría de Transporte y Obras Públicas — [Gobierno de la Ciudad Autónoma de Buenos Aires](https://buenosaires.gob.ar/gcaba_historico/jefedegobierno/secretariageneral/historias-con-datos).
- **Licencia:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.es).
- **Fecha de consulta:** 15 de octubre de 2026.
- **Procedimiento de construcción de la muestra:** Se elaboró un conjunto reproducible de **65 observaciones** en dos formatos equivalentes (`viajes_ecobici.csv` y `viajes_ecobici.json`) respetando las denominaciones reales de estaciones de la red Ecobici CABA (`001 - Retiro`, `005 - Plaza Italia`, `008 - Congreso`, `014 - Pacífico`, `022 - Facultad de Medicina`, `030 - Aduana`, `045 - Tribunales`, `052 - Parque Patricios`, `061 - Constitución`, `073 - Obelisco`).

## 2. Unidad de análisis y variables
Cada registro representa **un viaje registrado en el sistema de bicicletas públicas**.

| Campo | Tipo | Unidad / Formato | Descripción |
| :--- | :--- | :--- | :--- |
| `id_viaje` | `str` | Patrón `ECO-XXXX` | Identificador único del viaje. |
| `fecha_inicio` | `str` | `YYYY-MM-DD HH:MM:SS` | Marca temporal de retiro de la bicicleta en la estación de origen. |
| `fecha_fin` | `str` | `YYYY-MM-DD HH:MM:SS` | Marca temporal de devolución de la bicicleta en la estación de destino. |
| `estacion_origen` | `str` | Código y nombre | Estación donde comenzó el viaje. |
| `estacion_destino` | `str` | Código y nombre | Estación donde finalizó el viaje. |
| `duracion_min` | `int` | Minutos | Duración aproximada en minutos registrada en origen. |

## 3. Composición de la muestra (65 registros)
- **55 registros válidos (`ECO-1001` a `ECO-1055`):**
  - 41 viajes entre el `2026-10-01` y el `2026-10-03`.
  - 14 viajes entre el `2026-10-04` y el `2026-10-05`.
- **10 registros inválidos de prueba (incluidos intencionalmente para auditar la limpieza):**
  1. `ECO-1001` (segundo registro): identificador duplicado.
  2. `VIAJE-99`: identificador que no cumple el patrón `^ECO-\d{4,}$`.
  3. `ECO-9001`: `fecha_inicio` con formato `01/10/2026 11:30:00` (no ISO).
  4. `ECO-9002`: `fecha_inicio` con día inexistente en el calendario (`2026-09-31`).
  5. `ECO-9003`: `fecha_inicio` con día bisiesto inexistente (`2026-02-29`, dado que 2026 no es bisiesto).
  6. `ECO-9004`: tiempos incompatibles (`fecha_fin` anterior a `fecha_inicio`).
  7. `ECO-9005`: `estacion_origen` vacía.
  8. `ECO-9006`: `estacion_destino` compuesta solo por espacios en blanco.
  9. `ECO-9007`: `fecha_fin` vacía.
  10. Registro sin `id_viaje`.

## 4. Limitaciones y consideraciones
- La muestra cubre un subconjunto de 10 estaciones representativas para facilitar la verificación determinista de conteos y balances.
- Los registros no incluyen intervenciones de mantenimiento ni reubicación mecánica con camiones, por lo que el balance neto mide exclusivamente la demanda de viajes de usuarios.
