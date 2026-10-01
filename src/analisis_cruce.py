"""
analisis_cruce.py
-----------------
Cruce del CSV (base de comparacion) contra TODAS las hojas del ODS, calculo de
KPIs y clasificacion de calidad. Logica pura: no escribe archivos ni usa Excel.

Definiciones (ver tambien la hoja "Metodologia" del informe):
    - Trazabilidad CSV->ODS : casos del CSV con el mismo tipo e ID en la hoja
      de su tipo / total de casos del CSV.
    - Cobertura QA del ODS  : IDs validos del ODS que tienen un caso en el CSV /
      total de IDs validos del ODS.
    - Calidad del ODS       : filas validas / filas candidatas (con tipo o ID,
      sin contar encabezados ni filas de relleno).
"""

from collections import Counter, defaultdict
from typing import Any, Optional

from limpieza import limpiar_id
from transformacion import TIPOS_DOCUMENTO

NOTA_CIENTIFICA = "notacion_cientifica_recuperada"


def enmascarar_id(num_id: str) -> str:
    """Deja visibles los 3 primeros y 3 ultimos digitos (106****185)."""
    if len(num_id) <= 6:
        return "***"
    return num_id[:3] + "*" * (len(num_id) - 6) + num_id[-3:]


def pct(parte: int, total: int) -> Optional[float]:
    """Porcentaje con 2 decimales; None si no hay denominador."""
    return None if total == 0 else round(100.0 * parte / total, 2)


def fmt_pct(valor: Optional[float], decimales: int = 1) -> str:
    """Texto de un porcentaje; 'sin datos' si no hay denominador."""
    return "sin datos" if valor is None else f"{valor:.{decimales}f}%"


def semaforo(valor: Optional[float], umbral: dict[str, float]) -> str:
    """VERDE >= verde | AMARILLO >= amarillo | ROJO en otro caso | N/A sin dato."""
    if valor is None:
        return "N/A"
    if valor >= umbral["verde"]:
        return "VERDE"
    if valor >= umbral["amarillo"]:
        return "AMARILLO"
    return "ROJO"


def tipo_de_hoja(hoja: str) -> str:
    """'6_Tar_Seg_So' -> '6'."""
    return hoja.split("_")[0]


def descripcion_tipo(tipo: str) -> str:
    return TIPOS_DOCUMENTO.get(tipo, f"Tipo {tipo}")


def clasificar_fila_ods(celdas: list[str]) -> tuple[str, str, str]:
    """Retorna (categoria, tipo, num_id) de una fila del ODS."""
    tipo = celdas[0].strip() if celdas else ""
    num = limpiar_id(celdas[1]) if len(celdas) > 1 else ""
    if not tipo and not num:
        return "relleno", tipo, num
    if tipo and not tipo.isdigit():
        return ("encabezado" if num and not num.isdigit() else "otra"), tipo, num
    if num == "0":
        return "placeholder_cero", tipo, num
    if tipo.isdigit() and num.isdigit():
        return "valida", tipo, num
    if tipo.isdigit() and not num:
        return "tipo_sin_id", tipo, num
    if not tipo and num.isdigit():
        return "id_sin_tipo", tipo, num
    return "otra", tipo, num


def longitud_declarada(celdas: list[str], num_id: str) -> str:
    """Compara la longitud declarada en la columna 3 con la real del ID."""
    if len(celdas) > 2 and celdas[2].strip().isdigit():
        return "ok" if int(celdas[2]) == len(num_id) else "distinta"
    return "ausente"


def procesar_ods(filas_ods: list[dict]) -> dict[str, Any]:
    """Clasifica cada fila del ODS y acumula metricas de calidad por hoja."""
    validos: list[dict] = []
    excluidos: list[dict] = []
    calidad: dict[str, dict[str, Any]] = {}
    for r in filas_ods:
        hoja, celdas = r["hoja"], r["celdas"]
        categoria, tipo, num = clasificar_fila_ods(celdas)
        q = calidad.setdefault(hoja, {"conteo": Counter(), "decl": Counter(),
                                      "cientifica": 0, "columnas": Counter()})
        q["conteo"][categoria] += 1
        if categoria == "relleno":
            continue
        q["columnas"][len(celdas)] += 1
        registro = {
            "hoja": hoja, "fila": r["fila"], "tipo": tipo, "num_id": num,
            "categoria": categoria, "celdas": len(celdas),
            "long_decl": longitud_declarada(celdas, num) if categoria == "valida" else "",
            "nota": NOTA_CIENTIFICA if r["notas"] else "",
        }
        if categoria == "valida":
            validos.append(registro)
            q["decl"][registro["long_decl"]] += 1
        else:
            excluidos.append(registro)
        if registro["nota"]:
            q["cientifica"] += 1
    return {"validos": validos, "excluidos": excluidos, "calidad": calidad}


def hojas_calidad(proc: dict[str, Any], umbral_calidad: dict[str, float]) -> list[dict]:
    """Una fila de calidad por hoja del ODS."""
    tipicas = {h: q["columnas"].most_common(1)[0][0] if q["columnas"] else 0
               for h, q in proc["calidad"].items()}
    referencia = Counter(tipicas.values()).most_common(1)[0][0] if tipicas else 0
    ids_por_hoja: dict[str, Counter] = defaultdict(Counter)
    for r in proc["validos"]:
        ids_por_hoja[r["hoja"]][r["num_id"]] += 1

    filas = []
    for hoja, q in proc["calidad"].items():
        c = q["conteo"]
        descartadas = sum(c[k] for k in ("placeholder_cero", "tipo_sin_id", "id_sin_tipo", "otra"))
        candidatas = c["valida"] + descartadas
        calidad = pct(c["valida"], candidatas)
        filas.append({
            "hoja": hoja, "tipo": tipo_de_hoja(hoja),
            "filas_leidas": sum(c.values()), "relleno": c["relleno"], "encabezado": c["encabezado"],
            "candidatas": candidatas, "validas": c["valida"],
            "placeholder_cero": c["placeholder_cero"], "tipo_sin_id": c["tipo_sin_id"],
            "id_sin_tipo": c["id_sin_tipo"], "otra": c["otra"],
            "calidad_pct": calidad, "semaforo": semaforo(calidad, umbral_calidad),
            "duplicados": sum(v - 1 for v in ids_por_hoja[hoja].values() if v > 1),
            "notacion_cientifica": q["cientifica"],
            "long_ok": q["decl"]["ok"], "long_distinta": q["decl"]["distinta"],
            "long_ausente": q["decl"]["ausente"],
            "columnas_tipicas": tipicas[hoja], "estructura_distinta": tipicas[hoja] != referencia,
        })
    return sorted(filas, key=lambda f: int(f["tipo"]) if f["tipo"].isdigit() else 99)


def cruzar_csv(filas_csv: list[tuple[int, list[str]]], proc: dict[str, Any]) -> list[dict]:
    """Clasifica cada caso del CSV contra TODAS las hojas del ODS."""
    candidatos = proc["validos"] + [e for e in proc["excluidos"] if e["categoria"] == "id_sin_tipo"]
    indice: dict[str, list[dict]] = defaultdict(list)
    for r in candidatos:
        indice[r["num_id"]].append(r)

    detalle = []
    for fila, celdas in filas_csv:
        tipo = celdas[0].strip() if celdas else ""
        num = limpiar_id(celdas[1]) if len(celdas) > 1 else ""
        base = {"fila_csv": fila, "tipo": tipo, "num_id": num, "hoja_ods": "", "fila_ods": "",
                "hojas_encontradas": [], "observacion": ""}
        if not (tipo.isdigit() and num.isdigit()):
            detalle.append({**base, "resultado": "invalida"})
            continue
        hits = indice.get(num, [])
        base["hojas_encontradas"] = sorted({h["hoja"] for h in hits})
        exactas = [h for h in hits if h["tipo"] == tipo and tipo_de_hoja(h["hoja"]) == tipo]
        sin_tipo = [h for h in hits if not h["tipo"] and tipo_de_hoja(h["hoja"]) == tipo]
        if exactas:
            h = exactas[0]
            obs = "ID guardado en notacion cientifica en el ODS (recuperado)" if h["nota"] else ""
            detalle.append({**base, "resultado": "exacta", "hoja_ods": h["hoja"],
                            "fila_ods": h["fila"], "observacion": obs})
        elif sin_tipo:
            h = sin_tipo[0]
            detalle.append({**base, "resultado": "id_sin_tipo", "hoja_ods": h["hoja"],
                            "fila_ods": h["fila"], "observacion": "La fila del ODS no declara el tipo"})
        elif hits:
            h = hits[0]
            detalle.append({**base, "resultado": "otra_hoja", "hoja_ods": h["hoja"],
                            "fila_ods": h["fila"],
                            "observacion": f"En el ODS aparece con tipo '{h['tipo']}'"})
        else:
            detalle.append({**base, "resultado": "no_encontrado"})
    return detalle


def resumen_por_tipo(detalle: list[dict], validos: list[dict], umbral: dict[str, float]) -> list[dict]:
    """Trazabilidad y cobertura QA por tipo de documento."""
    csv_por_tipo = Counter(d["tipo"] for d in detalle if d["resultado"] != "invalida")
    exactas = Counter(d["tipo"] for d in detalle if d["resultado"] == "exacta")
    claves_csv = {(d["tipo"], d["num_id"]) for d in detalle}
    ods_por_tipo = Counter(v["tipo"] for v in validos)
    cubiertos = Counter(v["tipo"] for v in validos if (v["tipo"], v["num_id"]) in claves_csv)

    tipos = sorted(set(TIPOS_DOCUMENTO) | set(csv_por_tipo) | set(ods_por_tipo),
                   key=lambda t: int(t) if t.isdigit() else 99)
    filas = []
    for t in tipos:
        n_csv, n_ods = csv_por_tipo[t], ods_por_tipo[t]
        cobertura = pct(cubiertos[t], n_ods)
        filas.append({
            "tipo": t, "descripcion": descripcion_tipo(t),
            "hoja": next((v["hoja"] for v in validos if v["tipo"] == t), ""),
            "csv": n_csv, "ods": n_ods, "coincidencias": exactas[t],
            "solo_csv": n_csv - exactas[t], "solo_ods": n_ods - cubiertos[t],
            "trazabilidad": pct(exactas[t], n_csv), "cobertura_qa": cobertura,
            "semaforo": semaforo(cobertura, umbral),
        })
    return filas


def matriz_csv_hoja(detalle: list[dict], hojas: list[str]) -> dict[str, dict[str, int]]:
    """Casos del CSV por tipo (filas) segun la hoja del ODS donde aparece el ID (columnas)."""
    matriz: dict[str, Counter] = defaultdict(Counter)
    for d in detalle:
        if d["resultado"] == "invalida":
            continue
        for hoja in d["hojas_encontradas"] or ["No encontrado"]:
            matriz[d["tipo"]][hoja] += 1
    columnas = hojas + ["No encontrado"]
    return {t: {c: matriz[t][c] for c in columnas}
            for t in sorted(matriz, key=lambda x: int(x) if x.isdigit() else 99)}


def construir_kpis(res: dict[str, Any], u: dict[str, dict[str, float]]) -> list[dict]:
    """Tabla de KPIs gerenciales con semaforo."""
    s, tipos = res["resumen"], res["por_tipo"]
    con_cobertura = [t for t in tipos if t["cobertura_qa"] is not None]
    peor = min(con_cobertura, key=lambda t: t["cobertura_qa"]) if con_cobertura else None
    rojos = [t for t in con_cobertura if t["semaforo"] == "ROJO"]

    def kpi(nombre, definicion, valor, unidad, clave=None, detalle=""):
        sem = semaforo(valor, u[clave]) if clave and valor is not None else "N/A"
        umbral = f"verde >= {u[clave]['verde']:g} | amarillo >= {u[clave]['amarillo']:g}" if clave else "-"
        return {"nombre": nombre, "definicion": definicion, "valor": valor, "unidad": unidad,
                "umbral": umbral, "semaforo": sem, "detalle": detalle}

    return [
        kpi("Trazabilidad CSV a ODS",
            "Casos del CSV con el mismo tipo e ID en la hoja de su tipo / total de casos del CSV",
            s["trazabilidad"], "%", "trazabilidad", f"{s['csv_exactas']} de {s['csv_total']} casos"),
        kpi("Cobertura QA global del ODS",
            "IDs validos del ODS con caso en el CSV / IDs validos del ODS",
            s["cobertura_global"], "%", "cobertura_qa", f"{s['ods_cubiertos']} de {s['ods_validos']} IDs"),
        kpi("Peor cobertura QA por tipo", "Menor cobertura QA entre los tipos de documento",
            peor["cobertura_qa"] if peor else None, "%", "cobertura_qa",
            f"{peor['descripcion']} (tipo {peor['tipo']})" if peor else ""),
        kpi("Tipos de documento en rojo", "Tipos con cobertura QA bajo el umbral amarillo",
            len(rojos), "tipos", None, ", ".join(t["descripcion"] for t in rojos)),
        kpi("Calidad del ODS",
            "Filas validas / filas candidatas (con tipo o ID, sin encabezados ni relleno)",
            s["calidad_ods"], "%", "calidad_ods",
            f"{s['ods_validos']} validas de {s['ods_candidatas']} candidatas"),
        kpi("IDs del ODS sin caso QA", "IDs validos del ODS que no aparecen en el CSV", s["ods_sin_qa"], "IDs"),
        kpi("Casos CSV sin referencia exacta", "Casos del CSV que no coinciden exactamente con el ODS",
            s["csv_total"] - s["csv_exactas"], "casos"),
        kpi("IDs en notacion cientifica",
            "IDs del ODS guardados como numero; se recuperan pero son un riesgo en el origen",
            s["notacion_cientifica"], "IDs"),
    ]


def construir_hallazgos(res: dict[str, Any]) -> list[str]:
    """Hallazgos principales, redactados con las cifras reales."""
    s, tipos, hojas = res["resumen"], res["por_tipo"], res["hojas_calidad"]
    h = [
        f"{s['csv_exactas']} de {s['csv_total']} casos del CSV ({fmt_pct(s['trazabilidad'])}) estan en el ODS con el mismo tipo e ID.",
        f"{s['ods_cubiertos']} de {s['ods_validos']} IDs validos del ODS ({fmt_pct(s['cobertura_global'])}) tienen caso de prueba.",
    ]
    completos = [t for t in tipos if t["csv"] and t["trazabilidad"] == 100 and t["cobertura_qa"] == 100]
    h.append(f"{len(completos)} de {len(tipos)} tipos de documento cruzan al 100% en ambos sentidos.")
    for t in tipos:
        if t["semaforo"] == "ROJO":
            h.append(f"{t['descripcion']} (tipo {t['tipo']}): solo {t['coincidencias']} de {t['ods']} IDs del ODS "
                     f"tienen caso QA ({fmt_pct(t['cobertura_qa'])}); {t['solo_csv']} caso(s) del CSV no estan en el ODS.")
    distintas = [x["hoja"] for x in hojas if x["estructura_distinta"]]
    if distintas:
        h.append("Hojas con menos columnas que el resto (estructura distinta): " + ", ".join(distintas) + ".")
    if s["notacion_cientifica"]:
        h.append(f"{s['notacion_cientifica']} IDs del ODS estaban en notacion cientifica; "
                 "se recuperaron del valor almacenado.")
    return h


def construir_decisiones(res: dict[str, Any]) -> list[dict]:
    """Decisiones que se le piden al POM, ordenadas por prioridad."""
    s, tipos, hojas = res["resumen"], res["por_tipo"], res["hojas_calidad"]
    d = []
    for t in tipos:
        if t["semaforo"] == "ROJO":
            d.append({"prioridad": "Alta",
                      "decision": f"Definir si los {t['solo_ods']} IDs del ODS de {t['descripcion']} sin caso QA deben probarse.",
                      "soporte": f"Cobertura QA {fmt_pct(t['cobertura_qa'])} ({t['coincidencias']} de {t['ods']}).",
                      "responsable": "POM / QA"})
    sin_ref = s["csv_total"] - s["csv_exactas"]
    if sin_ref:
        d.append({"prioridad": "Media",
                  "decision": ("Confirmar si el caso del CSV sin referencia debe incorporarse al ODS o retirarse del CSV."
                              if sin_ref == 1 else
                              f"Confirmar si los {sin_ref} casos del CSV sin referencia deben incorporarse al ODS o retirarse del CSV."),
                  "soporte": "Ver hoja Detalle CSV, filtro por resultado.", "responsable": "POM / duenio del ODS"})
    distintas = [x["hoja"] for x in hojas if x["estructura_distinta"]]
    if distintas:
        d.append({"prioridad": "Media",
                  "decision": "Alinear la estructura de las hojas con menos columnas o confirmar que es intencional: "
                              + ", ".join(distintas) + ".",
                  "soporte": "Ver hoja Calidad ODS, columna Columnas tipicas.", "responsable": "Duenio del ODS"})
    descartadas = s["ods_candidatas"] - s["ods_validos"]
    if s["notacion_cientifica"] or descartadas:
        d.append({"prioridad": "Media",
                  "decision": "Corregir en el origen: guardar los IDs como texto y depurar filas con ID vacio, 0 o sin tipo.",
                  "soporte": f"{descartadas} fila(s) descartada(s); {s['notacion_cientifica']} ID(s) en notacion cientifica.",
                  "responsable": "Duenio del ODS"})
    d.append({"prioridad": "Baja",
              "decision": "Validar los umbrales del semaforo: son una propuesta tecnica, no un acuerdo.",
              "soporte": "Ver hoja Metodologia y config/configuracion.yaml.", "responsable": "POM"})
    return d


def analizar_datos(filas_csv: list[tuple[int, list[str]]], filas_ods: list[dict],
                   umbrales: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Ejecuta el analisis completo sobre filas ya leidas."""
    from datetime import datetime

    proc = procesar_ods(filas_ods)
    validos, excluidos = proc["validos"], proc["excluidos"]
    detalle = cruzar_csv(filas_csv, proc)
    calidad = hojas_calidad(proc, umbrales["calidad_ods"])

    claves_csv = {(d["tipo"], d["num_id"]) for d in detalle}
    ods_sin_qa = [v for v in validos if (v["tipo"], v["num_id"]) not in claves_csv]
    candidatas = len(validos) + sum(1 for e in excluidos if e["categoria"] != "encabezado")
    csv_total = sum(1 for d in detalle if d["resultado"] != "invalida")
    csv_exactas = sum(1 for d in detalle if d["resultado"] == "exacta")
    repetidas = Counter((d["tipo"], d["num_id"]) for d in detalle if d["resultado"] != "invalida")

    resumen = {
        "csv_total": csv_total, "csv_exactas": csv_exactas,
        "csv_duplicados": sum(v - 1 for v in repetidas.values() if v > 1),
        "ods_validos": len(validos), "ods_cubiertos": len(validos) - len(ods_sin_qa),
        "ods_sin_qa": len(ods_sin_qa), "ods_candidatas": candidatas,
        "trazabilidad": pct(csv_exactas, csv_total),
        "cobertura_global": pct(len(validos) - len(ods_sin_qa), len(validos)),
        "calidad_ods": pct(len(validos), candidatas),
        "notacion_cientifica": sum(h["notacion_cientifica"] for h in calidad),
        "resultados": dict(Counter(d["resultado"] for d in detalle)),
    }
    res: dict[str, Any] = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "umbrales": umbrales, "resumen": resumen,
        "por_tipo": resumen_por_tipo(detalle, validos, umbrales["cobertura_qa"]),
        "hojas_calidad": calidad, "detalle_csv": detalle,
        "matriz": matriz_csv_hoja(detalle, [h["hoja"] for h in calidad]),
        "ods_sin_qa": ods_sin_qa, "ods_excluidos": excluidos,
    }
    res["kpis"] = construir_kpis(res, umbrales)
    res["hallazgos"] = construir_hallazgos(res)
    res["decisiones"] = construir_decisiones(res)
    return res


def analizar(ruta_csv: str, ruta_ods: str, umbrales: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Lee los archivos de origen y ejecuta el analisis."""
    from limpieza import leer_csv_con_fila, leer_ods_detallado
    return analizar_datos(leer_csv_con_fila(ruta_csv), leer_ods_detallado(ruta_ods), umbrales)
