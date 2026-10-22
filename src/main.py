"""Punto de entrada de línea de comandos para el Reporte Operativo de Movimientos de Ecobici."""

import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from src.fuentes import obtener_fuente
from src.pipeline import (
    generar_balance,
    guardar_rechazos,
    guardar_resultado,
    normalizar_campos,
    registrar_movimientos,
    seleccionar_periodo,
    validar_esquema,
    validar_recorridos,
    verificar_resultado,
)


def ejecutar_flujo(
    ruta_entrada: str | Path,
    inicio: Optional[str] = None,
    fin: Optional[str] = None,
    ruta_salida: Optional[str | Path] = None,
    ruta_rechazos: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Ejecuta de punta a punta el flujo reproducible de procesamiento de viajes de Ecobici."""
    fuente = obtener_fuente(ruta_entrada)
    datos_crudos = fuente.cargar(ruta_entrada)
    datos_normalizados = normalizar_campos(datos_crudos)
    validar_esquema(datos_normalizados)

    viajes_validos, rechazos = validar_recorridos(datos_normalizados)
    viajes_periodo = seleccionar_periodo(viajes_validos, inicio=inicio, fin=fin)
    balances = registrar_movimientos(viajes_periodo)
    reporte = generar_balance(balances)
    verificar_resultado(reporte, viajes_periodo)

    if ruta_salida is not None:
        guardar_resultado(reporte, ruta_salida)
    if ruta_rechazos is not None:
        guardar_rechazos(rechazos, ruta_rechazos)

    return {
        "total_leidos": len(datos_normalizados),
        "total_validos": len(viajes_validos),
        "total_rechazados": len(rechazos),
        "viajes_en_periodo": len(viajes_periodo),
        "reporte": reporte,
        "rechazos": rechazos,
    }


def formatear_tabla_consola(resumen: Dict[str, Any], inicio: Optional[str], fin: Optional[str]) -> str:
    """Construye una representación tabular clara del reporte para mostrar por consola."""
    lineas: List[str] = []
    lineas.append("=" * 78)
    lineas.append("REPORTE OPERATIVO DE MOVIMIENTOS DE ECOBICI")
    lineas.append("=" * 78)
    rango_txt = f"{inicio or 'Inicio de datos'} -> {fin or 'Fin de datos'}"
    lineas.append(f"Período consultado      : {rango_txt}")
    lineas.append(f"Registros leídos        : {resumen['total_leidos']}")
    lineas.append(f"Viajes válidos totales  : {resumen['total_validos']}")
    lineas.append(f"Registros rechazados    : {resumen['total_rechazados']}")
    lineas.append(f"Viajes en el período    : {resumen['viajes_en_periodo']}")
    lineas.append("-" * 78)

    reporte: List[Dict[str, Any]] = resumen["reporte"]
    if not reporte:
        lineas.append("No se registraron viajes válidos para el período seleccionado.")
    else:
        encabezado = f"{'ESTACIÓN':<32} | {'SALIDAS':>8} | {'LLEGADAS':>8} | {'BALANCE':>8} | {'TOTAL':>8}"
        lineas.append(encabezado)
        lineas.append("-" * 78)
        for fila in reporte:
            balance_num = int(fila["balance_neto"])
            balance_str = f"+{balance_num}" if balance_num > 0 else str(balance_num)
            lineas.append(
                f"{str(fila['estacion']):<32} | "
                f"{int(fila['salidas']):>8} | "
                f"{int(fila['llegadas']):>8} | "
                f"{balance_str:>8} | "
                f"{int(fila['movimientos_totales']):>8}"
            )
        lineas.append("-" * 78)
        suma_salidas = sum(int(f["salidas"]) for f in reporte)
        suma_llegadas = sum(int(f["llegadas"]) for f in reporte)
        suma_balance = sum(int(f["balance_neto"]) for f in reporte)
        suma_movs = sum(int(f["movimientos_totales"]) for f in reporte)
        lineas.append(
            f"{'TOTAL RED':<32} | {suma_salidas:>8} | {suma_llegadas:>8} | {suma_balance:>8} | {suma_movs:>8}"
        )
    lineas.append("=" * 78)
    return chr(10).join(lineas)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera el reporte operativo de movimientos y balance neto por estación de Ecobici."
    )
    parser.add_argument(
        "--entrada",
        default="data/viajes_ecobici.csv",
        help="Ruta al archivo de entrada (.csv o .json). Por defecto: data/viajes_ecobici.csv",
    )
    parser.add_argument(
        "--inicio",
        default="2026-10-01 00:00:00",
        help="Fecha y hora de inicio del período (YYYY-MM-DD HH:MM:SS).",
    )
    parser.add_argument(
        "--fin",
        default="2026-10-03 23:59:59",
        help="Fecha y hora de fin del período (YYYY-MM-DD HH:MM:SS).",
    )
    parser.add_argument(
        "--salida",
        default="outputs/balance_estaciones.csv",
        help="Ruta del archivo CSV de salida con el balance por estación.",
    )
    parser.add_argument(
        "--rechazos",
        default="outputs/viajes_rechazados.csv",
        help="Ruta del archivo CSV donde se registrarán las filas rechazadas y sus motivos.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        resumen = ejecutar_flujo(
            ruta_entrada=args.entrada,
            inicio=args.inicio,
            fin=args.fin,
            ruta_salida=args.salida,
            ruta_rechazos=args.rechazos,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error durante la ejecución: {exc}", file=sys.stderr)
        return 1

    print(formatear_tabla_consola(resumen, args.inicio, args.fin))
    print(f"Reporte guardado en  : {args.salida}")
    print(f"Rechazos guardados en: {args.rechazos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
