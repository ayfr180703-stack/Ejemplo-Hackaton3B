# Despliegue del tablero

Plan previsto: publicar el tablero en Cloudflare.

**Ojo:** el tablero actual usa Streamlit, que necesita un servidor de Python. Cloudflare Pages solo publica páginas estáticas. Opciones:

1. **Local (respaldo siempre disponible):** `streamlit run dashboard/app.py` en la computadora de la presentación.
2. **Página estática en Cloudflare Pages:** exportar las tablas finales a archivos y hacer una página con gráficas (más trabajo).
3. **Streamlit Community Cloud u otro servicio con servidor:** más rápido, pero no es Cloudflare.

Pendiente de decidir por el equipo: cuál opción, quién tiene la cuenta y quién despliega.
