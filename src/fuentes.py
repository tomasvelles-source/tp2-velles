""" Abstracción e implementaciones concretas para lectura de fuentes de datos (CSV y JSON)."""

from abc import ABC, abstractmethod
import csv
import json
from pathlib import Path
from typing import Dict, List


class FuenteDatos(ABC):
    """Contrato común para las fuentes de datos tabulares de la aplicación."""

    @abstractmethod
    def cargar(self, ruta: str | Path) -> List[Dict[str, str]]:
        """Lee los registros desde la ruta indicada y devuelve una lista de diccionarios."""
        raise NotImplementedError


class FuenteCSV(FuenteDatos):
    """Lectura de datos tabulares desde archivos CSV con codificación UTF-8."""

    def cargar(self, ruta: str | Path) -> List[Dict[str, str]]:
        ruta_archivo = Path(ruta)
        if not ruta_archivo.exists():
            raise FileNotFoundError(f"No se encontró el archivo CSV en la ruta: {ruta_archivo}")
        if not ruta_archivo.is_file():
            raise ValueError(f"La ruta especificada no es un archivo válido: {ruta_archivo}")

        with ruta_archivo.open(mode="r", encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            if lector.fieldnames is None:
                raise ValueError(f"El archivo CSV está vacío o no posee encabezados: {ruta_archivo}")
            filas: List[Dict[str, str]] = []
            for fila in lector:
                fila_limpia = {
                    str(clave): ("" if valor is None else str(valor))
                    for clave, valor in fila.items()
                    if clave is not None
                }
                filas.append(fila_limpia)
        return filas


class FuenteJSON(FuenteDatos):
    """Lectura de datos tabulares desde archivos JSON (lista de objetos o clave 'viajes'/'datos')."""

    def cargar(self, ruta: str | Path) -> List[Dict[str, str]]:
        ruta_archivo = Path(ruta)
        if not ruta_archivo.exists():
            raise FileNotFoundError(f"No se encontró el archivo JSON en la ruta: {ruta_archivo}")
        if not ruta_archivo.is_file():
            raise ValueError(f"La ruta especificada no es un archivo válido: {ruta_archivo}")

        with ruta_archivo.open(mode="r", encoding="utf-8") as archivo:
            try:
                contenido = json.load(archivo)
            except json.JSONDecodeError as exc:
                raise ValueError(f"El archivo JSON tiene un formato inválido ({ruta_archivo}): {exc}") from exc

        if isinstance(contenido, dict):
            if "viajes" in contenido and isinstance(contenido["viajes"], list):
                registros = contenido["viajes"]
            elif "datos" in contenido and isinstance(contenido["datos"], list):
                registros = contenido["datos"]
            else:
                raise ValueError(
                    "El objeto JSON debe ser una lista de registros o contener la clave 'viajes' o 'datos'."
                )
        elif isinstance(contenido, list):
            registros = contenido
        else:
            raise ValueError("La estructura raíz del archivo JSON debe ser una lista de objetos.")

        filas: List[Dict[str, str]] = []
        for indice, item in enumerate(registros, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"El elemento #{indice} del JSON no es un objeto clave-valor.")
            fila_limpia = {
                str(clave): ("" if valor is None else str(valor))
                for clave, valor in item.items()
            }
            filas.append(fila_limpia)
        return filas


def obtener_fuente(ruta: str | Path) -> FuenteDatos:
    """Devuelve la implementación concreta de FuenteDatos según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ValueError(
        f"Formato de archivo no soportado ('{extension}'). Utilice un archivo '.csv' o '.json'."
    )
