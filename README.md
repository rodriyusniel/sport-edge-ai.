# SPORT EDGE AI v0.8 — EVOLUTION X (primera fase)

Conserva los 6 deportes y las 9 pestañas previas. Incorpora:
- EDGE Risk Shield: alerta sobre parlays largos, duplicación de partidos, probabilidades manuales bajas y exposición sobre 2% del presupuesto.
- EDGE Performance Lab: importa un CSV, valida columnas, calcula ROI, ganancia neta, tasa de acierto y rendimiento por deporte; permite exportar auditoría.
- Control básico de archivos CSV (máximo 2 MB, 20.000 registros).

**Limitaciones:** no hay integración oficial HRB, cuotas en vivo, predicciones entrenadas/calibradas ni conexión a cuentas de apuestas. Las probabilidades siguen siendo manuales y la independencia entre selecciones es un supuesto. El sistema no coloca apuestas. Los datos importados no son persistentes en la nube.

## Actualización desde iPhone
Descomprime el ZIP, reemplaza `app.py` en GitHub rama `main` y espera el redeploy en Streamlit. `requirements.txt` no cambia. Haz una copia del archivo anterior primero.

## Próximas etapas
1. Pruebas automáticas, persistencia y control de acceso.
2. Datos históricos licenciados, trazabilidad y validación temporal.
3. Modelos calibrados y auditoría de resultados fuera de muestra.
4. Conexión de cuotas HRB solamente mediante fuentes autorizadas.
