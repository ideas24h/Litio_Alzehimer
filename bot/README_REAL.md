# 🤖 Bot de difusión — @NeuroLitio_AD

Generador de contenido de divulgación científica sobre **litio y Alzheimer**,
listo para publicar en X (Twitter) y/o Telegram. Sustituye el antiguo
`BOT_INFO.md` (plan editorial) por una implementación real y funcional.

## Qué hace

Lee las bases de datos curadas (`data/estudios.csv`, `data/ensayos_clinicos.csv`)
y genera, según el **calendario semanal** de `BOT_INFO.md`:

| Día | Tipo |
|-----|------|
| Lunes | 🧵 Hilo de investigación |
| Martes | 💡 Dato rápido |
| Miércoles | ❓ Pregunta frecuente |
| Jueves | 💡 Dato rápido |
| Viernes | 🧵 Hilo de investigación |
| Sábado | 🚫 Desmentido/aclaración |
| Domingo | 💡 Dato rápido o silencio |

Cada pieza incluye: fuentes citadas (DOI/journal), nivel de evidencia,
limitaciones, disclaimer obligatorio y hashtags (#LitioYAlzheimer etc.),
con conteo de caracteres para hilos de X.

## Cómo ejecutarlo

```bash
# sin dependencias externas (solo Python 3 stdlib)

# contenido de hoy
python3 bot/briefing.py

# una fecha concreta
python3 bot/briefing.py --date 2026-08-17

# la semana completa (7 días) → bot/out/
python3 bot/briefing.py --week

# ver el calendario y rotación de estudios
python3 bot/briefing.py --list
```

El contenido generado se guarda en `bot/out/YYYY-MM-DD_<tipo>.md`.

## Integración futura (publicación)

1. **Telegram** — hay infraestructura en Hermes (sección `telegram` en
   `~/.hermes/config.yaml`). Enviar el `.md` del día al canal asociado.
2. **X / Twitter** — requiere `X_API_KEY`/`X_API_SECRET`/`X_ACCESS_*` (o API v2
   con OAuth). Añadir credenciales a `.env` (gitignoreado) y un publicador
   `bot/publish.py` que postee los tweets de cada `.md`.

## Reglas éticas (heredadas de BOT_INFO.md)

- ✅ Citar siempre fuente (journal, año, autores).
- ✅ Mencionar limitaciones y distinguir evidencia preclínica de clínica.
- ✅ Disclaimer en cada pieza.
- ❌ NO recomendar tomar litio.
- ❌ NO dar consejo médico; NO sensacionalizar.

## Estado

- ✅ Generador de contenido funcional (`briefing.py`)
- ✅ Contenido de ejemplo para la semana en `bot/out/`
- ⏳ Publicador Telegram/X (pendiente de credenciales)

_Generado por Starmate + agente `turing`, 2026-08-13._
