from __future__ import annotations

from pathlib import Path

from simulation import (
    DEFAULT_ARRIVAL_PROFILE,
    SimulationConfig,
    evaluate_capacities,
    recommend_capacity,
    write_csv,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data"
REPORT = ROOT / "report"


def render_svg_chart(results: list[dict], best: dict, path: Path) -> None:
    width, height = 960, 520
    margin = 60
    plot_w = width - margin * 2
    plot_h = height - margin * 2

    servers = [r["servers"] for r in results]
    waits = [r["avg_wait_minutes"] for r in results]
    margins = [r["net_margin_usd"] for r in results]

    min_x, max_x = min(servers), max(servers)
    min_wait, max_wait = 0.0, max(waits) * 1.1
    min_margin, max_margin = min(margins) * 0.9, max(margins) * 1.1

    def x_map(x: float) -> float:
        return margin + (x - min_x) / (max_x - min_x) * plot_w

    def y_wait(v: float) -> float:
        return margin + plot_h - (v - min_wait) / (max_wait - min_wait) * plot_h

    def y_margin(v: float) -> float:
        return margin + plot_h - (v - min_margin) / (max_margin - min_margin) * plot_h

    wait_points = " ".join(f"{x_map(s):.1f},{y_wait(w):.1f}" for s, w in zip(servers, waits))
    margin_points = " ".join(f"{x_map(s):.1f},{y_margin(m):.1f}" for s, m in zip(servers, margins))

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-size="20" font-family="Arial">Capacidad vs espera vs ingresos netos</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#333"/>',
        f'<line x1="{width-margin}" y1="{margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>',
        f'<polyline fill="none" stroke="#d62728" stroke-width="3" points="{wait_points}"/>',
        f'<polyline fill="none" stroke="#1f77b4" stroke-width="3" points="{margin_points}"/>',
    ]

    for s in servers:
        x = x_map(s)
        lines.append(f'<text x="{x:.1f}" y="{height-margin+20}" text-anchor="middle" font-size="12">{s}</text>')

    bx = x_map(best["servers"])
    lines.append(f'<line x1="{bx:.1f}" y1="{margin}" x2="{bx:.1f}" y2="{height-margin}" stroke="#2ca02c" stroke-dasharray="5,5"/>')
    lines.append(
        f'<text x="{bx+8:.1f}" y="{margin+20}" font-size="12" fill="#2ca02c">Recomendado: {best["servers"]} cupos</text>'
    )
    lines.append('<text x="70" y="55" font-size="12" fill="#d62728">Espera promedio (min)</text>')
    lines.append('<text x="70" y="72" font-size="12" fill="#1f77b4">Margen neto (USD)</text>')
    lines.append('</svg>')

    path.write_text("\n".join(lines), encoding="utf-8")


def write_one_pager(best: dict, path: Path) -> None:
    content = f"""# Proyecto (1 página): Simulación de capacidad y colas

## Problema
Dimensionar cupos operativos para evitar esperas altas y rechazos sin perder margen.

## Solución
Simulación de eventos discretos con llegadas Poisson por hora y servicio exponencial.

## Dataset y modelo
- Perfil de llegadas: {DEFAULT_ARRIVAL_PROFILE}
- Media de servicio: 22 min
- Cola máxima: 12
- Precio por servicio: USD 18
- Costo por cupo/hora: USD 11.5

## Resultados
- Capacidad recomendada: **{best['servers']} cupos**
- Espera promedio: **{best['avg_wait_minutes']:.1f} min**
- Rechazo: **{best['rejection_rate']*100:.1f}%**
- Margen neto: **USD {best['net_margin_usd']:.0f}**

## Decisión
Con {best['servers']} cupos y precio de USD 18 se logra un equilibrio entre servicio y rentabilidad.
"""
    path.write_text(content, encoding="utf-8")


def build_outputs() -> tuple[list[dict], dict]:
    config = SimulationConfig()
    results = evaluate_capacities(range(2, 13), DEFAULT_ARRIVAL_PROFILE, config)
    best = recommend_capacity(results)

    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)

    write_csv(results, DATA / "capacity_scenarios.csv")
    render_svg_chart(results, best, OUT / "capacidad_vs_espera_vs_ingresos.svg")
    write_json(best, OUT / "recomendacion.json")
    write_one_pager(best, REPORT / "resumen_1_pagina.md")
    return results, best


if __name__ == "__main__":
    build_outputs()
