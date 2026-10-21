"""Funciones de normalización, validación, selección de período, cálculo y exportación de balances."""

import csv
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.modelo import BalanceEstacion

CAMPOS_REQUERIDOS = (
    "id_viaje",
    "fecha_inicio",
    "fecha_fin",
    "estacion_origen",
    "estacion_destino",
)

# Expresión regular para validar formato de fecha ISO: YYYY-MM-DD HH:MM o YYYY-MM-DD HH:MM:SS
PATRON_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$")

# Expresión regular para validar identificadores de viaje de Ecobici (ej. ECO-1001)
PATRON_ID_VIAJE = re.compile(r"^ECO-\d{4,}$")


def convertir_fecha(texto_fecha: str) -> datetime:
    """Valida el patrón textual con regex y comprueba que la fecha exista en el calendario."""
    if not isinstance(texto_fecha, str):
        raise ValueError("La fecha debe ser una cadena de texto.")
    limpio = texto_fecha.strip()
    if not limpio:
        raise ValueError("La fecha está vacía.")
    if not PATRON_FECHA_ISO.match(limpio):
        raise ValueError(
            f"Formato de fecha inválido ('{limpio}'). Se esperaba 'YYYY-MM-DD HH:MM:SS'."
        )

    normalizado = limpio.replace("T", " ")
    formato = "%Y-%m-%d %H:%M:%S" if len(normalizado) == 19 else "%Y-%m-%d %H:%M"
    try:
        return datetime.strptime(normalizado, formato)
    except ValueError as exc:
        raise ValueError(
            f"Fecha inexistente en el calendario ('{limpio}'): {exc}"
        ) from exc


def normalizar_campos(datos: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Normaliza claves (minúsculas sin espacios extremos) y limpia valores textuales."""
    normalizados: List[Dict[str, str]] = []
    for fila in datos:
        if not isinstance(fila, dict):
            raise ValueError("Cada registro de entrada debe ser un diccionario.")
        nuevo: Dict[str, str] = {}
        for clave, valor in fila.items():
            clave_limpia = str(clave).strip().lower()
            texto_valor = "" if valor is None else str(valor).strip()
            nuevo[clave_limpia] = texto_valor
        normalizados.append(nuevo)
    return normalizados


def validar_esquema(datos: List[Dict[str, str]]) -> None:
    """Verifica que la colección no esté vacía y contenga todos los campos requeridos."""
    if not isinstance(datos, list) or len(datos) == 0:
        raise ValueError("El conjunto de datos de entrada está vacío.")
    columnas_presentes = set(datos[0].keys())
    faltantes = [campo for campo in CAMPOS_REQUERIDOS if campo not in columnas_presentes]
    if faltantes:
        raise ValueError(
            f"Faltan columnas obligatorias en el esquema de entrada: {', '.join(faltantes)}"
        )


def validar_recorridos(
    datos: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Valida cada recorrido y separa viajes válidos de registros rechazados con su motivo.

    Reglas aplicadas:
    1. 'id_viaje' no vacío, formato '^ECO-\d{4,}$' y sin duplicados previos.
    2. 'estacion_origen' y 'estacion_destino' no vacías.
    3. 'fecha_inicio' y 'fecha_fin' con patrón ISO válido y fecha real en el calendario.
    4. Consistencia temporal: 'fecha_fin' debe ser mayor o igual que 'fecha_inicio'.
    """
    viajes_validos: List[Dict[str, Any]] = []
    rechazos: List[Dict[str, Any]] = []
    ids_vistos: set[str] = set()

    for fila_num, registro in enumerate(datos, start=1):
        id_viaje = registro.get("id_viaje", "").strip()
        fecha_inicio_txt = registro.get("fecha_inicio", "").strip()
        fecha_fin_txt = registro.get("fecha_fin", "").strip()
        origen = registro.get("estacion_origen", "").strip()
        destino = registro.get("estacion_destino", "").strip()

        motivo: Optional[str] = None
        inicio_dt: Optional[datetime] = None
        fin_dt: Optional[datetime] = None

        if not id_viaje:
            motivo = "Identificador de viaje faltante"
        elif not PATRON_ID_VIAJE.match(id_viaje):
            motivo = f"Identificador de viaje con formato inválido ({id_viaje})"
        elif id_viaje in ids_vistos:
            motivo = f"Identificador de viaje duplicado ({id_viaje})"
        elif not origen:
            motivo = "Extremo faltante: estacion_origen vacía"
        elif not destino:
            motivo = "Extremo faltante: estacion_destino vacía"
        else:
            try:
                inicio_dt = convertir_fecha(fecha_inicio_txt)
            except ValueError as exc:
                motivo = f"fecha_inicio inválida: {exc}"

            if motivo is None:
                try:
                    fin_dt = convertir_fecha(fecha_fin_txt)
                except ValueError as exc:
                    motivo = f"fecha_fin inválida: {exc}"

            if motivo is None and inicio_dt is not None and fin_dt is not None:
                if fin_dt < inicio_dt:
                    motivo = (
                        f"Tiempos incompatibles: fecha_fin ({fecha_fin_txt}) "
                        f"es anterior a fecha_inicio ({fecha_inicio_txt})"
                    )

        if motivo is not None:
            rechazos.append(
                {
                    "fila_origen": fila_num,
                    "id_viaje": id_viaje,
                    "fecha_inicio": fecha_inicio_txt,
                    "fecha_fin": fecha_fin_txt,
                    "estacion_origen": origen,
                    "estacion_destino": destino,
                    "motivo_rechazo": motivo,
                }
            )
            continue

        assert inicio_dt is not None and fin_dt is not None
        ids_vistos.add(id_viaje)
        duracion_calculada = round((fin_dt - inicio_dt).total_seconds() / 60.0, 2)
        viajes_validos.append(
            {
                "id_viaje": id_viaje,
                "fecha_inicio": inicio_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_fin": fin_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "inicio_dt": inicio_dt,
                "fin_dt": fin_dt,
                "estacion_origen": origen,
                "estacion_destino": destino,
                "duracion_minutos": duracion_calculada,
            }
        )

    return viajes_validos, rechazos


def seleccionar_periodo(
    viajes_validos: List[Dict[str, Any]],
    inicio: Optional[str] = None,
    fin: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filtra los viajes válidos seleccionando aquellos cuyo inicio cae dentro de [inicio, fin]."""
    inicio_dt = convertir_fecha(inicio) if inicio else None
    fin_dt = convertir_fecha(fin) if fin else None

    if inicio_dt and fin_dt and fin_dt < inicio_dt:
        raise ValueError(
            f"El período solicitado es inválido: la fecha de fin ({fin}) "
            f"es anterior a la fecha de inicio ({inicio})."
        )

    seleccionados: List[Dict[str, Any]] = []
    for viaje in viajes_validos:
        marca_inicio = viaje.get("inicio_dt")
        if not isinstance(marca_inicio, datetime):
            marca_inicio = convertir_fecha(str(viaje["fecha_inicio"]))

        if inicio_dt and marca_inicio < inicio_dt:
            continue
        if fin_dt and marca_inicio > fin_dt:
            continue
        seleccionados.append(viaje)

    return seleccionados


def registrar_movimientos(
    viajes_periodo: List[Dict[str, Any]],
) -> Dict[str, BalanceEstacion]:
    """Acumula salidas y llegadas por estación contabilizando ambos extremos de cada viaje."""
    balances: Dict[str, BalanceEstacion] = {}

    for viaje in viajes_periodo:
        origen = str(viaje["estacion_origen"]).strip()
        destino = str(viaje["estacion_destino"]).strip()

        if origen not in balances:
            balances[origen] = BalanceEstacion(origen)
        if destino not in balances:
            balances[destino] = BalanceEstacion(destino)

        balances[origen].registrar_salida()
        balances[destino].registrar_llegada()

    return balances


def generar_balance(
    balances: Dict[str, BalanceEstacion],
    ruta_salida: Optional[str | Path] = None,
) -> List[Dict[str, str | int]]:
    """Calcula llegadas menos salidas por estación, ordena el reporte y opcionalmente lo exporta."""
    reporte = [est.a_diccionario() for est in balances.values()]
    reporte.sort(key=lambda item: (-int(item["balance_neto"]), str(item["estacion"])))

    if ruta_salida is not None:
        guardar_resultado(reporte, ruta_salida)

    return reporte


def verificar_resultado(
    reporte: List[Dict[str, str | int]],
    viajes_periodo: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Verifica las propiedades invariantes del balance operativo de estaciones.

    1. La suma de 'balance_neto' en el conjunto completo de estaciones debe ser exactamente 0.
    2. La suma total de 'salidas' debe coincidir con la suma total de 'llegadas'.
    3. Si se informa la lista de viajes del período, el total de salidas debe igualar len(viajes_periodo).
    """
    suma_balances = sum(int(fila["balance_neto"]) for fila in reporte)
    total_salidas = sum(int(fila["salidas"]) for fila in reporte)
    total_llegadas = sum(int(fila["llegadas"]) for fila in reporte)

    if suma_balances != 0:
        raise ValueError(
            f"Inconsistencia en el resultado: la suma de balances netos es {suma_balances} (se esperaba 0)."
        )
    if total_salidas != total_llegadas:
        raise ValueError(
            f"Inconsistencia en el resultado: salidas totales ({total_salidas}) != llegadas totales ({total_llegadas})."
        )
    if viajes_periodo is not None and total_salidas != len(viajes_periodo):
        raise ValueError(
            f"Inconsistencia de conteo: salidas acumuladas ({total_salidas}) != viajes del período ({len(viajes_periodo)})."
        )
    return True


def guardar_resultado(
    reporte: List[Dict[str, str | int]],
    ruta_salida: str | Path,
) -> Path:
    """Exporta la tabla de balance por estación a un archivo CSV."""
    destino = Path(ruta_salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    columnas = ["estacion", "salidas", "llegadas", "balance_neto", "movimientos_totales"]
    with destino.open(mode="w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for fila in reporte:
            escritor.writerow(fila)
    return destino


def guardar_rechazos(
    rechazos: List[Dict[str, Any]],
    ruta_rechazos: str | Path,
) -> Path:
    """Exporta los registros rechazados junto con su motivo a un archivo CSV."""
    destino = Path(ruta_rechazos)
    destino.parent.mkdir(parents=True, exist_ok=True)
    columnas = [
        "fila_origen",
        "id_viaje",
        "fecha_inicio",
        "fecha_fin",
        "estacion_origen",
        "estacion_destino",
        "motivo_rechazo",
    ]
    with destino.open(mode="w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for fila in rechazos:
            escritor.writerow(fila)
    return destino
