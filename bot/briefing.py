#!/usr/bin/env python3
"""
Generador de contenido para @NeuroLitio_AD.

Produce briefings/threads en markdown desde data/estudios.csv y
data/ensayos_clinicos.csv siguiendo el calendario semanal de BOT_INFO.md.

Uso:
    python3 bot/briefing.py                  # genera el contenido de hoy
    python3 bot/briefing.py --date 2026-08-17  # genera para una fecha concreta
    python3 bot/briefing.py --week           # genera los 7 días de esta semana
    python3 bot/briefing.py --list           # lista el calendario y rotación

Sin dependencias externas. Solo stdlib de Python 3.
"""

import csv
import os
import sys
import hashlib
import argparse
from datetime import date, datetime, timedelta

# ─── Constantes ────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "out")
ESTUDIOS_CSV = os.path.join(DATA_DIR, "estudios.csv")
ENSAYOS_CSV = os.path.join(DATA_DIR, "ensayos_clinicos.csv")

DISCLAIMER = (
    "⚠️ Esto NO es consejo médico. Es divulgación científica basada en "
    "evidencia publicada. Consulte siempre a un profesional de la salud."
)

HASHTAGS_BASE = "#LitioYAlzheimer #Neurociencia"
HASHTAGS_RESEARCH = "#LitioResearch #LitioYAlzheimer #InvestigaciónAlzheimer"
HASHTAGS_FAQ = "#LitioFAQ #LitioYAlzheimer"

# Calendario semanal del BOT_INFO.md
# (weekday: 0=Lunes ... 6=Domingo)
CALENDARIO = {
    0: {"tipo": "hilo_investigacion", "label": "Hilo de investigación", "hashtag": HASHTAGS_RESEARCH},
    1: {"tipo": "dato_rapido", "label": "Dato rápido", "hashtag": HASHTAGS_BASE},
    2: {"tipo": "faq", "label": "Pregunta frecuente", "hashtag": HASHTAGS_FAQ},
    3: {"tipo": "dato_rapido", "label": "Dato rápido", "hashtag": HASHTAGS_BASE},
    4: {"tipo": "hilo_investigacion", "label": "Hilo de investigación", "hashtag": HASHTAGS_RESEARCH},
    5: {"tipo": "desmentido", "label": "Desmentido / aclaración", "hashtag": HASHTAGS_BASE},
    6: {"tipo": "dato_rapido", "label": "Dato rápido", "hashtag": HASHTAGS_BASE},
}

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ─── Carga de datos ────────────────────────────────────────────────────────


def cargar_csv(path):
    """Carga un CSV y devuelve lista de dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cargar_estudios():
    """Estudios relevantes para litio y Alzheimer (filtra omega-3/NAD+ del bot principal)."""
    todos = cargar_csv(ESTUDIOS_CSV)
    # El bot se centra en litio. Filtramos los que no mencionan litio en dosis o tipo.
    litio = []
    for e in todos:
        dosis = (e.get("Lithium_Dose") or "").lower()
        finding = (e.get("Key_Finding") or "").lower()
        if "li " in finding or "litio" in finding or "lithium" in dosis or "li " in dosis or "orotate" in dosis or "carbonate" in dosis or "sulfate" in dosis:
            litio.append(e)
    return litio if litio else todos


def cargar_ensayos():
    return cargar_csv(ENSAYOS_CSV)


# ─── Selección determinista ────────────────────────────────────────────────


def seed_indice(fecha_str, rango):
    """Devuelve un índice determinista [0, rango) basado en la fecha.

    La misma fecha siempre produce el mismo índice, garantizando
    reproducibilidad y rotación natural entre días.
    """
    h = int(hashlib.md5(fecha_str.encode()).hexdigest(), 16)
    return h % rango


def seleccionar_estudio(fecha_str, estudios):
    idx = seed_indice(fecha_str, len(estudios))
    return estudios[idx]


def seleccionar_ensayo(fecha_str, ensayos):
    idx = seed_indice(fecha_str + "ensayo", len(ensayos))
    return ensayos[idx]


# ─── Clasificación de evidencia ────────────────────────────────────────────


def nivel_evidencia(study_type):
    """Traduce el tipo de estudio a una etiqueta de nivel de evidencia."""
    st = (study_type or "").lower()
    if "meta-analysis" in st or "meta-análisis" in st:
        return "📊 Nivel: Meta-análisis (alta calidad de evidencia agregada)"
    if "rct" in st or "aleatorizado" in st:
        return "📊 Nivel: Ensayo clínico aleatorizado (evidencia clínica)"
    if "ecological" in st or "ecológico" in st or "population" in st:
        return "📊 Nivel: Estudio ecológico poblacional (correlación, no causalidad)"
    if "translational" in st or "translacional" in st:
        return "📊 Nivel: Estudio translacional (humanos + animales)"
    if "systematic review" in st or "revisión sistemática" in st:
        return "📊 Nivel: Revisión sistemática"
    if "mecanístico" in st or "mechanistic" in st:
        return "📊 Nivel: Estudio mecanístico (preclínico)"
    if "preclínico" in st or "preclinical" in st:
        return "📊 Nivel: Estudio preclínico (animales/células)"
    if "observacional" in st or "cohort" in st:
        return "📊 Nivel: Estudio observacional"
    return "📊 Nivel: " + study_type


def limitaciones_estudio(study_type, population):
    """Genera texto de limitaciones según el tipo de estudio."""
    st = (study_type or "").lower()
    pop = (population or "").lower()

    if "meta-analysis" in st:
        return ("Combina estudios con diseños y dosis heterogéneos. "
                "La calidad depende de los estudios incluidos y hay variabilidad entre ellos.")
    if "ecological" in st or "population" in st:
        return ("Es un estudio poblacional: muestra una asociación a nivel "
                "de población, NO prueba causalidad individual. Factores de "
                "confusión no pueden descartarse.")
    if "translational" in st or "translacional" in st:
        return ("Los hallazgos en animales (ratones) NO se trasladan "
                "directamente a humanos. Se necesita validación clínica.")
    if "preclínico" in st or "preclinical" in st or "mecanístico" in st:
        return ("Evidencia preclínica (animales o células). Los resultados "
                "son prometedores pero requieren confirmación en humanos.")
    if "rct" in st:
        if "61" in pop or "~75" in pop or "40" in pop or "20" in pop or "10" in pop:
            return ("Ensayo con muestra pequeña. Los resultados son "
                    "prometedores pero necesitan confirmación en estudios "
                    "mayores antes de aplicarlos clínicamente.")
        return ("Ensayo clínico: diseño robusto, pero los resultados deben "
                "interpretarse en el contexto de la dosis, duración y población estudiada.")
    if "systematic review" in st:
        return ("Revisión que depende de la calidad y disponibilidad de "
                "los estudios primarios. La evidencia clínica sigue siendo limitada.")
    return ("Consultar las limitaciones específicas del estudio original.")


def implicacion(finding, study_type):
    """Genera una implicación prudente del hallazgo."""
    st = (study_type or "").lower()
    f = (finding or "").lower()

    if "reverse" in f or "reverti" in f:
        return ("Si se confirma en humanos, abriría una vía terapéutica "
                "nueva. Pero por ahora es promesa, no tratamiento.")
    if "stable" in f or "estabil" in f or "maintained" in f:
        return ("El litio podría ayudar a estabilizar la cognición en fases "
                "tempranas del deterioro. No es cura, pero ralentizar el "
                "declive ya sería valioso.")
    if "lower" in f and "incidence" in f or "menor" in f:
        return ("La asociación es sugerente, pero no prueba que tomar litio "
                "prevenga demencia. Muchos factores influyen.")
    if "no cognitive" in f or "no significant" in f or "negativo" in f:
        return ("Resultado negativo o nulo: el litio no mostró beneficio "
                "cognitivo en este contexto. Es información tan valiosa "
                "como los resultados positivos.")
    if "inhibit" in f or "inhibe" in f or "gsk" in f:
        return ("Comprender el mecanismo es clave para desarrollar "
                "terapias futuras, pero un mecanismo no equivale a un "
                "tratamiento comprobado.")
    return ("Este hallazgo añade una pieza al puzzle del litio y el "
            "Alzheimer. Falta investigación para saber cómo aplicarlo.")


# ─── Generadores de contenido ──────────────────────────────────────────────


def generar_hilo_investigacion(estudio, fecha):
    """Genera un hilo de 8-12 tweets sobre un estudio."""
    tweets = []
    autores = estudio.get("Authors", "—")
    journal = estudio.get("Journal", "—")
    year = estudio.get("Year", "—")
    title = estudio.get("Title", "—")
    doi = estudio.get("DOI", "")
    stype = estudio.get("Study_Type", "—")
    pop = estudio.get("Population", "—")
    finding = estudio.get("Key_Finding", "—")
    dosis = estudio.get("Lithium_Dose", "—")

    # Tweet 1: Hook
    tweets.append(
        f"🧵 Hilo sobre el estudio de {journal} ({year}) sobre litio y Alzheimer.\n\n"
        f"{autores}\n{title}\n\n#LitioResearch #LitioYAlzheimer"
    )

    # Tweet 2: Contexto — tipo de estudio
    tweets.append(
        f"📋 ¿Qué tipo de estudio es?\n\n"
        f"{nivel_evidencia(stype)}\n\n"
        f"Cada tipo de estudio tiene un peso distinto en la evidencia científica."
    )

    # Tweet 3: Contexto — población
    tweets.append(
        f"👥 ¿En quién se estudió?\n\n"
        f"Población: {pop}\n\n"
        f"Esto nos dice a quién pueden aplicarse los resultados."
    )

    # Tweet 4-5: Hallazgo
    tweets.append(f"🔬 ¿Qué encontraron?\n\n{finding}")

    # Tweet 6: Dosis (si aplica)
    if dosis and dosis.strip() not in ("N/A", "—", ""):
        tweets.append(
            f"💊 Dosis utilizada:\n\n{dosis}\n\n"
            f"La dosis importa: terapéutica vs microdosis tienen perfiles "
            f"distintos en eficacia y seguridad."
        )

    # Tweet 7: Implicación
    tweets.append(f"💡 ¿Qué significa esto?\n\n{implicacion(finding, stype)}")

    # Tweet 8: Limitaciones
    tweets.append(
        f"⚠️ Limitaciones:\n\n{limitaciones_estudio(stype, pop)}"
    )

    # Tweet 9: Conclusión
    tweets.append(
        f"✅ En resumen:\n\n"
        f"Este estudio ({journal}, {year}) aporta evidencia sobre el litio "
        f"y el Alzheimer. Es una pieza más del rompecabezas, no la imagen completa."
    )

    # Tweet 10: Disclaimer + fuente
    fuente = f"📄 DOI: {doi}" if doi and doi.strip() != "N/A" else f"📄 {journal} ({year})"
    tweets.append(
        f"{DISCLAIMER}\n\n"
        f"Fuente: {autores} — {journal} ({year})\n"
        f"{fuente}\n\n"
        f"#LitioYAlzheimer #Neurociencia #InvestigaciónAlzheimer"
    )

    return tweets


def generar_dato_rapido(estudio, ensayo, fecha):
    """Genera 1-2 tweets con un dato clave."""
    # Alternar entre dato de estudio y dato de ensayo
    alt = seed_indice(fecha.isoformat() + "dr", 2)

    if alt == 0 and estudio:
        tweet = (
            f"💡 Dato rápido:\n\n"
            f"{estudio.get('Key_Finding', '—')}\n\n"
            f"Fuente: {estudio.get('Authors', '—')} — {estudio.get('Journal', '—')} "
            f"({estudio.get('Year', '—')})\n\n"
            f"#LitioYAlzheimer #Neurociencia"
        )
    else:
        e = ensayo or estudio
        tweet = (
            f"💡 Dato rápido:\n\n"
            f"Ensayo clínico: {e.get('Title', e.get('Title', '—'))}\n"
            f"Población: {e.get('Target_Population', e.get('Population', '—'))}\n"
            f"Resultado: {e.get('Results_Summary', e.get('Key_Finding', '—'))}\n\n"
            f"#LitioYAlzheimer #InvestigaciónAlzheimer"
        )

    # Tweet de disclaimer (cada cierto tiempo, no en cada dato)
    extra = (
        f"{DISCLAIMER}\n\n#LitioYAlzheimer"
    )
    return [tweet, extra]


def generar_faq(fecha):
    """Genera un hilo FAQ basado en datos del proyecto."""
    preguntas = [
        {
            "q": "¿Puede el litio del agua potable protegernos del Alzheimer?",
            "tweets": [
                "❓ ¿Puede el litio del agua potable protegernos del Alzheimer? 🧵\n\n#LitioFAQ #LitioYAlzheimer",
                "🌍 Un estudio en JAMA Psychiatry (Kessing et al., 2017) analizó "
                "5,7 millones de personas en Dinamarca y encontró que las zonas "
                "con mayor litio en el agua tenían MENOR incidencia de demencia.",
                "📈 Había una relación dosis-respuesta: más litio en el agua, "
                "menos demencia. Pero es un estudio ecológico: muestra "
                "correlación poblacional, NO causalidad individual.",
                "⚠️ No sabemos si el litio del agua es suficiente ni en qué "
                "dosis. Muchos otros factores (dieta, educación, genética) "
                "influyen en el riesgo de demencia.\n\n"
                "Fuente: Kessing et al., JAMA Psychiatry 2017. DOI: 10.1001/jamapsychiatry.2017.2362",
                "✅ Conclusión: la asociación es intrigante y merece más "
                "investigación, pero NO podemos recomendar tomar litio del agua "
                "como prevención.\n\n" + DISCLAIMER + "\n\n#LitioFAQ #Neurociencia",
            ],
        },
        {
            "q": "¿El litio cura el Alzheimer?",
            "tweets": [
                "❓ ¿El litio cura el Alzheimer? 🧵\n\nRespuesta corta: NO. "
                "Pero veamos qué sí sabemos.\n\n#LitioFAQ #LitioYAlzheimer",
                "🔬 El litio ha mostrado efectos neuroprotectores en estudios "
                "preclínicos: inhibe GSK-3β (clave en placas de amiloide y "
                "ovillos de tau), aumenta BDNF y reduce neuroinflamación.",
                "🏥 En humanos, el ensayo de Forlenza (BJP, 2011) mostró que "
                "pacientes con deterioro cognitivo leve (MCI) que tomaron "
                "litio mantuvieron su cognición, mientras el grupo placebo "
                "empeoró. Prometedor, pero muestra pequeña (61 pacientes).",
                "❌ En Alzheimer ya establecido (no MCI), los resultados son "
                "menos alentadores. Hampel et al. (2009) no encontró mejora "
                "cognitiva global en 71 pacientes con Alzheimer leve-moderado.",
                "✅ Conclusión: el litio NO cura el Alzheimer. Podría "
                "ralentizar el declive cognitivo en fases muy tempranas "
                "(MCI), pero se necesitan ensayos más grandes para confirmarlo.\n\n"
                + DISCLAIMER + "\n\n#LitioFAQ #Neurociencia",
            ],
        },
        {
            "q": "¿Qué diferencia hay entre microdosis y dosis terapéutica de litio?",
            "tweets": [
                "❓ ¿Microdosis vs dosis terapéutica de litio: qué diferencia hay? 🧵\n\n#LitioFAQ #LitioYAlzheimer",
                "💊 Dosis terapéutica (para trastorno bipolar): 600-1200 mg/día "
                "de carbonato de litio, con niveles en sangre de 0,6-1,2 mmol/L. "
                "Requiere monitorización estrecha por riesgo de toxicidad.",
                "🔬 Microdosis / dosis subterapéutica: cantidades mucho menores "
                "(ej: 10 mg/día de orotato de litio, o el litio natural del "
                "agua). Niveles en sangre muy bajos o indetectables.",
                "🧠 Estudios preclínicos (De-Paula et al., 2025) sugieren que "
                "incluso dosis subterapéuticas reducen placas de amiloide, "
                "mejoran memoria y aumentan BDNF en modelos animales. "
                "Pero la evidencia clínica en humanos es limitada.",
                "⚖️ El ensayo de Macleod (2022, ~300 personas) usó orotato "
                "de litio 10 mg/día durante 2 años: no hubo diferencia "
                "cognitiva vs placebo, pero fue bien tolerado.\n\n"
                + DISCLAIMER + "\n\n#LitioFAQ #Neurociencia",
            ],
        },
        {
            "q": "¿Qué dice la evidencia más reciente (2025-2026)?",
            "tweets": [
                "❓ ¿Qué dice la evidencia más reciente sobre litio y Alzheimer? 🧵\n\n#LitioFAQ #LitioYAlzheimer",
                "🆕 Aron et al. (Nature, 2025): El cerebro de personas con "
                "Alzheimer tiene niveles significativamente menores de litio. "
                "El litio se 'secuestra' en las placas de amiloide. "
                "El orotato de litio revirtió la patología en ratones.",
                "📊 Kishi et al. (2026): Meta-análisis que confirma un efecto "
                "cognitivo favorable moderado del litio, pero con alta "
                "heterogeneidad entre estudios.",
                "🏥 LATTICE (2026): Ensayo piloto de viabilidad con dosis "
                "subterapéuticas en MCI. Resultados publicados en marzo 2026. "
                "Demostró viabilidad del diseño y resultados de biomarcadores.",
                "✅ La evidencia avanza: mecanismos confirmados, señales "
                "clínicas modestas en fases tempranas, pero aún NO hay "
                "tratamiento establecido con litio para Alzheimer.\n\n"
                + DISCLAIMER + "\n\n#LitioFAQ #Neurociencia",
            ],
        },
        {
            "q": "¿Es seguro tomar litio en microdosis?",
            "tweets": [
                "❓ ¿Es seguro tomar litio en microdosis? 🧵\n\n#LitioFAQ #LitioYAlzheimer",
                "💊 Las dosis subterapéuticas de litio (ej: 10 mg/día) tienen "
                "un perfil de seguridad generalmente bueno en los ensayos "
                "publicados. El estudio Macleod (2022) reportó buena tolerancia.",
                "⚠️ PERO: 'generalmente seguro en estudios' no significa "
                "'seguro para todos'. El litio puede interactuar con otros "
                "medicamentos, afectar la función renal y tiroidea, y "
                "requiere supervisión médica.",
                "🚫 NO recomendamos tomar litio por iniciativa propia. "
                "Este bot es divulgación, no consejo médico.\n\n"
                + DISCLAIMER + "\n\n#LitioFAQ #Neurociencia",
            ],
        },
    ]

    idx = seed_indice(fecha.isoformat() + "faq", len(preguntas))
    return preguntas[idx]["tweets"]


def generar_desmentido(fecha):
    """Genera un tweet de MITO vs REALIDAD."""
    mitos = [
        {
            "mito": "El litio cura el Alzheimer",
            "realidad": (
                "El litio ha mostrado un efecto MODERADO en mantenimiento "
                "cognitivo en deterioro cognitivo leve (MCI), no en Alzheimer "
                "establecido. No hay cura para el Alzheimer."
            ),
            "fuente": "Forlenza et al. (BJP, 2011); Hampel et al. (2009)",
        },
        {
            "mito": "Las microdosis de litio son inofensivas porque son 'naturales'",
            "realidad": (
                "Las dosis subterapéuticas son bien toleradas en ensayos, "
                "pero el litio puede afectar riñón y tiroides e interactuar "
                "con otros fármacos. 'Natural' no es sinónimo de 'sin riesgo'."
            ),
            "fuente": "Macleod et al. (2022); De-Paula et al. (2025)",
        },
        {
            "mito": "El litio del agua potable previene la demencia",
            "realidad": (
                "Un estudio poblacional (Kessing 2017, 5,7M de personas en "
                "Dinamarca) encontró asociación entre más litio en el agua y "
                "menos demencia. Pero correlación poblacional ≠ causalidad individual."
            ),
            "fuente": "Kessing et al., JAMA Psychiatry 2017",
        },
        {
            "mito": "Todos los estudios de litio en Alzheimer son positivos",
            "realidad": (
                "No. Macleod (2022, ~300 personas, 2 años) NO encontró "
                "diferencia cognitiva con microdosis de litio. Hampel (2009) "
                "tampoco mostró mejora global. La evidencia es mixta."
            ),
            "fuente": "Macleod et al. (2022); Hampel et al. (2009)",
        },
        {
            "mito": "El orotato de litio es milagroso porque cruza la barrera hematoencefálica",
            "realidad": (
                "El orotato de litio se usa en estudios preclínicos con "
                "resultados prometedores (Aron 2025, Nature), pero NO hay "
                "evidencia clínica robusta en humanos que confirme ventaja "
                "sobre el carbonato. Es promesa preclínica, no hecho clínico."
            ),
            "fuente": "Aron et al. (Nature, 2025); Macleod et al. (2022)",
        },
        {
            "mito": "Si el litio inhibe GSK-3β, debería funcionar contra el Alzheimer",
            "realidad": (
                "Inhibir GSK-3β es un mecanismo plausible (reduce placas de "
                "amiloide y ovillos de tau), pero un mecanismo plausible no "
                "garantiza eficacia clínica. Muchos fármacos anti-amiloide "
                "también tuvieron mecanismos sólidos y fallaron en ensayos."
            ),
            "fuente": "De-Paula et al. (2025); Kishi et al. (2026)",
        },
    ]

    idx = seed_indice(fecha.isoformat() + "mito", len(mitos))
    m = mitos[idx]
    return [
        f"❌ MITO: {m['mito']}\n\n"
        f"✅ REALIDAD: {m['realidad']}\n\n"
        f"Fuente: {m['fuente']}\n\n"
        f"#LitioYAlzheimer #Neurociencia",
        f"{DISCLAIMER}\n\n#LitioYAlzheimer",
    ]


# ─── Renderizado a Markdown ────────────────────────────────────────────────


def tweets_a_markdown(tweets, tipo, fecha, fuentes_extra=None):
    """Convierte una lista de tweets a un documento markdown."""
    dia_nombre = DIAS_SEMANA[fecha.weekday()]
    fecha_str = fecha.strftime("%Y-%m-%d")
    cfg = CALENDARIO[fecha.weekday()]

    header = f"""# {cfg['label']} — {dia_nombre} {fecha_str}

> @NeuroLitio_AD | Bot de divulgación sobre litio y Alzheimer
> {DISCLAIMER}

---

## Contenido para X/Twitter ({len(tweets)} tweet{"s" if len(tweets) != 1 else ""})

"""
    body = ""
    for i, tweet in enumerate(tweets, 1):
        body += f"### Tweet {i}/{len(tweets)}\n\n"
        body += f"> {tweet}\n\n"
        body += f"_Caracteres: {len(tweet)}_"
        if len(tweet) > 280:
            body += f" ⚠️ **SUPERA 280 caracteres**"
        body += "\n\n---\n\n"

    fuentes = "## Fuentes citadas\n\n"
    if fuentes_extra:
        for f in fuentes_extra:
            fuentes += f"- {f}\n"
    fuentes += "\n## Hashtags\n\n"
    fuentes += f"Principales: `{cfg['hashtag']}`\n"
    fuentes += "Todas: `#LitioYAlzheimer #Neurociencia #InvestigaciónAlzheimer #LitioResearch #LitioFAQ`\n"

    footer = f"""
---

## Metadatos

- **Fecha**: {fecha_str}
- **Día**: {dia_nombre}
- **Tipo de contenido**: {tipo} ({cfg['label']})
- **Generado por**: bot/briefing.py
- **Seed**: {fecha.isoformat()}
"""

    return header + body + fuentes + footer


# ─── Orquestación principal ───────────────────────────────────────────────


def generar_contenido_dia(fecha, estudios, ensayos, verbose=False):
    """Genera el contenido para una fecha dada y devuelve (filename, markdown)."""
    fecha_str = fecha.isoformat()
    weekday = fecha.weekday()
    cfg = CALENDARIO[weekday]
    tipo = cfg["tipo"]

    fuentes = []

    if tipo == "hilo_investigacion":
        estudio = seleccionar_estudio(fecha_str, estudios)
        tweets = generar_hilo_investigacion(estudio, fecha)
        fuentes.append(
            f"{estudio.get('Authors', '—')} — {estudio.get('Title', '—')}. "
            f"{estudio.get('Journal', '—')} ({estudio.get('Year', '—')}). "
            f"DOI: {estudio.get('DOI', 'N/A')}"
        )
        if verbose:
            print(f"  Estudio seleccionado: {estudio.get('Authors', '?')} ({estudio.get('Year', '?')})")

    elif tipo == "dato_rapido":
        estudio = seleccionar_estudio(fecha_str, estudios)
        ensayo = seleccionar_ensayo(fecha_str, ensayos)
        tweets = generar_dato_rapido(estudio, ensayo, fecha)
        fuentes.append(
            f"{estudio.get('Authors', '—')} — {estudio.get('Journal', '—')} "
            f"({estudio.get('Year', '—')})"
        )
        if verbose:
            print(f"  Dato de: {estudio.get('Authors', '?')}")

    elif tipo == "faq":
        tweets = generar_faq(fecha)
        if verbose:
            print(f"  FAQ generada")

    elif tipo == "desmentido":
        tweets = generar_desmentido(fecha)
        if verbose:
            print(f"  Desmentido generado")

    else:
        tweets = [f"Contenido para {fecha_str}"]

    md = tweets_a_markdown(tweets, tipo, fecha, fuentes if fuentes else None)

    filename = f"{fecha_str}_{tipo}.md"
    return filename, md


def main():
    parser = argparse.ArgumentParser(
        description="Generador de contenido para @NeuroLitio_AD"
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Fecha en formato YYYY-MM-DD (default: hoy)"
    )
    parser.add_argument(
        "--week", action="store_true",
        help="Generar contenido para toda la semana (Lun-Dom)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Listar el calendario y salir"
    )
    args = parser.parse_args()

    # Modo --list
    if args.list:
        print("=" * 60)
        print("CALENDARIO SEMANAL @NeuroLitio_AD")
        print("=" * 60)
        for wd in range(7):
            cfg = CALENDARIO[wd]
            print(f"  {DIAS_SEMANA[wd]:12s} → {cfg['label']:30s} [{cfg['tipo']}]")
        print()
        estudios = cargar_estudios()
        ensayos = cargar_ensayos()
        print(f"Estudios disponibles: {len(estudios)}")
        print(f"Ensangos disponibles: {len(ensayos)}")
        print(f"Output: {OUT_DIR}/")
        return

    # Resolver fecha
    if args.date:
        fecha = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        fecha = date.today()

    # Cargar datos
    print(f"Cargando datos desde {DATA_DIR}/...")
    estudios = cargar_estudios()
    ensayos = cargar_ensayos()
    print(f"  {len(estudios)} estudios de litio cargados")
    print(f"  {len(ensayos)} ensayos clínicos cargados")

    # Crear directorio output
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.week:
        # Generar toda la semana (lunes a domingo)
        lunes = fecha - timedelta(days=fecha.weekday())
        print(f"\nGenerando semana del {lunes.isoformat()} al {(lunes + timedelta(days=6)).isoformat()}:")
        for i in range(7):
            d = lunes + timedelta(days=i)
            print(f"\n  {DIAS_SEMANA[d.weekday()]} {d.isoformat()}:")
            filename, md = generar_contenido_dia(d, estudios, ensayos, verbose=True)
            path = os.path.join(OUT_DIR, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"    → {path}")
    else:
        # Generar un solo día
        cfg = CALENDARIO[fecha.weekday()]
        print(f"\nDía: {DIAS_SEMANA[fecha.weekday()]} {fecha.isoformat()}")
        print(f"Tipo de contenido: {cfg['label']} ({cfg['tipo']})")
        filename, md = generar_contenido_dia(fecha, estudios, ensayos, verbose=True)
        path = os.path.join(OUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n✅ Generado: {path}")
        print(f"   {len(md)} caracteres, formato markdown con tweets numerados y fuentes citadas.")

    print("\nHecho.")


if __name__ == "__main__":
    main()
