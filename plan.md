# Plan de mejoras — AI Grocery Planner

> Documento vivo. Cada item tiene un id (`M-NN`), prioridad, estado y notas de implementación. Las ideas del usuario están marcadas con `★`.

## Leyenda

- **Estado**: `pendiente` · `en curso` · `hecho` · `descartado`
- **Prioridad**: `alta` · `media` · `baja`
- **Esfuerzo**: `S` (< 1h) · `M` (1-3h) · `L` (3h+)

---

## Alta prioridad (UX, valor inmediato)

### M-01 · Cache persistente de productos por ingrediente  · `alta` · `M` · pendiente
- Existe `config.PRODUCTS_CACHE` pero no se usa.
- Implementar lectura/escritura en `adapters/mercadona_cli.py::search()` con TTL configurable (default 7 días).
- Clave: término normalizado (lowercase, strip). Valor: lista de productos.
- En `search_view.py`, botón "Guardar selección" persiste el `product_id` elegido como match por defecto para ese término.

### M-02 · Feedback de progreso por pasos  · `alta` · `M` · pendiente
- `recipe_view._worker` solo muestra "Generando…" → OK.
- Añadir estados: "pidiendo recetas a Gemini…" → "consolidando ingredientes…" → "buscando X/Y en Mercadona…" → "rellenando carrito…".
- Barra `CTkProgressBar` ligada a un `queue.Queue` que el worker va rellenando.

### M-03 · Editar/eliminar líneas del carrito  · `alta` · `M` · pendiente
- `cart_view.py` solo permite exportar.
- Añadir botones `−` `+` y 🗑️ por fila, bind a `cart_engine.remove()` / `update_qty()` (probablemente hay que añadirlos al engine).
- Edit inline de cantidad con `CTkEntry` y validación numérica.

### M-04 · Historial de prompts  · `alta` · `S` · pendiente
- Dropdown en `recipe_view` con las últimas 10 peticiones.
- Persistir en `data/prompt_history.json`.

### M-05 · Precio estimado en vivo  · `alta` · `M` · pendiente
- Durante el matching, actualizar `self.cart.total()` en una label del header de la sidebar.

### M-06 · Pestaña "Pantry" (ya tengo en casa) ★  · `alta` · `M` · pendiente
- Nueva vista `ui/pantry_view.py`.
- Lista editable de ingredientes que el usuario ya tiene (ej: "arroz, aceite, sal").
- Al consolidar la lista de la compra, **restar** lo que ya esté en el pantry antes de buscar en Mercadona.
- Persistencia en `data/pantry.json`.
- API: `pantry.contains(term: str) -> bool` con matching difuso (rapidfuzz, threshold 85).
- El carrito solo se llena con lo que NO esté en el pantry.

### M-07 · Pestaña "Avoid" (no quiero comprar) ★  · `alta` · `M` · pendiente
- Nueva vista `ui/avoid_view.py`.
- Lista de términos/ingredientes a excluir (ej: "marisco", "frutos secos", "perejil").
- Filtro previo al matching: si un ingrediente matchea con algo del avoid list, se descarta y se pasa al siguiente candidato o se reporta al usuario.
- Persistencia en `data/avoid.json`.
- UI: input + lista con 🗑️ por fila, igual que pantry.

---

## Media (calidad del resultado)

### M-08 · Embeddings Gemini para matching semántico  · `media` · `L` · pendiente
- Sustituir fuzzy matching por cosine similarity sobre `text-embedding-004`.
- Índice local en `data/embeddings.npz` (término → vector + ids de productos cacheados).
- "tomate" → "tomate triturado Hacendado" sin reglas manuales.

### M-09 · Reintentos con backoff exponencial en Gemini  · `media` · `S` · pendiente
- En `core/gemini_client._call`, capturar HTTP 429/503 y reintentar 3 veces con `sleep(2**attempt)`.
- Loggear cada reintento.

### M-10 · Validación de JSON de Gemini con esquema  · `media` · `M` · pendiente
- `_extract_json` usa regex; frágil.
- Definir `Recipe = {title, servings, ingredients: [{name, qty, unit}], steps: [str]}` con `pydantic` o `dataclasses`.
- Si Gemini devuelve algo que no encaja, reintentar una vez con prompt de corrección.

### M-11 · Refinar cantidad en el carrito  · `media` · `M` · pendiente
- Gemini devuelve "200g de arroz" pero el carrito suma 1 unidad.
- `cart_engine.add(product, quantity, unit)`: consolidar por `product_id` y sumar cantidades.
- Si Gemini dice "1 cebolla" en 3 recetas → 3 unidades de cebolla, no 3 líneas.

### M-12 · Filtros dietéticos  · `media` · `S` · pendiente
- Checkboxes en `recipe_view`: vegetariano / vegano / sin gluten / sin lactosa / bajo en sodio.
- Se prependen al prompt como restricciones explícitas.

---

## Baja (polish / infra)

### M-13 · Tests unitarios  · `baja` · `M` · pendiente
- Cero cobertura actual. Priorizar:
  - `core/cart_engine.py` (sumas, dedupe, export)
  - `core/product_matcher.py` (fuzzy, sin resultados)
  - `adapters/mercadona_cli.py` (mockear subprocess, fixtures JSON)
- Framework: `pytest`. Fixture con respuestas reales del CLI en `tests/fixtures/`.

### M-14 · Settings panel en la UI  · `baja` · `M` · pendiente
- Temperatura, modelo, warehouse editables desde un diálogo (hoy solo env vars).
- Guardar en `data/settings.json` con override sobre env.

### M-15 · Log a fichero  · `baja` · `S` · pendiente
- `data/app.log` con `RotatingFileHandler` (1MB × 3 backups).
- Reemplazar prints/stderr por `logger.info/warning/error`.

### M-16 · Empaquetado con PyInstaller  · `baja` · `L` · pendiente
- `pyinstaller --noconsole --onefile main.py` → `dist/AI Grocery Planner.exe`.
- Incluir `mercadona-cli` como dependencia documentada (sigue requiriendo Node + npm install -g).

### M-17 · Tema claro/oscuro toggle  · `baja` · `S` · pendiente
- `customtkinter.set_appearance_mode("dark"/"light")` + switch en la sidebar.

### M-18 · Exportar carrito a CSV  · `baja` · `S` · pendiente
- Además de `basket.txt`, botón "Exportar CSV" → `basket.csv` con columnas `id,producto,cantidad,precio_unit,subtotal`.

### M-19 · Linter + formatter  · `baja` · `S` · pendiente
- Añadir `ruff` y `black` a `requirements-dev.txt`.
- `pyproject.toml` con config mínima (line-length=100, target=py310).

### M-20 · .gitignore + init git  · `baja` · `S` · pendiente
- `__pycache__/`, `data/cache.db`, `data/*.log`, `.venv/`, `.env`.
- Repo aún no inicializado.

---

## Roadmap sugerido

| Sesión | Items | Por qué |
|--------|-------|---------|
| 1 | M-01, M-09, M-06, M-07 | Reduce 429, hace la app usable en repetidas peticiones, y mete los filtros nuevos (pantry/avoid) que son el diferenciador. |
| 2 | M-03, M-11, M-13 | Sube calidad percibida (editar carrito, cantidades reales) y blinda regresiones con tests. |
| 3 | M-02, M-04, M-05 | Polish de UX: progreso, historial, precio en vivo. |
| 4 | M-08, M-10, M-12 | Matching y parsing de Gemini más robustos. |
| 5 | M-14 → M-20 | Infra, settings, packaging. |

---

## Ideas descartadas / descartables

_(Se irán moviendo aquí conforme se descarten o se implemente otra cosa.)_
