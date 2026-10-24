# SPORT EDGE AI v0.3 — iPhone + Soccer

Prototipo Streamlit en español con MLB, NHL, NBA, NFL, NCAAF y Soccer. En fútbol permite seleccionar Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League y MLS.

## Publicar desde un iPhone (sin computadora)

1. En Safari, entra en **github.com**, crea una cuenta o inicia sesión y crea un repositorio **privado** llamado `sport-edge-ai`.
2. Dentro del repositorio, usa **Add file → Create new file** y crea `app.py`. Copia allí el contenido del `app.py` de este paquete. Haz **Commit changes**.
3. Repite para `requirements.txt`, copiando el archivo de este paquete.
4. Abre **share.streamlit.io** en Safari e inicia sesión con GitHub. Elige **Create app**, selecciona el repositorio, rama `main` y archivo `app.py`. Si la plataforma no admite el repositorio privado en el plan disponible, tendrás que ajustar la visibilidad o elegir otro hosting; no publiques claves ni datos privados.
5. Espera a que termine el despliegue y abre la dirección web que te proporcione Streamlit.
6. En Safari pulsa **Compartir → Añadir a pantalla de inicio** para acceder como una app.

Consejo: en Safari activa **Solicitar sitio web de escritorio** si algún botón de GitHub no aparece en la vista móvil. Como alternativa, GitHub permite cargar archivos desde su interfaz web, pero algunos iPhone requieren descomprimir el ZIP en la app Archivos primero.

## Limitaciones

- Calendarios/resultados: endpoint público no oficial de ESPN, sujeto a cambios, sin garantía de disponibilidad ni cobertura completa.
- No hay cuotas en vivo de Hard Rock Bet, modelos predictivos, bot Telegram ni lectura de capturas todavía.
- Las probabilidades son manuales; la estimación de parlay presupone independencia.
- El registro de apuestas se guarda en un CSV local del servidor y puede perderse al reiniciar en hosting gratuito. Exporta copias CSV; no guardes datos sensibles.
- Esta versión no hace apuestas ni accede a cuentas de casas de apuestas.

## Ejecutar localmente (opcional)

`pip install -r requirements.txt` y `streamlit run app.py`.
