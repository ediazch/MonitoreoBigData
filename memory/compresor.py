#!/usr/bin/env python3
"""
compresor.py — Compresion inteligente de memoria para aura-mem.
100% local, sin API keys, sin internet.

Estrategia hibrida:
    1. Sumy (LSA) — compresion estadistica de texto largo
    2. Reglas inteligentes — fallback si sumy falla, y para textos cortos

Equivalente al componente de compresion semantica de claude-mem
pero implementado completamente offline.

Uso (automatico — llamado por aura_mem.py y session_log.py):
    from compresor import comprimir_sesion, comprimir_observaciones

Uso manual:
    python memory/compresor.py --sesion <sesion_id>
    python memory/compresor.py --auto          <- comprime sesiones sin comprimir
    python memory/compresor.py --stats         <- muestra estadisticas de compresion
"""

import os
import sys
import re
from datetime import datetime
from collections import Counter
from typing import Optional

# ---------------------------------------------------------------------------
# Auto-instalar dependencias si faltan
# ---------------------------------------------------------------------------
import subprocess

def _asegurar_dependencia(modulo: str, paquete: str) -> bool:
    try:
        __import__(modulo)
        return True
    except ImportError:
        print(f"[compresor] Instalando {paquete}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", paquete, "--quiet"])
        return True


_asegurar_dependencia("sumy", "sumy")
_asegurar_dependencia("nltk", "nltk")

import nltk
# Descargar recursos NLTK si no existen
for recurso in ["punkt", "punkt_tab", "stopwords"]:
    try:
        nltk.data.find(f"tokenizers/{recurso}")
    except LookupError:
        nltk.download(recurso, quiet=True)

sys.path.insert(0, os.path.dirname(__file__))
from aura_mem import conectar

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
UMBRAL_COMPRIMIR    = 10   # comprimir sesion cuando tiene >= N observaciones
RATIO_COMPRESION    = 0.3  # conservar 30% de las frases originales (70% reduccion)
MIN_FRASES_SUMY     = 3    # minimo de frases para usar Sumy (texto muy corto usa reglas)
TIPOS_PRIORITARIOS  = {"decision", "bugfix", "error", "fase"}  # nunca descartar estos
TIPOS_DESCARTABLES  = {"nota"}  # candidatos a comprimir primero

SEP = "=" * 60


# ---------------------------------------------------------------------------
# Motor de compresion — Sumy LSA
# ---------------------------------------------------------------------------

def _comprimir_con_sumy(texto: str, num_frases: int = 3) -> str:
    """
    Usa el algoritmo LSA (Latent Semantic Analysis) de Sumy.
    LSA identifica las frases mas semanticamente importantes
    usando descomposicion de valores singulares (SVD).
    No necesita internet ni modelos preentrenados.
    """
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lsa import LsaSummarizer
        from sumy.nlp.stemmers import Stemmer
        from sumy.utils import get_stop_words

        # Sumy trabaja mejor en ingles, pero funciona con espanol
        # usando stemmer neutro
        LANGUAGE = "spanish"
        try:
            stemmer    = Stemmer(LANGUAGE)
            stop_words = get_stop_words(LANGUAGE)
        except Exception:
            stemmer    = Stemmer("english")
            stop_words = get_stop_words("english")

        parser     = PlaintextParser.from_string(texto, Tokenizer(LANGUAGE))
        summarizer = LsaSummarizer(stemmer)
        summarizer.stop_words = stop_words

        frases = summarizer(parser.document, num_frases)
        return " | ".join(str(f) for f in frases)

    except Exception as e:
        # Fallback a reglas si sumy falla
        return _comprimir_con_reglas(texto, num_frases)


# ---------------------------------------------------------------------------
# Motor de compresion — Reglas inteligentes (fallback)
# ---------------------------------------------------------------------------

def _comprimir_con_reglas(texto: str, num_frases: int = 3) -> str:
    """
    Compresion basada en reglas cuando Sumy no puede procesar el texto.
    Algoritmo:
        1. Tokenizar en frases
        2. Puntuar cada frase por: longitud optima + palabras clave + posicion
        3. Retornar las N frases con mayor puntaje
    """
    # Palabras clave de alto valor para este proyecto
    KEYWORDS_ALTO_VALOR = {
        "completad", "instalad", "error", "bug", "fase", "resultado",
        "coincidencia", "analisis", "cobertura", "test", "prueba",
        "decision", "implementad", "creado", "git", "commit", "auto"
    }

    frases = _tokenizar_frases(texto)
    if not frases:
        return texto[:200]
    if len(frases) <= num_frases:
        return " | ".join(frases)

    puntuaciones = []
    for i, frase in enumerate(frases):
        puntaje = 0.0
        palabras = frase.lower().split()

        # Factor 1: longitud optima (ni muy corta ni muy larga)
        if 5 <= len(palabras) <= 25:
            puntaje += 1.0
        elif len(palabras) < 5:
            puntaje -= 0.5

        # Factor 2: palabras clave del proyecto
        for palabra in palabras:
            for kw in KEYWORDS_ALTO_VALOR:
                if kw in palabra:
                    puntaje += 0.5
                    break

        # Factor 3: posicion (primera y ultima frase son mas importantes)
        if i == 0 or i == len(frases) - 1:
            puntaje += 0.3

        # Factor 4: contiene numeros (datos concretos)
        if re.search(r'\d+', frase):
            puntaje += 0.4

        # Factor 5: contiene prefijos de tipo auto-mem
        if any(tag in frase.upper() for tag in ["[AUTO]", "[GIT]", "[F]", "[R]", "[!]"]):
            puntaje += 0.6

        puntuaciones.append((puntaje, i, frase))

    # Ordenar por puntaje, mantener orden original
    top = sorted(puntuaciones, key=lambda x: x[0], reverse=True)[:num_frases]
    top_ordenado = sorted(top, key=lambda x: x[1])

    return " | ".join(f for _, _, f in top_ordenado)


def _tokenizar_frases(texto: str) -> list[str]:
    """Divide texto en frases usando NLTK o fallback simple."""
    try:
        from nltk.tokenize import sent_tokenize
        frases = sent_tokenize(texto, language="spanish")
        if len(frases) == 1:
            # Si NLTK no separo bien, usar separadores manuales
            frases = re.split(r'[.\n|]+', texto)
    except Exception:
        frases = re.split(r'[.\n|]+', texto)

    return [f.strip() for f in frases if f.strip() and len(f.strip()) > 10]


# ---------------------------------------------------------------------------
# Compresion de sesion completa
# ---------------------------------------------------------------------------

def comprimir_sesion(sesion_id: str, verbose: bool = True) -> Optional[str]:
    """
    Comprime todas las observaciones de una sesion en un resumen compacto.
    Estrategia:
        - Tipos prioritarios (decision, bugfix, error, fase): siempre incluidos
        - Resto: comprimidos con Sumy/Reglas
        - Resultado: guardado en sesiones.resumen + tabla comprimidos

    Returns:
        Resumen comprimido como string, o None si falla.
    """
    conn = conectar()

    obs = conn.execute(
        "SELECT id, tipo, mensaje, fecha FROM observaciones WHERE sesion_id=? ORDER BY fecha",
        (sesion_id,)
    ).fetchall()

    if not obs:
        conn.close()
        return None

    tokens_antes = sum(len(o["mensaje"].split()) for o in obs)

    # Separar por prioridad
    prioritarias = [o for o in obs if o["tipo"] in TIPOS_PRIORITARIOS]
    resto        = [o for o in obs if o["tipo"] not in TIPOS_PRIORITARIOS]

    # Construir texto para comprimir del resto
    texto_resto = "\n".join(
        f"[{o['tipo'].upper()}] {o['mensaje']}" for o in resto
    ) if resto else ""

    # Calcular cuantas frases conservar
    num_frases = max(2, int(len(obs) * RATIO_COMPRESION))

    # Comprimir
    partes_resumen = []

    # 1. Siempre incluir prioritarias (resumidas si son muchas)
    if prioritarias:
        for p in prioritarias:
            partes_resumen.append(f"[{p['tipo'].upper()}] {p['mensaje'][:120]}")

    # 2. Comprimir el resto
    if texto_resto and len(texto_resto.split()) >= MIN_FRASES_SUMY:
        comprimido = _comprimir_con_sumy(texto_resto, num_frases=max(2, num_frases - len(prioritarias)))
        if comprimido:
            partes_resumen.append(f"[COMPRIMIDO] {comprimido}")
    elif texto_resto:
        partes_resumen.append(f"[NOTAS] {texto_resto[:200]}")

    resumen_final = " || ".join(partes_resumen)

    # Calcular reduccion
    tokens_despues = len(resumen_final.split())
    reduccion_pct  = round((1 - tokens_despues / max(tokens_antes, 1)) * 100, 1)

    # Guardar resumen en DB
    conn.execute(
        "UPDATE sesiones SET resumen=? WHERE id=?",
        (resumen_final, sesion_id)
    )
    conn.commit()
    conn.close()

    if verbose:
        print(f"\n{SEP}")
        print(f"  COMPRESION COMPLETADA — Sesion: {sesion_id}")
        print(f"  Observaciones  : {len(obs)}")
        print(f"  Tokens antes   : {tokens_antes}")
        print(f"  Tokens despues : {tokens_despues}")
        print(f"  Reduccion      : {reduccion_pct}%")
        print(f"\n  RESUMEN:")
        for parte in partes_resumen:
            print(f"  {parte[:100]}")
        print(SEP)

    return resumen_final


def comprimir_automatico(verbose: bool = True) -> int:
    """
    Comprime automaticamente todas las sesiones cerradas
    que tengan >= UMBRAL_COMPRIMIR observaciones y sin resumen aun.
    Llamado automaticamente al cerrar sesion.

    Returns:
        Numero de sesiones comprimidas.
    """
    conn = conectar()
    sesiones = conn.execute("""
        SELECT s.id, s.num_obs
        FROM sesiones s
        WHERE s.fin IS NOT NULL
          AND (s.resumen IS NULL OR s.resumen = '' OR s.resumen LIKE 'Sesion%')
          AND s.num_obs >= ?
    """, (UMBRAL_COMPRIMIR,)).fetchall()
    conn.close()

    if not sesiones:
        if verbose:
            print("[compresor] No hay sesiones que comprimir.")
        return 0

    comprimidas = 0
    for s in sesiones:
        if verbose:
            print(f"[compresor] Comprimiendo sesion {s['id']} ({s['num_obs']} obs)...")
        resultado = comprimir_sesion(s["id"], verbose=verbose)
        if resultado:
            comprimidas += 1

    return comprimidas


def stats_compresion() -> None:
    """Muestra estadisticas globales de compresion de memoria."""
    conn = conectar()

    total_obs      = conn.execute("SELECT COUNT(*) FROM observaciones").fetchone()[0]
    total_sesiones = conn.execute("SELECT COUNT(*) FROM sesiones").fetchone()[0]
    con_resumen    = conn.execute(
        "SELECT COUNT(*) FROM sesiones WHERE resumen IS NOT NULL AND resumen != ''"
    ).fetchone()[0]
    sin_resumen    = total_sesiones - con_resumen

    # Estimacion de tokens
    obs_rows = conn.execute("SELECT mensaje FROM observaciones").fetchall()
    tokens_raw = sum(len(r["mensaje"].split()) for r in obs_rows)

    res_rows = conn.execute(
        "SELECT resumen FROM sesiones WHERE resumen IS NOT NULL AND resumen != ''"
    ).fetchall()
    tokens_comprimidos = sum(len(r["resumen"].split()) for r in res_rows)

    conn.close()

    print(f"\n{SEP}")
    print(f"  ESTADISTICAS DE COMPRESION — aura-mem")
    print(SEP)
    print(f"  Total observaciones         : {total_obs}")
    print(f"  Total sesiones              : {total_sesiones}")
    print(f"  Sesiones comprimidas        : {con_resumen}")
    print(f"  Sesiones sin comprimir      : {sin_resumen}")
    print()
    print(f"  Tokens en observaciones raw : {tokens_raw}")
    print(f"  Tokens en resumenes         : {tokens_comprimidos}")
    if tokens_raw > 0:
        ahorro = round((1 - tokens_comprimidos / tokens_raw) * 100, 1)
        print(f"  Ahorro estimado de tokens   : {ahorro}%")
    print(f"\n  Umbral compresion           : >= {UMBRAL_COMPRIMIR} observaciones")
    print(f"  Ratio compresion objetivo   : {int(RATIO_COMPRESION*100)}% de frases conservadas")
    print(f"  Algoritmo primario          : Sumy LSA (local, sin internet)")
    print(f"  Algoritmo fallback          : Reglas inteligentes (frecuencia + keywords)")
    print(SEP)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="compresor: compresion local de memoria aura-mem")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sesion", help="Comprimir una sesion especifica por ID")
    group.add_argument("--auto",   action="store_true", help="Comprimir todas las sesiones pendientes")
    group.add_argument("--stats",  action="store_true", help="Ver estadisticas de compresion")

    args = parser.parse_args()

    if args.sesion:
        comprimir_sesion(args.sesion)
    elif args.auto:
        n = comprimir_automatico()
        print(f"\n  {n} sesion(es) comprimidas.")
    elif args.stats:
        stats_compresion()


if __name__ == "__main__":
    main()
