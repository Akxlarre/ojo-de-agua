# 🌊 Ojo de Agua — Atlas & Copiloto de Inteligencia Hídrica de Chile

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Angular](https://img.shields.io/badge/Angular-20.3-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.0-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Tests Passing](https://img.shields.io/badge/Pytest-155%2F155%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Architecture](https://img.shields.io/badge/Architecture-DDD%20%2B%20Event%20Sourcing-blueviolet?style=for-the-badge)](#-arquitectura-del-sistema-domain-driven-design)
[![CI/CD](https://img.shields.io/badge/GitHub%20Actions-Automated%20Sync-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)](#-automatización-y-cicd)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**Gemelo Digital, Atlas Cartográfico Interactivo y Motor de Gobernanza Hídrica basado en Domain-Driven Design (DDD), Guardrails de Integridad Hidro-Legal y Grafo de Conocimiento Nacional para Chile.**

[Visión General](#-visión-general) •
[Características](#-características-principales) •
[Arquitectura DDD](#-arquitectura-del-sistema-domain-driven-design) •
[Fuentes Oficiales](#-fuentes-de-datos-del-estado-integradas) •
[Guía de Inicio](#-puesta-en-marcha-rápida) •
[API REST](#-api-rest-y-documentación-openapi) •
[Testing](#-suite-de-pruebas)

</div>

---

## 📖 Visión General

**Ojo de Agua** es una plataforma integral de gobernanza, auditoría telemétrica y modelación hidrográfica para la gestión del recurso hídrico en Chile. Desarrollada bajo los principios de **Domain-Driven Design (DDD)**, la plataforma formaliza el complejo marco normativo chileno (**Código de Aguas - D.F.L. 1.122 y Ley 21.435 de 2022**) junto con las dinámicas físicas, operativas e institucionales del país.

El sistema unifica a las **Organizaciones de Usuarios de Agua (OUA)** —Juntas de Vigilancia, Asociaciones de Canalistas y Comunidades de Aguas Subterráneas— con los organismos fiscalizadores del Estado (**DGA, SMA, SISS, TGR, CONAF, SERNAGEOMIN**), proporcionando un **gemelo digital** que permite simular prorrateos legales en periodos de sequía severa, auditar en tiempo real extracciones ilegales y navegar un atlas cartográfico 360° con más de 12 capas geoespaciales simultáneas.

---

## ✨ Características Principales

### ⚖️ 1. Motor de Prorrateo Legal Determinista (Ley 21.435)
- **Prioridad Absoluta al Consumo Humano (Art. 5 bis):** Reserva y abastecimiento garantizado de Sistemas Sanitarios Rurales (SSR / APR) previo a cualquier distribución consuntiva.
- **Redistribución por Caudales Críticos (Art. 18 & Art. 314):** Algoritmo de prorrateo proporcional por alícuotas o acciones de agua cuando el aforo del río no cubre el 100% de los DAA (Derechos de Aprovechamiento de Aguas).
- **Mapeo de Contextos:** Conversión bidireccional entre la métrica legal-estatal ($L/s$ o $m^3/s$) y la métrica de reparto tradicional de las OUAs (*acciones*, *tejas*, *regadores*).

### 🛡️ 2. Guardrails de Integridad Hidro-Legal
- **Ubiquitous Language Linter:** Asegura el uso estricto del lenguaje técnico-jurídico, bloqueando ambigüedades en contratos u órdenes de turno.
- **Hydraulic Guard (Conservación de Masa):** Invariante física que impide distribuciones físicamente imposibles ($Q_{\text{disponible}} \ge \sum Q_{\text{entregado}} + Q_{\text{pérdidas}}$).
- **Topological Guard (Flujo Gravitacional):** Valida la dirección natural aguas arriba $\to$ aguas abajo y la contención jerárquica estricta (Cuenca $\to$ Río $\to$ Sección $\to$ Bocatoma $\to$ Canal).
- **Illegal Extraction Guard (MEE vs Órdenes):** Cruza lecturas de sensores telemétricos de Monitoreo de Extracciones Efectivas (MEE) contra órdenes de turno activas y DAA registrados, disparando alertas por extracción no autorizada o sobreextracción.

### 🧠 3. Knowledge Graph & Búsqueda Híbrida
- **Grafo Semántico Consolidado:** Cientos de entidades interconectadas (90 cuencas DGA, 85 Juntas de Vigilancia, glaciares, centrales hidroeléctricas, relaves, plantas sanitarias).
- **Persistencia Dual:** Grafo en memoria optimizado para traversals relacionales y base relacional **SQLite** con soporte **FTS5** (Full-Text Search) y filtros geoespaciales.
- **Búsqueda Híbrida:** Recuperación unificada combinando coincidencia léxica BM25 y expansión topológica en el grafo.

### 🏛️ 4. Event Sourcing & Modelado Bitemporal
- **Event Sourcing & CQRS:** Bitácora inmutable de aforos de celadores y movimientos de compuertas con reproducción de estado temporal.
- **Bitemporalidad:** Distinción rigurosa entre **Tiempo Físico** (momento en que ocurrió el aforo o la entrega) y **Tiempo de Registro** (momento de inscripción en CBR o toma de razón DGA).

### 🗺️ 5. Visor Cartográfico & Copiloto AI
- **Atlas GIS Interactivo:** Renderizado con Leaflet / WebGL con capas conmutables de Cuencas, Glaciares (IPG 2022), Canales CIREN, Relaves SERNAGEOMIN, Humedales MMA, Estaciones BNA y Decretos de Escasez.
- **Ficha 360° Reactiva:** Diagnóstico integral de cuenca con scoring de estrés hídrico, vulnerabilidad de glaciares, sanciones ambientales y simulador de prorrateo embebido.
- **Copiloto AI:** Asistente conversacional especializado en normativa hídrica con respuestas en streaming (Server-Sent Events) y ejecución reactiva de acciones sobre la cámara cartográfica.

---

## 🏛️ Arquitectura del Sistema (Domain-Driven Design)

El proyecto sigue una arquitectura desacoplada en **Bounded Contexts** claramente delimitados:

```
rios/
├── src/
│   ├── api/                     # Capa de Interfaz REST (FastAPI)
│   │   ├── server.py            # Servidor HTTP, SSE Streaming, OpenAPI/Swagger
│   │   └── security.py          # OWASP Headers, API Key Auth, Rate Limiter
│   ├── core/                    # Núcleo de Dominio & Contratos Base
│   │   ├── base.py              # Entidades, Value Objects, Domain Events
│   │   ├── hooks.py             # Lifecycle Hooks de ejecución agéntica
│   │   └── ubiquitous.py        # Diccionario Oficial de Lenguaje Ubicuo
│   ├── domain/                  # Bounded Contexts de Negocio
│   │   ├── legal/               # Código de Aguas, DAA, Decretos Art. 314, Bitemporal
│   │   ├── oua/                 # Juntas de Vigilancia, Asociaciones, Context Translator
│   │   ├── physical/            # Cuencas, Ríos, Bocatomas, Geometrías GIS WGS84
│   │   ├── operation/           # Celadores, Órdenes de Turno, Prorrateo, TimeSeries
│   │   ├── topological/         # Relaciones cruzadas y conectividad hidrográfica
│   │   └── analytics/           # Diagnóstico Holístico de Cuencas y Búsqueda Híbrida
│   ├── guardrails/              # Barreras de Integridad y Validación
│   │   ├── ubiquitous_linter.py # Linter léxico de vocabulario de dominio
│   │   ├── hydraulic_guard.py   # Conservación de masa y pérdidas por conducción
│   │   ├── topological_guard.py # Flujo gravitacional e invariantes de red
│   │   └── illegal_extraction_guard.py # Cruce MEE vs derechos legales
│   ├── memory/                  # Capa de Persistencia
│   │   ├── graph.py             # Domain Knowledge Graph en memoria
│   │   └── sqlite_store.py      # Base SQLite con FTS5 y consultas espaciales
│   └── harness/                 # Pipelines de Ingestión Masiva y Orquestación
│       ├── batch_ingestion.py   # Pipeline ETL nacional unificado
│       ├── runner.py            # Orquestador del Harness (Hooks + Guardrails)
│       └── sync_pipeline.py     # Sincronización continua de fuentes estatales
├── frontend/                    # Single Page Application (Angular v20)
│   ├── src/app/
│   │   ├── core/                # Servicios de Dominio, Repositorios, Interceptores
│   │   ├── features/
│   │   │   └── water-platform/  # Plataforma Hídrica: Mapa GIS, Ficha 360°, Copiloto
│   │   └── shared/              # Prorrateo Simulator, Chat Bubbles, Selectores
│   └── package.json
├── data/                        # Repositorio de Catastros y Knowledge Graph
├── specs/                       # Spec-Driven Development (SDD: Specs, Planes, Roadmaps)
└── tests/                       # Suite de Pruebas Automatizadas (155 tests)
```

---

## 🏛️ Fuentes de Datos del Estado Integradas

El pipeline de ingesta procesa, normaliza y cruza información pública proveniente de más de **12 organismos oficiales**:

| Organismo | Insumo Integrado | Cobertura / Impacto |
|---|---|---|
| **DGA** | Red Hidrométrica BNA, Catastro de Cuencas, Decretos de Escasez (Art. 314) | 90 cuencas oficiales, estaciones telemétricas y decretos activos |
| **DGA - IPG** | Inventario Público de Glaciares 2022 | Reservas criosféricas y retroceso glaciar por cuenca |
| **CPA** | Catastro Público de Aguas (Derechos Concedidos) | Derechos de Aprovechamiento de Aguas (DAA consuntivos y no consuntivos) |
| **TGR** | Tesorería General de la República | Cobro de Patentes por No Uso del Agua (control de especulación) |
| **SMA** | Superintendencia del Medio Ambiente (SNIFA) | Procesos sancionatorios históricos y multas por infracciones hídricas |
| **SISS** | Superintendencia de Servicios Sanitarios | Plantas de Tratamiento de Aguas Servidas (PTAS) y puntos de descarga |
| **SERNAGEOMIN**| Catastro Nacional de Depósitos de Relaves | Relaves activos, inactivos y abandonados con riesgo de lixiviación |
| **MMA** | Ministerio del Medio Ambiente | Humedales Urbanos declarados bajo Ley 21.202 |
| **CONAF** | Áreas Silvestres Protegidas (SNASPE) e Incendios | Zonas de recarga en cabeceras de cuenca y afectación por fuego |
| **CNE** | Comisión Nacional de Energía | Centrales hidroeléctricas de pasada y de embalse |
| **CNR / CIREN** | Catastro Nacional de Riego y Red de Canales | Trazado de canales matrices troncales y demanda agrícola |
| **CR2 / CAMELS-CL** | Datos Hidroclimáticos de Cuencas de Chile | Series de tiempo de precipitación, evapotranspiración y temperatura |
| **ACADES** | Asociación Chilena de Desalación | Plantas desaladoras en operación y en evaluación ambiental |
| **DOH / Subdere** | Sistemas Sanitarios Rurales (SSR / APR) | Puntos de captación para consumo humano prioritario (Art. 5 bis) |

---

## 🚀 Puesta en Marcha Rápida

### Requisitos Previos
- **Python:** 3.11, 3.12 o 3.14
- **Node.js:** v20.x o superior
- **NPM:** v10.x o superior

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Akxlarre/ojo-de-agua.git
cd ojo-de-agua
```

### 2. Configurar el Backend (Python / FastAPI)
```bash
# Crear y activar entorno virtual
python -m venv .venv

# En Windows (PowerShell):
.venv\Scripts\Activate.ps1
# En Linux / macOS:
# source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor FastAPI
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload
```
- **API Swagger UI:** Visita [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **Visor Cartográfico Directo:** Visita [`http://127.0.0.1:8000/mapa`](http://127.0.0.1:8000/mapa)

### 3. Configurar el Frontend (Angular v20)
```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm start
```
- La aplicación web estará disponible en [`http://localhost:4200`](http://localhost:4200).

---

## 🌐 API REST y Documentación OpenAPI

La API REST expone más de **40 endpoints especializados**. A continuación se destacan los más relevantes:

### 💧 Catastro Hídrico y Cuencas
- `GET /api/cuencas`: Listado de las 90 cuencas hidrográficas oficiales DGA con metadatos.
- `GET /api/ouas`: Organizaciones de Usuarios de Agua registradas (Juntas de Vigilancia, Asociaciones).
- `GET /api/decretos-escasez`: Decretos de escasez hídrica vigentes dictados por el MOP.
- `GET /api/estaciones-bna`: Estaciones de la Red Hidrométrica Nacional con telemetría.

### ⚖️ Operación, Prorrateo & Auditoría
- `POST /api/prorrateo`: Simulación determinista de distribución legal de caudales (Art. 5 bis y 18).
- `POST /api/auditoria/extraccion`: Evaluación en tiempo real de extracciones telemétricas MEE vs derechos concedidos.
- `POST /api/telemetria/lote`: Ingesta masiva de aforos con validación de invariantes.
- `GET /api/telemetria/estacion/{id}/hidrograma`: Curva de caudal temporal para una estación.

### 📊 Diagnóstico Holístico & Búsqueda
- `GET /api/diagnostico/cuencas`: Diagnóstico multidimensional de salud hídrica para todas las cuencas.
- `GET /api/diagnostico/cuenca/{codigo_dga}`: Ficha 360° detallada (presión extractiva, sequía, glaciares, relaves, sanitarias).
- `GET /api/consulta/avanzada`: Búsqueda híbrida (FTS5 + Grafo) en el repositorio de conocimiento.
- `POST /api/chat/stream`: Endpoint de streaming SSE para el Copiloto AI con Generative UI.

---

## 🧪 Suite de Pruebas

El sistema cuenta con una exhaustiva batería de pruebas unitarias y de integración que verifican cada invariante del dominio hidro-legal:

```bash
python -m pytest -v
```

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2
collected 155 items

tests/test_api_server.py ...........                                      [  7%]
tests/test_batch_pipeline.py .                                           [  7%]
tests/test_bitemporal.py ..                                              [  9%]
tests/test_camels_and_ssr.py ....                                        [ 11%]
tests/test_canales_ciren.py .....                                        [ 15%]
tests/test_clima_analytics.py ....                                       [ 17%]
tests/test_cne_hidroelectricas.py ......                                 [ 21%]
tests/test_conaf_snaspe.py ......                                        [ 25%]
tests/test_context_mapping.py ..                                         [ 26%]
tests/test_cpa_derechos.py ......                                        [ 30%]
tests/test_cross_relations.py ..                                         [ 32%]
tests/test_desaladoras.py .....                                          [ 35%]
tests/test_dga_catastro_ingestion.py .                                   [ 35%]
tests/test_dga_connector.py ...                                          [ 37%]
tests/test_diagnostic_analytics.py ........                              [ 43%]
tests/test_domain_models.py ....                                         [ 45%]
tests/test_enterprise_improvements.py ...................                [ 57%]
tests/test_event_sourcing.py ..                                          [ 59%]
tests/test_extractor.py ..                                               [ 60%]
tests/test_gis_topological.py ....                                       [ 63%]
tests/test_glaciares.py .....                                            [ 66%]
tests/test_guardrails_and_harness.py ....                                [ 68%]
tests/test_illegal_extraction.py ...                                     [ 70%]
tests/test_mma_humedales.py ......                                       [ 74%]
tests/test_prorrateo_service.py ....                                     [ 77%]
tests/test_sernageomin_relaves.py ......                                 [ 81%]
tests/test_siss_sanitarias.py ......                                     [ 85%]
tests/test_sma_sanciones.py ......                                       [ 88%]
tests/test_sync_and_telemetry.py .....                                   [ 92%]
tests/test_tgr_patentes.py ...                                           [ 94%]
tests/test_tgr_patentes_ingestion.py ......                              [ 97%]
tests/test_wildfire_and_agriculture.py .....                             [100%]

============================ 155 passed in 49.15s =============================
```

---

## 🔄 Automatización y CI/CD

El repositorio incluye un flujo automatizado en **GitHub Actions** (`.github/workflows/water_intel_sync.yml`) configurado para:
1. **Ejecución Periódica Programada:** Cada lunes a las 06:00 UTC (03:00 hora de Chile).
2. **Validación Continua:** Ejecución completa de la suite de 155 tests unitarios e integración.
3. **Sincronización de Datos:** Descarga y normalización de nuevos decretos de escasez hídrica y aforos telemétricos.
4. **Auto-commit Controlado:** Actualización versionada de los datasets derivados (`knowledge_graph_chile.json`, `mapa_cuencas_chile.html`, `sync_report.json`).

---

## 🗺️ Roadmap de Desarrollo (SDD)

El proyecto sigue una metodología rigurosa de **Spec-Driven Development (SDD)**:

- [x] **Spec 0000:** Scaffolding Angular v20 + Koa Blueprint + Integración inicial FastAPI.
- [x] **Spec 0001:** Visor Cartográfico Limpio, Puente Bidireccional y Ficha 360° Reactiva con Prorrateo *(7/7 Criterios de Aceptación Aprobados)*.
- [ ] **Spec 0002:** Generative UI: Copiloto AI con manipulación reactiva de cámara y capas del mapa (*Planificada*).
- [ ] **Spec 0003:** Migración a visualizador cartográfico nativo WebGL (MapLibre GL / Leaflet Angular) a 60 FPS.
- [ ] **Spec 0004:** Slider Temporal Histórico de Megasequía y Retroceso Glaciar (2010–2026).
- [ ] **Spec 0005:** Generador Ejecutivo de Dictamen Técnico Institucional de Prorrateo en PDF.

---

## 📜 Licencia

Distribuido bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más información.

---

<div align="center">
Desarrollado con rigor técnico y compromiso por la seguridad hídrica de Chile. 🇨🇱
</div>
