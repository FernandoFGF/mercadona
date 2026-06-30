# AI Grocery Planner

App de escritorio (CustomTkinter) que combina **Gemini** (recetas) + **mercadona-cli** (productos reales) para generar menús y carritos de Mercadona a partir de peticiones en lenguaje natural.

> Pídele cosas como: *"algo sano, bajo en colesterol"*, *"menú de 5 días bajo en calorías"*, *"cena vegetariana rápida"*. Gemini devuelve recetas estructuradas, se buscan los ingredientes reales en Mercadona y se monta un carrito con precios.

## Arquitectura

```
app/
├── main.py
├── config.py                 ← env vars, paths, defaults
├── ui/
│   ├── dashboard.py          ← shell con sidebar
│   ├── recipe_view.py        ← generación de recetas con Gemini
│   ├── cart_view.py          ← carrito + export basket.txt
│   └── search_view.py        ← búsqueda manual de productos
├── core/
│   ├── gemini_client.py      ← wrapper Google Gemini (REST)
│   ├── recipe_engine.py      ← plan de recetas + lista consolidada
│   ├── product_matcher.py    ← ingrediente → producto real
│   └── cart_engine.py        ← carrito, totales, export
├── adapters/
│   └── mercadona_cli.py      ← wrapper del CLI de ivorpad/mercadona-cli
└── data/
    ├── cache.db
    └── products_cache.json
```

## Requisitos

- Python 3.10+
- [mercadona-cli](https://github.com/ivorpad/mercadona-cli) en PATH (o configurar `MERCADONA_CLI_PATH`):
  ```bash
  npm install -g @ivorpad/mercadona
  ```
  Comprueba con `mercadona search arroz`.

## Instalación

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="tu-clave-de-google-ai-studio"   # o setx en Windows
python main.py
```

Variables de entorno opcionales:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | **obligatoria** |
| `GEMINI_MODEL` | `gemini-2.0-flash` | modelo de Gemini |
| `MERCADONA_CLI_PATH` | `mercadona` | ruta al binario |
| `MERCADONA_WAREHOUSE` | `mad1` | almacén (precios e ids varían) |
| `MERCADONA_MAX_EUR` | `0` | tope de gasto (0 = sin tope) |

## Uso

1. **Recipe Generator** → escribe una petición (`"algo sano bajo en colesterol"`), elige días y raciones, dale a *Generar*. Gemini propone recetas, se buscan los ingredientes en Mercadona y se añaden al carrito.
2. **Cart** → revisa productos y precios, exporta `basket.txt`. Después, en la terminal:
   ```bash
   mercadona total -f basket.txt            # precio total real
   mercadona cart set-many -f basket.txt    # volcarlo al carrito de Mercadona
   ```
   (Para el checkout de verdad necesitas `mercadona import-har` una vez.)
3. **Product Search** → busca cualquier producto a mano y añádelo al carrito.

## Cómo funciona el flujo

```
petición libre
   ↓ Gemini → recetas estructuradas (días / ingredientes)
   ↓ Gemini → lista de la compra consolidada
   ↓ mercadona-cli search por cada ingrediente
   ↓ product_matcher (fuzzy: rapidfuzz o difflib)
   ↓ cart_engine (dedupe, subtotal, total)
   ↓ UI
```

## Limitaciones

- La API de Mercadona **no es oficial**: puede caerse. Para uso personal es estable.
- El matching ingrediente → producto es fuzzy; los nombres muy ambiguos (`"tomate"`) conviene refinarlos a `"tomate triturado Hacendado"`.
- El checkout real (`mercadona checkout submit`) **no** se automatiza desde la app; se exporta la cesta y se opera desde el CLI (más seguro, con `--max` como red de seguridad).

## Mejoras futuras

- Embeddings Gemini para matching semántico (fase 2).
- Menú semanal con reutilización de ingredientes (p.ej. pollo que sirve para 2 recetas).
- Estimación nutricional por receta.
- Caché local de productos con TTL.
