"""Ejercicio 7: autenticación local e instalación reproducible del tablero."""
import argparse
import getpass
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SESSION_FILE = ROOT / "data" / "processed" / "metabase_session.json"
STATE_FILE = ROOT / "data" / "processed" / "metabase_dashboard_state.json"
CONFIG = ROOT / "docs" / "tablero" / "indicadores.json"


def call(session, method, base, path, **kwargs):
    response = session.request(method, base + "/api/" + path, timeout=300, **kwargs)
    if not response.ok:
        # Nunca mostrar headers de sesión, credenciales o cookies.
        raise RuntimeError(f"Metabase {method} {path}: HTTP {response.status_code}: {response.text[:1000]}")
    return response.json() if response.content else None


def login(base):
    print("Inicio de sesión local. La contraseña no se muestra ni se guarda.")
    username = input("Correo de Metabase: ").strip()
    password = getpass.getpass("Contraseña: ")
    with requests.Session() as session:
        result = call(session, "POST", base, "session", json={"username": username, "password": password})
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps({"base_url": base, "session_id": result["id"]}) + "\n")
    SESSION_FILE.chmod(0o600)
    print("Sesión guardada en data/processed/metabase_session.json (excluida de Git).")


def install(base, public_url="http://localhost:3000"):
    credentials = json.loads(SESSION_FILE.read_text())
    if credentials.get("base_url") != base:
        raise ValueError("La sesión pertenece a otra URL. Inicie sesión para esta instalación.")
    session = requests.Session()
    session.headers["X-Metabase-Session"] = credentials["session_id"]
    call(session, "GET", base, "user/current")
    config = json.loads(CONFIG.read_text())
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    desired_file = "/workspace/"+config.get("database_file", "data/processed/benchmark/completo.duckdb")
    temp_id = hashlib.sha256(desired_file.encode()).hexdigest()[:12]
    desired_init = f"SET threads=4; SET temp_directory='/tmp/duckdb-metabase-{temp_id}';"
    if not state.get("database_id"):
        existing = call(session, "GET", base, "database")["data"]
        database = next((d for d in existing if d["name"] == "NYC Taxi · DuckDB local"), None)
        if database is None:
            database = call(session, "POST", base, "database", json={
                "name": "NYC Taxi · DuckDB local", "engine": "duckdb", "is_full_sync": True,
                "details": {"database_file": "/workspace/"+config.get("database_file", "data/processed/benchmark/completo.duckdb"),
                            "read_only": True, "memory_limit": "1GB", "init_sql": desired_init}})
        state["database_id"] = database["id"]
    current = call(session, "GET", base, "database/"+str(state["database_id"]))
    desired = desired_file
    if current["details"].get("database_file") != desired or current["details"].get("init_sql") != desired_init:
        details = current["details"]
        details.update({"database_file": desired, "read_only": True, "memory_limit": "1GB",
                        "init_sql": desired_init})
        call(session, "PUT", base, "database/"+str(state["database_id"]), json={"details": details})
    if not state.get("dashboard_id"):
        dashboard = call(session, "POST", base, "dashboard", json={
            "name": config["name"], "description": "Ejercicio 7 · 2024 y 2026. Seleccione año y tipo; meses disponibles, no extrapolación anual."})
        state["dashboard_id"] = dashboard["id"]
    state.setdefault("cards", {})
    def save_state():
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    save_state()
    cards = []
    for item in config["indicators"]:
        tags = {"anio": {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, item["key"]+"anio")),
                          "name": "anio", "display-name": "Año", "type": "number", "required": False, "default": 2026},
                "tipo_taxi": {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, item["key"]+"tipo")),
                              "name": "tipo_taxi", "display-name": "Tipo de taxi", "type": "text", "required": False}}
        if item.get("ignore_year"): tags.pop("anio")
        payload = {"name": item["name"], "description": item["question"] + " " + item["rationale"] + " Población: " + item["population"] + ". Unidad: " + item["unit"],
                   "dataset_query": {"database": state["database_id"], "type": "native",
                                     "native": {"query": (ROOT/item["sql"]).read_text(), "template-tags": tags}},
                   "display": item["display"], "visualization_settings": item["visualization_settings"]}
        if item["key"] in state["cards"]:
            card = call(session, "PUT", base, "card/"+str(state["cards"][item["key"]]), json=payload)
        else:
            card = call(session, "POST", base, "card", json=payload)
            state["cards"][item["key"]] = card["id"]
            save_state()
        result = call(session, "POST", base, f"card/{card['id']}/query", json={"parameters": []})
        if result.get("status") != "completed":
            raise RuntimeError(f"La consulta {item['key']} no terminó correctamente: {result.get('error')}")
        output = ROOT/config.get("evidence_dir", "docs/resultados_ejercicio_7/metabase")
        output.mkdir(parents=True, exist_ok=True)
        # Evidencia de datos, sin tokens ni cookies.
        (output/(item["key"]+".json")).write_text(json.dumps({"card_id": card["id"], "status": result["status"],
            "columns": [{"name": c["name"], "base_type": c.get("base_type")} for c in result["data"]["cols"]],
            "rows": result["data"]["rows"]}, indent=2, ensure_ascii=False) + "\n")
        cards.append({"id": -(len(cards)+1), "card_id": card["id"],
                      **{k:item[k] for k in ("row","col","size_x","size_y")},
                      "parameter_mappings": [
                          {"parameter_id": "anio", "card_id": card["id"], "target": ["variable", ["template-tag", "anio"]]},
                          {"parameter_id": "tipo_taxi", "card_id": card["id"], "target": ["variable", ["template-tag", "tipo_taxi"]]}]})
        if item.get("ignore_year"):
            cards[-1]["parameter_mappings"] = [m for m in cards[-1]["parameter_mappings"] if m["parameter_id"] != "anio"]
        print("Indicador verificado:", item["key"], flush=True)
    intro = {"id": -100, "card_id": None, "row": 0, "col": 0, "size_x": 24, "size_y": 3,
             "visualization_settings": {"virtual_card": {"name": "Alcance", "display": "text", "dataset_query": {}},
             "text": "## Viajes de taxi NYC · Laboratorio 8\nAño inicial: **2026**. Tipo: escriba **yellow** o **green**, o deje vacío para ambos. 2024 y 2025 tienen 12 meses; 2026 solo los publicados. Las mediciones filtran distancia (0,100] millas, duración (0,24] horas y pagos positivos. Las propinas se analizan solo en tarjeta. Los índices comparan perfiles relativos, no volumen absoluto."}}
    dashboard = call(session, "PUT", base, f"dashboard/{state['dashboard_id']}", json={
        "dashcards": [intro,*cards], "width": "full", "parameters": [
            {"id": "anio", "name": "Año", "slug": "anio", "type": "number/=", "default": [2026]},
            {"id": "tipo_taxi", "name": "Tipo: yellow / green", "slug": "tipo_taxi", "type": "string/="}]})
    evidence = {"dashboard_id": state["dashboard_id"], "url": public_url+f"/dashboard/{state['dashboard_id']}",
                "database_id": state["database_id"], "read_only": True, "cards": state["cards"],
                "indicadores": len(cards), "verificados": True, "fecha_utc": datetime.now(timezone.utc).isoformat()}
    (ROOT/"docs"/"tablero"/"metabase_evidencia.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False)+"\n")
    print("Tablero listo:", evidence["url"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--public-url", default="http://localhost:3000")
    parser.add_argument("--url", default="http://localhost:3000")
    args = parser.parse_args()
    if args.login: login(args.url.rstrip("/"))
    else: install(args.url.rstrip("/"), args.public_url.rstrip("/"))


if __name__ == "__main__": main()
