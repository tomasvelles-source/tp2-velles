"""Suite de pruebas unitarias y de integración para el reporte operativo de Ecobici."""

from pathlib import Path
import tempfile
import unittest

from src.fuentes import FuenteCSV, FuenteJSON, obtener_fuente
from src.main import ejecutar_flujo
from src.modelo import BalanceEstacion
from src.pipeline import (
    convertir_fecha,
    generar_balance,
    normalizar_campos,
    registrar_movimientos,
    seleccionar_periodo,
    validar_esquema,
    validar_recorridos,
    verificar_resultado,
)

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_CSV = RAIZ_PROYECTO / "data" / "viajes_ecobici.csv"
RUTA_JSON = RAIZ_PROYECTO / "data" / "viajes_ecobici.json"


class TestReporteEcobici(unittest.TestCase):
    """Verifica casos normales, entradas inválidas/casos límite y propiedades del resultado."""

    def test_caso_normal_viaje_a_b_balance_cero(self) -> None:
        """Un viaje válido de A a B debe sumar 1 salida en A (-1) y 1 llegada en B (+1), con suma total 0."""
        datos = [
            {
                "id_viaje": "ECO-2001",
                "fecha_inicio": "2026-10-01 08:00:00",
                "fecha_fin": "2026-10-01 08:20:00",
                "estacion_origen": "001 - Retiro",
                "estacion_destino": "073 - Obelisco",
            }
        ]
        normalizados = normalizar_campos(datos)
        validar_esquema(normalizados)
        validos, rechazos = validar_recorridos(normalizados)

        self.assertEqual(len(validos), 1)
        self.assertEqual(len(rechazos), 0)

        balances = registrar_movimientos(validos)
        self.assertEqual(balances["001 - Retiro"].salidas, 1)
        self.assertEqual(balances["001 - Retiro"].llegadas, 0)
        self.assertEqual(balances["001 - Retiro"].obtener_balance(), -1)

        self.assertEqual(balances["073 - Obelisco"].salidas, 0)
        self.assertEqual(balances["073 - Obelisco"].llegadas, 1)
        self.assertEqual(balances["073 - Obelisco"].obtener_balance(), 1)

        reporte = generar_balance(balances)
        self.assertTrue(verificar_resultado(reporte, validos))
        suma_balances = sum(int(item["balance_neto"]) for item in reporte)
        self.assertEqual(suma_balances, 0)

    def test_entradas_invalidas_no_alteran_conteos(self) -> None:
        """Fechas inexistentes, tiempos invertidos, extremos vacíos y duplicados deben rechazarse sin alterar conteos."""
        datos = [
            # Válido
            {
                "id_viaje": "ECO-3001",
                "fecha_inicio": "2026-10-02 09:00:00",
                "fecha_fin": "2026-10-02 09:15:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "Estacion B",
            },
            # Duplicado de ECO-3001
            {
                "id_viaje": "ECO-3001",
                "fecha_inicio": "2026-10-02 10:00:00",
                "fecha_fin": "2026-10-02 10:20:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "Estacion C",
            },
            # Fecha calendario inexistente (29 de febrero de 2026)
            {
                "id_viaje": "ECO-3002",
                "fecha_inicio": "2026-02-29 09:00:00",
                "fecha_fin": "2026-02-29 09:20:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "Estacion B",
            },
            # Tiempo fin anterior a inicio
            {
                "id_viaje": "ECO-3003",
                "fecha_inicio": "2026-10-02 12:30:00",
                "fecha_fin": "2026-10-02 12:10:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "Estacion B",
            },
            # Estación destino faltante
            {
                "id_viaje": "ECO-3004",
                "fecha_inicio": "2026-10-02 14:00:00",
                "fecha_fin": "2026-10-02 14:20:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "   ",
            },
            # ID con patrón inválido
            {
                "id_viaje": "ABC-12",
                "fecha_inicio": "2026-10-02 15:00:00",
                "fecha_fin": "2026-10-02 15:20:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "Estacion B",
            },
        ]
        normalizados = normalizar_campos(datos)
        validos, rechazos = validar_recorridos(normalizados)

        self.assertEqual(len(validos), 1)
        self.assertEqual(len(rechazos), 5)

        balances = registrar_movimientos(validos)
        reporte = generar_balance(balances)
        self.assertTrue(verificar_resultado(reporte, validos))
        self.assertEqual(balances["Estacion A"].salidas, 1)
        self.assertEqual(balances["Estacion B"].llegadas, 1)
        self.assertNotIn("Estacion C", balances)

    def test_caso_limite_periodo_sin_viajes_e_intervalo_invalido(self) -> None:
        """Un período sin coincidencias debe devolver lista vacía y un intervalo invertido debe lanzar ValueError."""
        datos = [
            {
                "id_viaje": "ECO-4001",
                "fecha_inicio": "2026-10-01 08:00:00",
                "fecha_fin": "2026-10-01 08:20:00",
                "estacion_origen": "Estacion A",
                "estacion_destino": "Estacion B",
            }
        ]
        validos, _ = validar_recorridos(normalizar_campos(datos))

        sin_viajes = seleccionar_periodo(
            validos,
            inicio="2026-11-01 00:00:00",
            fin="2026-11-02 00:00:00",
        )
        self.assertEqual(sin_viajes, [])
        reporte_vacio = generar_balance(registrar_movimientos(sin_viajes))
        self.assertEqual(reporte_vacio, [])
        self.assertTrue(verificar_resultado(reporte_vacio, sin_viajes))

        with self.assertRaises(ValueError):
            seleccionar_periodo(
                validos,
                inicio="2026-10-05 00:00:00",
                fin="2026-10-01 00:00:00",
            )

    def test_equivalencia_csv_y_json_y_conservacion_de_cantidades(self) -> None:
        """Las muestras equivalentes CSV y JSON deben producir exactamente el mismo reporte y rechazos."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            res_csv = ejecutar_flujo(
                ruta_entrada=RUTA_CSV,
                inicio="2026-10-01 00:00:00",
                fin="2026-10-03 23:59:59",
                ruta_salida=tmp_path / "balance_csv.csv",
                ruta_rechazos=tmp_path / "rechazos_csv.csv",
            )
            res_json = ejecutar_flujo(
                ruta_entrada=RUTA_JSON,
                inicio="2026-10-01 00:00:00",
                fin="2026-10-03 23:59:59",
                ruta_salida=tmp_path / "balance_json.csv",
                ruta_rechazos=tmp_path / "rechazos_json.csv",
            )

            self.assertEqual(res_csv["total_leidos"], 65)
            self.assertEqual(res_csv["total_validos"], 55)
            self.assertEqual(res_csv["total_rechazados"], 10)
            self.assertEqual(res_csv["viajes_en_periodo"], 41)

            self.assertEqual(res_csv["reporte"], res_json["reporte"])
            self.assertEqual(res_csv["rechazos"], res_json["rechazos"])

            suma_balances = sum(int(f["balance_neto"]) for f in res_csv["reporte"])
            self.assertEqual(suma_balances, 0)

    def test_validaciones_de_modelo_y_fuentes(self) -> None:
        """Comprueba que fallas de lectura, formato o parámetros inválidos no se silencien."""
        with self.assertRaises(ValueError):
            BalanceEstacion("   ")

        estacion = BalanceEstacion("001 - Retiro")
        with self.assertRaises(ValueError):
            estacion.registrar_salida(0)
        with self.assertRaises(ValueError):
            estacion.registrar_llegada(-2)

        with self.assertRaises(FileNotFoundError):
            FuenteCSV().cargar(RAIZ_PROYECTO / "data" / "no_existe.csv")

        with self.assertRaises(FileNotFoundError):
            FuenteJSON().cargar(RAIZ_PROYECTO / "data" / "no_existe.json")

        with self.assertRaises(ValueError):
            obtener_fuente("datos.xlsx")

        with self.assertRaises(ValueError):
            convertir_fecha("2026-04-31 10:00:00")


if __name__ == "__main__":
    unittest.main()
