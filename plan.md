# Plan de mejoras — AI Grocery Planner

> Documento vivo. Cada item tiene un id (`M-NN`), prioridad, estado y notas de implementación. Las ideas del usuario están marcadas con `★`.

## Leyenda

- **Estado**: `pendiente` · `en curso` · `hecho` · `descartado`
- **Prioridad**: `alta` · `media` · `baja`
- **Esfuerzo**: `S` (< 1h) · `M` (1-3h) · `L` (3h+)

---

## Alta prioridad (UX, valor inmediato)

### M-01 · Cache persistente de productos por ingrediente  · `alta` · `M` · hecho
- Existe `config.PRODUCTS_CACHE` pero no se usa.
- Implementar lectura/escritura en `adapters/mercadona_cli.py::search()` con TTL configurable (default 7 días).
- Clave: término normalizado (lowercase, strip). Valor: lista de productos.
- En `search_view.py`, botón "Guardar selección" persiste el `product_id` elegido como match por defecto para ese término.
- **Hecho:** `adapters/mercadona_cli.py:24-95` (cache en memoria + disco, TTL 7d, `clear_cache()`, `is_cache_populated()`). `ui/search_view.py` botón "★ Guardar" → `data/default_matches.json`.

### M-02 · Feedback de progreso por pasos  · `alta` · `M` · hecho
- `recipe_view._worker` solo muestra "Generando…" → OK.
- Añadir estados: "pidiendo recetas a Gemini…" → "consolidando ingredientes…" → "buscando X/Y en Mercadona…" → "rellenando carrito…".
- Barra `CTkProgressBar` ligada a un `queue.Queue` que el worker va rellenando.
- **Hecho:** `ui/recipe_view.py` — `CTkProgressBar` + `queue.Queue`. Worker emite `_emit_progress(fraction, msg)` en 4 hitos; `_drain_progress()` procesa cada 80ms.

### M-03 · Editar/eliminar líneas del carrito  · `alta` · `M` · hecho
- `cart_view.py` solo permite exportar.
- Añadir botones `−` `+` y 🗑️ por fila, bind a `cart_engine.remove()` / `update_qty()` (probablemente hay que añadirlos al engine).
- Edit inline de cantidad con `CTkEntry` y validación numérica.
- **Hecho:** `ui/cart_view.py` — botones `−`/`+`/🗑 + `CTkEntry` inline (Enter/FocusOut). `core/cart_engine.py:31-46` — `add()` consolida por id, `update_qty()` con redondeo, qty≤0 elimina.

### M-04 · Historial de prompts  · `alta` · `S` · hecho
- Dropdown en `recipe_view` con las últimas 10 peticiones.
- Persistir en `data/prompt_history.json`.
- **Hecho:** `core/prompt_history.py` (JSON, dedupe case-insensitive, mover al frente, máx 10). `ui/recipe_view.py` — dropdown + botón "Limpiar".

### M-05 · Precio estimado en vivo  · `alta` · `M` · hecho
- Durante el matching, actualizar `self.cart.total()` en una label del header de la sidebar.
- **Hecho:** `ui/dashboard.py:69-84` — bloque destacado "Total estimado" (24pt bold) en sidebar. `_on_cart_updated` actualiza tras cada `cart.add` (item por item en el worker, así el total crece en vivo).

### M-06 · Pestaña "Pantry" (ya tengo en casa) ★  · `alta` · `M` · hecho
- Nueva vista `ui/pantry_view.py`.
- Lista editable de ingredientes que el usuario ya tiene (ej: "arroz, aceite, sal").
- Al consolidar la lista de la compra, **restar** lo que ya esté en el pantry antes de buscar en Mercadona.
- Persistencia en `data/pantry.json`.
- API: `pantry.contains(term: str) -> bool` con matching difuso (rapidfuzz, threshold 85).
- El carrito solo se llena con lo que NO esté en el pantry.
- **Hecho:** `core/user_lists.PantryStore` (fuzzy rapidfuzz/difflib, threshold 85, persistido). `ui/pantry_view.py` con `ui/simple_list_view.py` reutilizable. Integrado en `recipe_view._worker` — `pantry.filter_out()` antes del matching.

### M-07 · Pestaña "Avoid" (no quiero comprar) ★  · `alta` · `M` · hecho
- Nueva vista `ui/avoid_view.py`.
- Lista de términos/ingredientes a excluir (ej: "marisco", "frutos secos", "perejil").
- Filtro previo al matching: si un ingrediente matchea con algo del avoid list, se descarta y se pasa al siguiente candidato o se reporta al usuario.
- Persistencia en `data/avoid.json`.
- UI: input + lista con 🗑️ por fila, igual que pantry.
- **Hecho:** `core/user_lists.AvoidStore` (misma API). `ui/avoid_view.py` con `simple_list_view`. Filtrado previo al matching; los saltados se reportan en la UI como "🚫 Saltados (en avoid)".

---

## Media (calidad del resultado)

### M-08 · Embeddings Gemini para matching semántico  · `media` · `L` · hecho
- Sustituir fuzzy matching por cosine similarity sobre `text-embedding-004`.
- Índice local en `data/embeddings.npz` (término → vector + ids de productos cacheados).
- "tomate" → "tomate triturado Hacendado" sin reglas manuales.
- **Hecho:** `core/semantic_matcher.py` — embeddings `text-embedding-004`, índice `data/embeddings.npz` (término → vector + ts, TTL 7d), cosine contra nombres de hits cacheados, umbral 0.55. `core/product_matcher.py` — pipeline 4 niveles (search → semantic → fuzzy → fallback) con `match_kind` en el resultado. `requirements.txt` añade `numpy`.

### M-09 · Reintentos con backoff exponencial en Gemini  · `media` · `S` · hecho
- En `core/gemini_client._call`, capturar HTTP 429/503 y reintentar 3 veces con `sleep(2**attempt)`.
- Loggear cada reintento.
- **Hecho:** `core/gemini_client.py:42-87` — 3 intentos con backoff 1s/2s/4s para 429/500/502/503/504 y `RequestException`. `logger.warning` por intento.

### M-10 · Validación de JSON de Gemini con esquema  · `media` · `M` · hecho
- `_extract_json` usa regex; frágil.
- Definir `Recipe = {title, servings, ingredients: [{name, qty, unit}], steps: [str]}` con `pydantic` o `dataclasses`.
- Si Gemini devuelve algo que no encaja, reintentar una vez con prompt de corrección.
- **Hecho:** `core/recipe_schema.py` — `Ingredient`, `Recipe`, `MealPlan`, `ShoppingItem`, `ShoppingList` con `from_dict()` que valida tipos y normaliza (meal a `comida|cena`, exige claves `days`/`shopping_list`). `core/recipe_engine.py:107-135` reintenta una vez con `_CORRECTION_SYSTEM` si la validación falla.

### M-11 · Refinar cantidad en el carrito  · `media` · `M` · hecho
- Gemini devuelve "200g de arroz" pero el carrito suma 1 unidad.
- `cart_engine.add(product, quantity, unit)`: consolidar por `product_id` y sumar cantidades.
- Si Gemini dice "1 cebolla" en 3 recetas → 3 unidades de cebolla, no 3 líneas.
- **Hecho:** `core/quantity.py` — parser `200g`, `1.5 kg`, `3 unidades` → float (g/ml/ud). `core/cart_engine.py` ya consolidaba por `product_id`; ahora se le pasa la cantidad real parseada desde `recipe_view._worker`.

### M-12 · Filtros dietéticos  · `media` · `S` · hecho
- Checkboxes en `recipe_view`: vegetariano / vegano / sin gluten / sin lactosa / bajo en sodio.
- Se prependen al prompt como restricciones explícitas.
- **Hecho:** `core/recipe_engine.py:26-32` `DIETARY_RESTRICTIONS` (5 dietas con descripciones). `_dietary_block()` las inyecta. 5 checkboxes en `ui/recipe_view.py:62-71`; `generate_meal_plan(restrictions=...)` propaga.

---

## Baja (polish / infra)

### M-13 · Tests unitarios  · `baja` · `M` · hecho
- Cero cobertura actual. Priorizar:
  - `core/cart_engine.py` (sumas, dedupe, export)
  - `core/product_matcher.py` (fuzzy, sin resultados)
  - `adapters/mercadona_cli.py` (mockear subprocess, fixtures JSON)
- Framework: `pytest`. Fixture con respuestas reales del CLI en `tests/fixtures/`.
- **Hecho:** 98 tests pasando en 11 archivos (`pytest.ini` + `tests/conftest.py` con `tmp_data_dir` que redirige `config.DATA_DIR` por test, `requirements-dev.txt` con `pytest`). Cubre: cart_engine, product_matcher, mercadona_cli, quantity, user_lists, prompt_history, recipe_exporter, recipe_engine, recipe_schema, semantic_matcher, settings_store, to_csv.

### M-14 · Settings panel en la UI  · `baja` · `M` · hecho
- Temperatura, modelo, warehouse editables desde un diálogo (hoy solo env vars).
- Guardar en `data/settings.json` con override sobre env.
- **Hecho:** `core/settings_store.py` (env > settings.json > defaults, filtra secretos al guardar). `ui/settings_dialog.py` (`CTkToplevel` modal con validación temp 0-2, max_eur ≥ 0). Botón ⚙ en la sidebar.

### M-15 · Log a fichero  · `baja` · `S` · hecho
- `data/app.log` con `RotatingFileHandler` (1MB × 3 backups).
- Reemplazar prints/stderr por `logger.info/warning/error`.
- **Hecho:** `core/logging_setup.py` con `RotatingFileHandler` 1MB×3 + consola solo WARNING+. `main.py` lo arranca. `mercadona_cli` ahora usa `logger.warning` en vez de fallar silencioso.

### M-16 · Empaquetado con PyInstaller  · `baja` · `L` · hecho
- `pyinstaller --noconsole --onefile main.py` → `dist/AI Grocery Planner.exe`.
- Incluir `mercadona-cli` como dependencia documentada (sigue requiriendo Node + npm install -g).
- **Hecho:** `build.bat` (Windows) y `build.sh` (Linux/macOS) con `pyinstaller --noconsole --onefile --name "AI Grocery Planner" main.py`. mercadona-cli sigue requiriéndose aparte.

### M-17 · Tema claro/oscuro toggle  · `baja` · `S` · hecho
- `customtkinter.set_appearance_mode("dark"/"light")` + switch en la sidebar.
- **Hecho:** `CTkSwitch` "Tema claro" en la sidebar. Sincronizado con `settings_store.appearance_mode` y el settings dialog.

### M-18 · Exportar carrito a CSV  · `baja` · `S` · hecho
- Además de `basket.txt`, botón "Exportar CSV" → `basket.csv` con columnas `id,producto,cantidad,precio_unit,subtotal`.
- **Hecho:** `cart_engine.to_csv()` con cabecera y quoting. Botón "Exportar CSV" en `ui/cart_view.py` con `filedialog`.

### M-19 · Linter + formatter  · `baja` · `S` · hecho
- Añadir `ruff` y `black` a `requirements-dev.txt`.
- `pyproject.toml` con config mínima (line-length=100, target=py310).
- **Hecho:** `pyproject.toml` con ruff (E,F,W,I,B,UP, line-length=100, py310) y black. `requirements-dev.txt` añade `ruff` y `black`.

### M-20 · .gitignore + init git  · `baja` · `S` · hecho
- `__pycache__/`, `data/cache.db`, `data/*.log`, `.venv/`, `.env`.
- Repo aún no inicializado.
- **Hecho:** `.gitignore` ya existía del initial commit; ampliado con `data/*.json`, `data/*.npz`. Repo inicializado y 6 commits pusheados a `origin/main` (1 initial + 5 features por sesión).

---

## Roadmap sugerido

| Sesión | Items | Por qué | Estado |
|--------|-------|---------|--------|
| 1 | M-01, M-09, M-06, M-07 | Reduce 429, hace la app usable en repetidas peticiones, y mete los filtros nuevos (pantry/avoid) que son el diferenciador. | ✅ hecho (commit 17682eb) |
| 2 | M-03, M-11, M-13 + EX-1 | Sube calidad percibida (editar carrito, cantidades reales) y blinda regresiones con tests. | ✅ hecho (commit 6ddb5f6) |
| 3 | M-02, M-04, M-05 | Polish de UX: progreso, historial, precio en vivo. | ✅ hecho (commit c2b4803) |
| 4 | M-08, M-10, M-12 | Matching y parsing de Gemini más robustos. | ✅ hecho (commit c8da3ea) |
| 5 | M-14 → M-20 | Infra, settings, packaging. | ✅ hecho (commit cbdf033) |

**Plan completo: 20/20 items hechos + 1 extra.** Ver `git log` para el detalle por sesión.

## Resumen de la app

```
ai-grocery-planner/
├── main.py
├── config.py
├── pyproject.toml              ← ruff + black
├── pytest.ini
├── requirements.txt            ← customtkinter, requests, rapidfuzz, numpy
├── requirements-dev.txt        ← + pytest, ruff, black
├── build.bat / build.sh        ← PyInstaller
├── adapters/
│   └── mercadona_cli.py        ← wrapper CLI + cache TTL 7d
├── core/
│   ├── cart_engine.py          ← Cart, to_basket, to_csv
│   ├── gemini_client.py        ← REST + retries exponencial
│   ├── logging_setup.py        ← RotatingFileHandler
│   ├── product_matcher.py      ← semantic → fuzzy → fallback
│   ├── prompt_history.py       ← últimas 10 con dedupe
│   ├── quantity.py             ← parser 200g / 1.5kg / 3 unidades
│   ├── recipe_engine.py        ← plan + shopping + dietary
│   ├── recipe_exporter.py      ← plan → Markdown
│   ├── recipe_schema.py        ← dataclasses + from_dict validation
│   ├── semantic_matcher.py     ← embeddings Gemini + npz
│   ├── settings_store.py       ← env > json > defaults
│   └── user_lists.py           ← PantryStore, AvoidStore
├── ui/
│   ├── avoid_view.py
│   ├── cart_view.py            ← edición inline, export txt + csv
│   ├── dashboard.py            ← shell + sidebar + tema + precio en vivo
│   ├── pantry_view.py
│   ├── recipe_view.py          ← generación + progreso + historial + dieta + MD
│   ├── search_view.py          ← búsqueda + "★ Guardar" match por defecto
│   ├── settings_dialog.py
│   └── simple_list_view.py     ← base para pantry/avoid
├── tests/                      ← 98 tests
└── data/                       ← cache, settings, history, embeddings (gitignored)
```

---

## Extras (no estaban en el plan original)

### EX-1 · Exportar recetas a Markdown  · `alta` · `S` · hecho ★
- Tras recibir recetas de Gemini, el usuario puede descargar un `.md` con todas las recetas (título, prompt original, descripción, ingredientes con cantidad, pasos numerados).
- **Hecho:** `core/recipe_exporter.py::render_recipes_markdown()`. Botón "📄 Exportar recetas (.md)" en `ui/recipe_view.py:60-71` (deshabilitado hasta generar un plan).

---

## Ideas descartadas / descartables

- **M-08 con `pydantic`** → se implementó con `dataclasses` (más ligero, sin dependencia extra). Si el proyecto crece y aparecen validadores complejos, se puede migrar.
- **M-13 con fixtures reales del CLI en `tests/fixtures/`** → no se hizo (los tests mockean subprocess; con el CLI real, los tests serían lentos y flaky). Si en el futuro se necesita regresión contra respuestas reales, se pueden añadir fixtures puntuales.
