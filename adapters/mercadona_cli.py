"""
Wrapper Python del CLI mercadona (https://github.com/ivorpad/mercadona-cli).

Permite usar el CLI como si fuera una API local: search, product,
categories, batch, total. Todo devuelve dicts / listas de dicts.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import config


class MercadonaCLIError(Exception):
    pass


def _resolve_cmd(extra_args: list[str]) -> list[str]:
    """
    Devuelve la línea de comando completa para invocar el CLI.

    En Windows, npm instala `mercadona` como un script `.ps1` que NO se
    puede ejecutar directamente con subprocess (WinError 2). Hay que
    envolverlo con powershell.exe.
    """
    cli = config.MERCADONA_CLI
    path = shutil.which(cli)
    if path is None and Path(cli).exists():
        path = str(Path(cli).resolve())
    if path is None:
        raise MercadonaCLIError(
            f"No se encuentra el binario '{cli}'. "
            "Instálalo con: npm install -g @ivorpad/mercadona"
        )

    if sys.platform == "win32" and path.lower().endswith((".ps1", ".cmd", ".bat")):
        if path.lower().endswith(".ps1"):
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", path,
                *extra_args,
            ]
        # .cmd / .bat → cmd.exe
        return ["cmd.exe", "/c", path, *extra_args]

    return [path, *extra_args]


def _run(args: list[str], timeout: int = 60, stdin_data: str | None = None) -> dict[str, Any] | list[Any] | str:
    """Ejecuta el CLI con los args dados y devuelve el stdout parseado."""
    full_args = [*args, "--json", "--wh", config.MERCADONA_WAREHOUSE]
    cmd = _resolve_cmd(full_args)
    result = subprocess.run(
        cmd, input=stdin_data, capture_output=True, text=True, timeout=timeout
    )

    if result.returncode != 0:
        raise MercadonaCLIError(
            f"mercadona CLI falló ({' '.join(cmd)}): {result.stderr.strip() or result.stdout.strip()}"
        )

    out = result.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def search(query: str, limit: int = 5, fresh: bool = False) -> list[dict[str, Any]]:
    """Busca productos por nombre. Devuelve lista de productos."""
    args = ["search", query, "--limit", str(limit)]
    if fresh:
        args.append("--fresh")
    data = _run(args)
    if isinstance(data, dict):
        return data.get("hits", data.get("products", []))
    if isinstance(data, list):
        return data
    return []


def product(product_id: int | str) -> dict[str, Any]:
    """Detalle completo de un producto por id."""
    data = _run(["product", str(product_id)])
    return data if isinstance(data, dict) else {}


def categories(category_id: int | str | None = None) -> Any:
    """Lista categorías o productos de una categoría."""
    args = ["categories"]
    if category_id is not None:
        args += ["--id", str(category_id)]
    return _run(args)


def batch(terms: list[str]) -> list[dict[str, Any]]:
    """Resuelve muchos términos en una sola petición."""
    if not terms:
        return []
    input_data = "\n".join(terms)
    cmd = _resolve_cmd(["batch", "-f", "-"])
    result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise MercadonaCLIError(f"batch falló: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            return data.get("results", data.get("lines", []))
        return data
    except json.JSONDecodeError:
        return []


def total(basket: list[tuple[int | str, float]]) -> dict[str, Any]:
    """Calcula el precio total de una cesta [(product_id, qty), ...]."""
    lines = [f"{pid} {qty}" for pid, qty in basket]
    input_data = "\n".join(lines)
    cmd = _resolve_cmd(["total", "-f", "-"])
    result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise MercadonaCLIError(f"total falló: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def whoami() -> dict[str, Any]:
    """Comprueba si hay sesión autenticada (necesaria para cart/checkout)."""
    cmd = _resolve_cmd(["whoami"])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode}


def is_available() -> bool:
    """True si el binario mercadona está en PATH o en la ruta configurada."""
    return shutil.which(config.MERCADONA_CLI) is not None or Path(config.MERCADONA_CLI).exists()
