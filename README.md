# miniredsocial
# 🧠 Mini Red Social con Neo4j (Python + Docker)

Este proyecto crea una **mini red social** usando **Neo4j** como base de datos de grafos y **Python** como interfaz de consola.  
Permite agregar personas, crear amistades bidireccionales y obtener recomendaciones de amigos por ciudad o por una propiedad personalizada.

---

## ⚙️ Requisitos previos

### 1. Instalar Docker
Descargá e instalá [Docker Desktop](https://www.docker.com/products/docker-desktop/).  
Verificá que funcione:
```powershell
docker --version
```

### 2. Instalar Python
1. Descargá desde [https://www.python.org/downloads/](https://www.python.org/downloads/)  
2. Durante la instalación, **tildá la opción “Add Python to PATH”** antes de presionar *Install Now*.
3. Verificá en PowerShell:
   ```powershell
   python --version
   pip --version
   ```

Si alguno no aparece, reiniciá PowerShell o reinstalá asegurándote de incluir el PATH.

---

## 🐳 Iniciar Neo4j con Docker

Ejecutá en PowerShell (una sola línea):

```powershell
docker run --name neo4j-social -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH="neo4j/contrasena123" -d neo4j:5
```

> ⚠️ **No uses `\` para continuar líneas** en PowerShell; si querés separar líneas, usá el acento invertido `` ` ``.

Verificá que esté corriendo:
```powershell
docker ps
```

Accedé desde tu navegador a:
> http://localhost:7474  
> Usuario: `neo4j`  
> Contraseña: `contrasena123`

---

## 🐍 Configurar el entorno de Python

1. Crear la carpeta del proyecto:
   ```powershell
   mkdir mini_red_social
   cd mini_red_social
   ```

2. Crear un entorno virtual (opcional pero recomendado):
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instalar la librería de Neo4j:
   ```powershell
   pip install neo4j
   ```

4. Crear el archivo principal:
   ```powershell
   notepad main.py
   ```
   Pegar el código completo del programa y guardar.

---

## ▶️ Ejecutar la aplicación

Ejecutá:
```powershell
python main.py
```

En el primer inicio, te pedirá una propiedad personalizada:
```
Propiedad personalizada para las personas (ej: profesion, hobby, edad):
```
Por ejemplo, escribí `profesion`.

Aparecerá el menú principal:

```
=== MINI RED SOCIAL ===
1. Agregar persona
2. Listar todas las personas
3. Buscar persona
4. Crear amistad
5. Ver amigos de una persona
6. Eliminar amistad
7. Recomendaciones por ciudad
8. Recomendaciones por profesion
9. Estadísticas
10. Eliminar persona
0. Salir
```

---

## 💡 Ejemplo de uso

```
1 → Agregar persona
Nombre: Ana
Ciudad: Córdoba
profesion: Ingeniera

1 → Agregar persona
Nombre: Juan
Ciudad: Córdoba
profesion: Abogado

4 → Crear amistad
Persona A: Ana
Persona B: Juan

5 → Ver amigos de una persona
Nombre: Ana
```

### Recomendaciones:
```
7 → Recomendaciones por ciudad
8 → Recomendaciones por profesion
```

---

## 🌐 Visualizar en Neo4j Browser

Abrí [http://localhost:7474](http://localhost:7474)  
Iniciá sesión con las credenciales y ejecutá:
```cypher
MATCH (p:Persona)-[r:AMIGO_DE]-(o) RETURN p, r, o
```
Verás el grafo con las personas y sus amistades.

---

## 🧹 Comandos útiles de Docker

Detener Neo4j:
```powershell
docker stop neo4j-social
```

Reiniciar:
```powershell
docker start neo4j-social
```

Eliminar contenedor:
```powershell
docker rm -f neo4j-social
```

Ver logs:
```powershell
docker logs neo4j-social --tail 50
```

---

## 🧠 Preguntas de análisis

**P1. ¿Por qué Neo4j en lugar de una base relacional?**  
Porque trata las relaciones como entidades de primer nivel. Las consultas de relaciones complejas son más simples y rápidas. En lugar de múltiples JOIN, se usan patrones (`()-[:AMIGO_DE]-()`) que se recorren con costo constante por salto.

**P2. Escalabilidad y rendimiento**  
- **Desafíos:** millones de nodos y alta conectividad generan fan-out y consumo de memoria.  
- **Optimización:**  
  1. Crear índices por `ciudad` y por la propiedad personalizada.  
  2. Usar proyecciones GDS (Graph Data Science) para precalcular recomendaciones.  
  3. Paginación con `LIMIT` y `ORDER BY`.  
  4. Uso de `MERGE` para evitar duplicados y relaciones redundantes.

---

## 🧩 Créditos
Proyecto educativo creado con **Python + Neo4j** para practicar:
- Teoría de grafos  
- Consultas Cypher  
- Control de integridad de relaciones  
- Recomendaciones basadas en similitudes  

---

## ✅ Resumen rápido de instalación

```bash
# 1. Levantar Neo4j
docker run --name neo4j-social -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH="neo4j/contrasena123" -d neo4j:5

# 2. Instalar dependencias
pip install neo4j

# 3. Ejecutar aplicación
python main.py
```

---

## 📂 Estructura del repositorio
```
mini_red_social/
│
├── main.py
├── README.md
└── venv/               # opcional
```

