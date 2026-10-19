"""Modelo de dominio para el balance operativo de estaciones de Ecobici."""

from typing import Dict


class BalanceEstacion:
    """Representa el conteo de movimientos (salidas y llegadas) y el balance neto de una estación.

    Nota de dominio: este balance refleja exclusivamente la diferencia entre llegadas y salidas
    de viajes válidos en el período analizado; no representa el stock físico disponible porque
    no incluye inventario inicial ni reposiciones operativas.
    """

    def __init__(self, estacion: str) -> None:
        nombre_limpio = estacion.strip() if isinstance(estacion, str) else ""
        if not nombre_limpio:
            raise ValueError("El nombre de la estación no puede estar vacío.")
        self.estacion: str = nombre_limpio
        self.salidas: int = 0
        self.llegadas: int = 0

    def registrar_salida(self, cantidad: int = 1) -> None:
        """Incrementa el contador de salidas de la estación."""
        if cantidad <= 0:
            raise ValueError("La cantidad de salidas a registrar debe ser un entero positivo.")
        self.salidas += int(cantidad)

    def registrar_llegada(self, cantidad: int = 1) -> None:
        """Incrementa el contador de llegadas de la estación."""
        if cantidad <= 0:
            raise ValueError("La cantidad de llegadas a registrar debe ser un entero positivo.")
        self.llegadas += int(cantidad)

    def obtener_balance(self) -> int:
        """Calcula el balance neto de la estación (llegadas menos salidas)."""
        return self.llegadas - self.salidas

    def movimientos_totales(self) -> int:
        """Devuelve la suma de salidas y llegadas registradas en la estación."""
        return self.salidas + self.llegadas

    def a_diccionario(self) -> Dict[str, str | int]:
        """Convierte el estado de la estación en un diccionario listo para exportar."""
        return {
            "estacion": self.estacion,
            "salidas": self.salidas,
            "llegadas": self.llegadas,
            "balance_neto": self.obtener_balance(),
            "movimientos_totales": self.movimientos_totales(),
        }

    def __repr__(self) -> str:
        return (
            f"BalanceEstacion(estacion={self.estacion!r}, "
            f"salidas={self.salidas}, llegadas={self.llegadas}, "
            f"balance_neto={self.obtener_balance()})"
        )
