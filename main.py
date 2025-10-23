# -*- coding: utf-8 -*-
"""
Mini Red Social con Neo4j
Python 3.10+
Requiere: pip install neo4j==5.*
Diseño:
- Un nodo :Persona {nombre, ciudad, <prop_personalizada>}
- Una única relación :AMIGO_DE tratada como no dirigida
  (consultas con -- patrón no dirigido -- para garantizar simetría)
- Unicidad por nombre con CONSTRAINT
- Sin amistades duplicadas gracias a MERGE en la arista
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict
from neo4j import GraphDatabase, Driver, Session

# ==========================
# Configuración de conexión
# ==========================
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "contraseña123")

# Esta propiedad personalizada se define al inicio.
# Puedes fijarla por entorno o te preguntará al arrancar.
CUSTOM_PROP_ENV = os.getenv("CUSTOM_PROP_NAME")  # ej: "profesion"

@dataclass
class AppConfig:
    uri: str
    user: str
    password: str
    custom_prop: str  # p.ej. "profesion" o "hobby"

# ==========================
# Capa de acceso a Neo4j
# ==========================
class SocialGraph:
    """
    Encapsula todas las operaciones Cypher.
    Las transacciones se aíslan por método para claridad.
    """

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.driver: Driver = GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))

    def close(self):
        self.driver.close()

    # --------- Bootstrap ---------
    def init_db(self) -> None:
        """
        Crea restricciones e índices idempotentes.
        - Unicidad de :Persona.nombre
        - Índices útiles para búsqueda por ciudad y propiedad personalizada
        """
        cyphers = [
            # Un nombre único evita duplicar personas
            f"CREATE CONSTRAINT persona_nombre_unique IF NOT EXISTS "
            f"FOR (p:Persona) REQUIRE p.nombre IS UNIQUE",

            # Índice por ciudad para acelerar recomendaciones por ciudad
            f"CREATE INDEX persona_ciudad IF NOT EXISTS FOR (p:Persona) ON (p.ciudad)",

            # Índice por propiedad personalizada para acelerar recomendaciones
            f"CREATE INDEX persona_custom IF NOT EXISTS FOR (p:Persona) ON (p.{self.cfg.custom_prop})",
        ]
        with self.driver.session() as session:
            for c in cyphers:
                session.run(c)

    # --------- Personas ---------
    def add_person(self, nombre: str, ciudad: str, custom_value: str) -> bool:
        """
        Inserta o actualiza una persona.
        MERGE asegura idempotencia por nombre.
        """
        query = (
            f"MERGE (p:Persona {{nombre: $nombre}}) "
            f"SET p.ciudad = $ciudad, p.{self.cfg.custom_prop} = $custom_value "
            f"RETURN p"
        )
        with self.driver.session() as sess:
            rec = sess.run(query, nombre=nombre, ciudad=ciudad, custom_value=custom_value).single()
            return rec is not None

    def list_people(self) -> List[Dict]:
        query = (
            f"MATCH (p:Persona) "
            f"RETURN p.nombre AS nombre, p.ciudad AS ciudad, p.{self.cfg.custom_prop} AS custom "
            f"ORDER BY nombre"
        )
        with self.driver.session() as sess:
            return [r.data() for r in sess.run(query)]

    def get_person(self, nombre: str) -> Optional[Dict]:
        query = (
            f"MATCH (p:Persona {{nombre: $nombre}}) "
            f"RETURN p.nombre AS nombre, p.ciudad AS ciudad, p.{self.cfg.custom_prop} AS custom"
        )
        with self.driver.session() as sess:
            rec = sess.run(query, nombre=nombre).single()
            return rec.data() if rec else None

    def delete_person(self, nombre: str) -> int:
        """
        Elimina la persona y todas sus relaciones.
        Devuelve el número de nodos eliminados (0 o 1).
        """
        query = (
            "MATCH (p:Persona {nombre: $nombre}) "
            "DETACH DELETE p "
            "RETURN 1 AS deleted"
        )
        with self.driver.session() as sess:
            rec = sess.run(query, nombre=nombre).single()
            return 1 if rec else 0

    # --------- Amistad ---------
    def create_friendship(self, a: str, b: str) -> bool:
        """
        Crea UNA sola relación no dirigida entre A y B.
        Evita auto-relaciones y duplicados.
        """
        if a == b:
            return False
        query = (
            "MATCH (pa:Persona {nombre: $a}), (pb:Persona {nombre: $b}) "
            "MERGE (pa)-[:AMIGO_DE]-(pb) "
            "RETURN true AS ok"
        )
        with self.driver.session() as sess:
            rec = sess.run(query, a=a, b=b).single()
            return bool(rec and rec["ok"])

    def delete_friendship(self, a: str, b: str) -> int:
        """
        Borra la relación en cualquier dirección.
        Devuelve cuántas relaciones se eliminaron (0 o 1).
        """
        query = (
            "MATCH (pa:Persona {nombre: $a})-[r:AMIGO_DE]-(pb:Persona {nombre: $b}) "
            "DELETE r "
            "RETURN count(r) AS deleted"
        )
        with self.driver.session() as sess:
            rec = sess.run(query, a=a, b=b).single()
            return rec["deleted"]

    def list_friends(self, nombre: str) -> List[str]:
        query = (
            "MATCH (:Persona {nombre: $nombre})-[:AMIGO_DE]-(f:Persona) "
            "RETURN f.nombre AS amigo "
            "ORDER BY amigo"
        )
        with self.driver.session() as sess:
            return [r["amigo"] for r in sess.run(query, nombre=nombre)]

    # --------- Recomendaciones ---------
    def recommend_by_city(self, nombre: str) -> List[str]:
        """
        Sugiere personas de la misma ciudad que no son amigas ni la persona misma.
        """
        query = (
            "MATCH (p:Persona {nombre: $nombre}) "
            "MATCH (candidato:Persona {ciudad: p.ciudad}) "
            "WHERE candidato <> p AND NOT (p)-[:AMIGO_DE]-(candidato) "
            "RETURN candidato.nombre AS sugerido "
            "ORDER BY sugerido"
        )
        with self.driver.session() as sess:
            return [r["sugerido"] for r in sess.run(query, nombre=nombre)]

    def recommend_by_custom(self, nombre: str) -> List[str]:
        """
        Sugiere por propiedad personalizada compartida.
        """
        query = (
            f"MATCH (p:Persona {{nombre: $nombre}}) "
            f"MATCH (candidato:Persona) "
            f"WHERE candidato <> p "
            f"  AND p.{self.cfg.custom_prop} = candidato.{self.cfg.custom_prop} "
            f"  AND NOT (p)-[:AMIGO_DE]-(candidato) "
            f"RETURN candidato.nombre AS sugerido "
            f"ORDER BY sugerido"
        )
        with self.driver.session() as sess:
            return [r["sugerido"] for r in sess.run(query, nombre=nombre)]

    # --------- Stats ---------
    def stats(self) -> Dict[str, int]:
        """
        Cuenta nodos y relaciones de amistad.
        """
        with self.driver.session() as sess:
            total_personas = sess.run("MATCH (p:Persona) RETURN count(p) AS c").single()["c"]
            total_amistades = sess.run("MATCH ()-[r:AMIGO_DE]-() RETURN count(r) AS c").single()["c"]
            return {"personas": total_personas, "amistades": total_amistades}

# ==========================
# Interfaz de consola
# ==========================
def prompt(texto: str) -> str:
    return input(texto).strip()

def main():
    # Determina propiedad personalizada
    custom_prop = CUSTOM_PROP_ENV if CUSTOM_PROP_ENV else prompt(
        "Propiedad personalizada para las personas (ej: profesion, hobby, edad): "
    ) or "hobby"

    cfg = AppConfig(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASS,
        custom_prop=custom_prop
    )
    sg = SocialGraph(cfg)
    sg.init_db()

    menu = f"""
=== MINI RED SOCIAL ===
1. Agregar persona
2. Listar todas las personas
3. Buscar persona
4. Crear amistad
5. Ver amigos de una persona
6. Eliminar amistad
7. Recomendaciones por ciudad
8. Recomendaciones por {cfg.custom_prop}
9. Estadísticas
10. Eliminar persona
0. Salir
"""
    acciones = {
        "1": lambda: (
            lambda nombre, ciudad, custom:
                print("OK" if sg.add_person(nombre, ciudad, custom) else "Error")
        )(
            prompt("Nombre: "), prompt("Ciudad: "), prompt(f"{cfg.custom_prop}: ")
        ),
        "2": lambda: [print(f"- {p['nombre']} | {p['ciudad']} | {cfg.custom_prop}={p['custom']}") for p in sg.list_people()],
        "3": lambda: (
            lambda n:
                print(sg.get_person(n) if sg.get_person(n) else "No encontrada")
        )(prompt("Nombre: ")),
        "4": lambda: (
            lambda a, b:
                print("Amistad creada" if sg.create_friendship(a, b) else "No creada")
        )(prompt("Persona A: "), prompt("Persona B: ")),
        "5": lambda: (
            lambda n, amigos:
                print("Amigos:", ", ".join(amigos) if amigos else "Sin amigos")
        )(prompt("Nombre: "), None),
        "6": lambda: (
            lambda a, b, k:
                print(f"Relaciones eliminadas: {k}")
        )(prompt("Persona A: "), prompt("Persona B: "), None),
        "7": lambda: (
            lambda n, rec:
                print("Sugerencias:", ", ".join(rec) if rec else "Sin sugerencias")
        )(prompt("Nombre: "), None),
        "8": lambda: (
            lambda n, rec:
                print("Sugerencias:", ", ".join(rec) if rec else "Sin sugerencias")
        )(prompt("Nombre: "), None),
        "9": lambda: (
            lambda s: print(f"Personas={s['personas']} | Amistades={s['amistades']}")
        )(sg.stats()),
        "10": lambda: (
            lambda n, k:
                print("Eliminada" if k == 1 else "No existía")
        )(prompt("Nombre: "), None),
    }

    # Ajustes que requieren los datos recuperados en el momento
    def accion5():
        n = prompt("Nombre: ")
        amigos = sg.list_friends(n)
        print("Amigos:", ", ".join(amigos) if amigos else "Sin amigos")

    def accion6():
        a = prompt("Persona A: ")
        b = prompt("Persona B: ")
        k = sg.delete_friendship(a, b)
        print(f"Relaciones eliminadas: {k}")

    def accion7():
        n = prompt("Nombre: ")
        rec = sg.recommend_by_city(n)
        print("Sugerencias:", ", ".join(rec) if rec else "Sin sugerencias")

    def accion8():
        n = prompt("Nombre: ")
        rec = sg.recommend_by_custom(n)
        print("Sugerencias:", ", ".join(rec) if rec else "Sin sugerencias")

    # Mapeo definitivo con las acciones que requieren lectura previa
    acciones["5"] = accion5
    acciones["6"] = accion6
    acciones["7"] = accion7
    acciones["8"] = accion8

    # Bucle principal
    try:
        while True:
            print(menu)
            op = prompt("Opción: ")
            if op == "0":
                break
            accion = acciones.get(op)
            if accion:
                accion()
            else:
                print("Opción inválida")
    finally:
        sg.close()

if __name__ == "__main__":
    main()
