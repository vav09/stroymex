"""
pkps_plots.py — эпюры по результатам расчёта (matplotlib).

Все функции возвращают matplotlib.figure.Figure; Streamlit показывает их через
st.pyplot, а в скриптах их можно сохранить через fig.savefig("name.png", dpi=200).
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np
from matplotlib.figure import Figure

ACCENT = "#1f5f8b"      # основная линия
ACCENT_SOFT = "#cfe0ee"
SECOND = "#b5483a"      # вторая линия (для Mр)
GRID = "#d9d9d9"
TEXT = "#222222"


def _num(v: float) -> str:
    """12345.6 -> '12 346' (неразрывный пробел между тысячами)."""
    return f"{v:,.0f}".replace(",", "\u00a0")


def _style(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_title(title, fontsize=12, loc="left", color=TEXT)
    ax.set_xlabel(xlabel, color=TEXT)
    ax.set_ylabel(ylabel, color=TEXT)
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_xlim(0, 1)
    ax.axhline(0, color="#555555", linewidth=0.9)
    ax.tick_params(colors=TEXT)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _length_axis(ax, L: float) -> None:
    """Вторая шкала сверху — в метрах."""
    sec = ax.secondary_xaxis("top", functions=(lambda v: v * L, lambda m: m / L))
    sec.set_xlabel("м по длине судна", color=TEXT, fontsize=9)
    sec.tick_params(colors=TEXT, labelsize=8)


def fig_moment(x: np.ndarray, M: np.ndarray, L: float, Mdv: float,
               plateau: float, basin_label: str) -> Figure:
    """Эпюра Mдв (±) по длине судна."""
    fig = Figure(figsize=(8, 3.8), dpi=110)
    ax = fig.subplots()
    ax.fill_between(x, M, -M, color=ACCENT_SOFT, alpha=0.9)
    ax.plot(x, M, color=ACCENT, linewidth=2.0)
    ax.plot(x, -M, color=ACCENT, linewidth=2.0)
    edge = (1 - plateau) / 2
    ax.annotate(f"±{_num(Mdv)} кН·м",
                xy=(0.5, Mdv), xytext=(0.5, Mdv * 1.12), ha="center",
                fontsize=10, color=TEXT)
    ax.set_ylim(-Mdv * 1.3, Mdv * 1.3)
    for xv in (edge, 1 - edge):
        ax.axvline(xv, color="#888888", linestyle=":", linewidth=1)
    _style(ax, "x / L", "Mдв, кН·м",
           f"Эпюра дополнительного волнового момента, класс «{basin_label}»")
    ax.text(0.5, -Mdv * 1.22, f"постоянный участок {plateau:.2f}L",
            ha="center", fontsize=8, color="#555555")
    _length_axis(ax, L)
    fig.tight_layout()
    return fig


def fig_shear(x: np.ndarray, N: np.ndarray, L: float, Ndv: float) -> Figure:
    """Эпюра Nдв (±) по рис. 2.2.10."""
    fig = Figure(figsize=(8, 3.8), dpi=110)
    ax = fig.subplots()
    ax.fill_between(x, N, -N, color=ACCENT_SOFT, alpha=0.9)
    ax.plot(x, N, color=ACCENT, linewidth=2.0)
    ax.plot(x, -N, color=ACCENT, linewidth=2.0)
    ax.annotate(f"±{_num(Ndv)} кН",
                xy=(0.22, Ndv), xytext=(0.22, Ndv * 1.12), ha="center",
                fontsize=10, color=TEXT)
    ax.annotate(f"0,7·Nдв = {_num(0.7 * Ndv)} кН",
                xy=(0.5, 0.7 * Ndv), xytext=(0.5, 0.7 * Ndv * 1.12), ha="center",
                fontsize=9, color=TEXT)
    ax.set_ylim(-Ndv * 1.3, Ndv * 1.3)
    _style(ax, "x / L", "Nдв, кН",
           "Эпюра дополнительной волновой перерезывающей силы (рис. 2.2.10)")
    _length_axis(ax, L)
    fig.tight_layout()
    return fig


def fig_total(x: np.ndarray, mtv: np.ndarray, m_plus: np.ndarray,
              m_minus: np.ndarray, L: float) -> Figure:
    """Mтв и Mр = Mтв ± Mдв по длине (п. 2.2.12-1)."""
    fig = Figure(figsize=(8, 3.8), dpi=110)
    ax = fig.subplots()
    ax.plot(x, mtv, color="#666666", linewidth=1.5, linestyle="--", label="Mтв")
    ax.plot(x, m_plus, color=ACCENT, linewidth=2.0, label="Mр = Mтв + Mдв")
    ax.plot(x, m_minus, color=SECOND, linewidth=2.0, label="Mр = Mтв − Mдв")
    ax.fill_between(x, m_minus, m_plus, color=ACCENT_SOFT, alpha=0.6)
    top = max(float(np.max(m_plus)), float(np.max(m_minus)))
    bot = min(float(np.min(m_plus)), float(np.min(m_minus)))
    pad = 0.12 * max(abs(top), abs(bot), 1.0)
    ax.set_ylim(bot - pad, top + pad)
    _style(ax, "x / L", "M, кН·м", "Расчётный изгибающий момент Mр = Mтв ± Mдв")
    ax.legend(frameon=False, fontsize=9, loc="upper center",
              bbox_to_anchor=(0.5, -0.2), ncol=3)
    _length_axis(ax, L)
    fig.tight_layout()
    return fig


def fig_to_png(fig: Figure, dpi: int = 200) -> bytes:
    """PNG-байты для кнопки скачивания."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    return buf.getvalue()
