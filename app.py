"""
app.py — веб-приложение «Дополнительный волновой изгибающий момент».
ПКПС РКО, часть I, п. 2.2.10.

Запуск:   streamlit run app.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import pkps_core as core
import pkps_plots as plots
from pkps_core import BasinClass, ShipType

st.set_page_config(page_title="Волновой момент — ПКПС РКО", layout="wide")


# ----------------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------------
def csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV, который корректно открывается в русском Excel (разделитель «;», запятая в числах)."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def profile_table(L: float, xm, m, xn, n) -> pd.DataFrame:
    x = np.union1d(xm, xn)
    return pd.DataFrame({
        "x/L": x,
        "x, м": x * L,
        "Mдв, кН·м": np.interp(x, xm, m),
        "Nдв, кН": np.interp(x, xn, n),
    })


def protocol_table(res: core.WaveMomentResult) -> pd.DataFrame:
    return pd.DataFrame({
        "Обозначение": [s.symbol for s in res.steps],
        "Величина": [s.name for s in res.steps],
        "Пункт ПКПС": [s.ref for s in res.steps],
        "Значение": [core.format_value(s.value) for s in res.steps],
        "Ед. изм.": [s.unit for s in res.steps],
    })


def metric(col, label: str, value, unit: str = "") -> None:
    text = core.format_value(value)
    col.metric(label, f"{text} {unit}".strip() if value is not None else "—")


# ----------------------------------------------------------------------------
# Ввод данных
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("Исходные данные")

    basin = st.selectbox("Класс судна (разряд бассейна)", list(BasinClass),
                         format_func=lambda c: f"«{c.value}»")
    ship_type = st.selectbox(
        "Тип судна", list(ShipType), format_func=lambda s: s.value,
        help="Определяет коэффициент ks в формуле 2.2.10-10.")

    st.subheader("Главные размерения, м")
    L = st.number_input("L — длина", min_value=1.0, max_value=400.0,
                        value=110.0, step=1.0, format="%.2f")
    B = st.number_input("B — ширина", min_value=0.5, max_value=80.0,
                        value=16.5, step=0.1, format="%.2f")
    T = st.number_input("T — осадка", min_value=0.1, max_value=20.0,
                        value=3.5, step=0.1, format="%.2f")
    Tn = st.number_input("Tн — осадка носом", min_value=0.1, max_value=40.0,
                         value=3.4, step=0.1, format="%.2f",
                         help="Для расчётного случая нагрузки. От неё зависит ударный момент Mу.")

    st.subheader("Полнота и скорость")
    Cb = st.number_input("Cb — коэффициент полноты (δ)", min_value=0.30, max_value=1.00,
                         value=0.85, step=0.01, format="%.3f")
    c1, c2 = st.columns([3, 2])
    v_in = c1.number_input("V₀ — скорость хода", min_value=0.0, max_value=100.0,
                           value=18.0, step=0.5, format="%.2f")
    v_unit = c2.selectbox("Ед.", list(core.SPEED_UNITS), index=0)
    V0_kmh = core.speed_to_kmh(v_in, v_unit)
    if v_unit != "км/ч":
        st.caption(f"В расчёт идёт {V0_kmh:.2f} км/ч — в таких единицах скорость входит в формулы Правил.")

    st.subheader("Прочность и масса")
    I = st.number_input("I — момент инерции миделевого сечения, м⁴", min_value=0.001,
                        max_value=1000.0, value=5.0, step=0.1, format="%.3f",
                        help="Эквивалентного бруса при проектных толщинах и "
                             "редукционных коэффициентах, равных единице.")
    manual_D = st.checkbox("Задать водоизмещение D вручную", value=False)
    if manual_D:
        D_val = st.number_input("D — водоизмещение, кН", min_value=1.0, max_value=5.0e7,
                                value=52000.0, step=500.0, format="%.0f",
                                help="Для расчётного случая нагрузки.")
        rho = 1.0
    else:
        D_val = None
        rho = st.selectbox("Плотность воды для оценки D", [1.0, 1.025],
                           format_func=lambda r: "пресная, 1,000 т/м³" if r == 1.0
                           else "морская, 1,025 т/м³")

    st.subheader("Эпюра")
    pmin = core.min_plateau(basin)
    if basin in (BasinClass.M, BasinClass.O):
        plateau = st.slider("Постоянный участок Mдв, доли L", min_value=float(pmin),
                            max_value=0.9, value=0.5, step=0.05,
                            help="Для «М» и «О» границы участка не ближе 0,15L к миделю "
                                 "(то есть не менее 0,3L). По умолчанию 0,5L, как на рис. 2.2.10.")
    else:
        plateau = 0.5
        st.caption("Для «Р» и «Л» постоянный участок — 0,5L (п. 2.2.10).")


# ----------------------------------------------------------------------------
# Расчёт
# ----------------------------------------------------------------------------
st.title("Дополнительный волновой изгибающий момент")
st.caption("ПКПС РКО, часть I «Корпус и его оборудование», п. 2.2.10 — классы «М», «О», «Р», «Л»")

inp = core.ShipInput(basin=basin, ship_type=ship_type, L=L, B=B, T=T, Tn=Tn, Cb=Cb,
                     V0_kmh=V0_kmh, I=I, D=D_val, rho=rho)
try:
    res = core.calculate(inp)
except core.InputError as exc:
    st.error(str(exc))
    st.stop()

for w in res.warnings:
    (st.info if w.startswith("D оценено") else st.warning)(w)

cols = st.columns(5)
metric(cols[0], "Mв — волновой", res.Mv, "кН·м")
metric(cols[1], "kр — вибрация", res.kp)
metric(cols[2], "Mу — ударный", res.My, "кН·м")
metric(cols[3], "Mдв = kр·Mв + Mу", res.Mdv, "кН·м")
metric(cols[4], "Nдв = 4Mдв/L", res.Ndv, "кН")

tab_epure, tab_total, tab_protocol, tab_help = st.tabs(
    ["Эпюры", "Расчётный момент Mр", "Протокол расчёта", "Справка"])

# ----------------------------------------------------------------------------
# Эпюры
# ----------------------------------------------------------------------------
with tab_epure:
    if res.Mdv is None:
        st.info("Эпюры не построены: коэффициент kр определить нельзя (см. предупреждение выше).")
    else:
        xm, m = core.moment_profile(res.Mdv, plateau)
        xn, n = core.shear_profile(res.Ndv)

        fig_m = plots.fig_moment(xm, m, L, res.Mdv, plateau, basin.value)
        st.pyplot(fig_m)
        fig_n = plots.fig_shear(xn, n, L, res.Ndv)
        st.pyplot(fig_n)
        st.caption("Эпюры даны по модулю с двумя знаками (±): дополнительный волновой момент "
                   "учитывается и на прогиб, и на перегиб.")

        d1, d2, d3 = st.columns(3)
        d1.download_button("Эпюра Mдв (PNG)", plots.fig_to_png(fig_m),
                           file_name="epure_Mdv.png", mime="image/png")
        d2.download_button("Эпюра Nдв (PNG)", plots.fig_to_png(fig_n),
                           file_name="epure_Ndv.png", mime="image/png")
        d3.download_button("Данные эпюр (CSV)", csv_bytes(profile_table(L, xm, m, xn, n)),
                           file_name="epure_data.csv", mime="text/csv")

# ----------------------------------------------------------------------------
# Mр = Mтв ± Mдв
# ----------------------------------------------------------------------------
with tab_total:
    st.markdown("Расчётный момент **Mр = Mтв + Mдв** (п. 2.2.12-1). Момент на тихой воде Mтв "
                "в п. 2.2.10 не определяется — введите его эпюру из расчёта загрузки "
                "(x/L от 0 до 1, значения в кН·м). Знак Mтв задаётся вашей конвенцией, "
                "одной на всю таблицу.")
    if res.Mdv is None:
        st.info("Mдв не определён — расчёт Mр недоступен.")
    else:
        df0 = pd.DataFrame({"x/L": [0.0, 0.25, 0.5, 0.75, 1.0],
                            "Mтв, кН·м": [0.0, None, None, None, 0.0]})
        edited = st.data_editor(
            df0, num_rows="dynamic", key="mtv_table",
            column_config={
                "x/L": st.column_config.NumberColumn("x/L", min_value=0.0, max_value=1.0,
                                                     format="%.3f"),
                "Mтв, кН·м": st.column_config.NumberColumn("Mтв, кН·м", format="%.1f"),
            })
        valid = edited.dropna()
        if len(valid) < 3:
            st.info("Заполните Mтв хотя бы в одной точке между концами — "
                    "тогда будет построена эпюра Mр.")
        else:
            xm, m = core.moment_profile(res.Mdv, plateau)
            try:
                mtv, m_plus, m_minus = core.combine_with_still_water(
                    valid["x/L"].tolist(), valid["Mтв, кН·м"].tolist(), xm, m)
            except core.InputError as exc:
                st.error(str(exc))
            else:
                fig_t = plots.fig_total(xm, mtv, m_plus, m_minus, L)
                st.pyplot(fig_t)
                k1, k2 = st.columns(2)
                k1.metric("max (Mтв + Mдв)", core.format_value(float(m_plus.max())) + " кН·м")
                k2.metric("min (Mтв − Mдв)", core.format_value(float(m_minus.min())) + " кН·м")
                out = pd.DataFrame({"x/L": xm, "x, м": xm * L, "Mтв, кН·м": mtv,
                                    "Mдв, кН·м": m, "Mтв+Mдв, кН·м": m_plus,
                                    "Mтв−Mдв, кН·м": m_minus})
                st.download_button("Данные Mр (CSV)", csv_bytes(out),
                                   file_name="Mr_data.csv", mime="text/csv")

# ----------------------------------------------------------------------------
# Протокол
# ----------------------------------------------------------------------------
with tab_protocol:
    proto = protocol_table(res)
    st.dataframe(proto, hide_index=True)
    st.download_button("Протокол (CSV)", csv_bytes(proto),
                       file_name="protocol_2_2_10.csv", mime="text/csv")
    with st.expander("Сверка с таблицами Правил"):
        st.markdown(
            f"Параметры для табл. 2.2.10-2…2.2.10-4: **δ = {Cb:.3f}**, "
            f"**a = {res.a:.3f} м** (табл. 2.2.10-3), **b = {res.b:.3f} м** (табл. 2.2.10-4). "
            "Коэффициенты kδ, kт, kв в протоколе считаются по формулам; "
            "значения из таблиц должны совпасть с ними с точностью до интерполяции.")

# ----------------------------------------------------------------------------
# Справка
# ----------------------------------------------------------------------------
with tab_help:
    st.markdown("""
**Что считается.** Дополнительный волновой момент на миделе по п. 2.2.10:

`Mдв = ±(kр·Mв + Mу)`, `Nдв = 4·Mдв / L`.

- `Mв = 0,255·ε·kδ·kт·kв·B·L²·h` — прямое действие волны;
- `kр` — влияние волновой вибрации (через ψ, ωк, σ, kμ);
- `Mу = kу·φ1·D·L` — удар волн в носовую оконечность, возникает при малой осадке носом.

**Единицы.** L, B, T, Tн — м; скорость V₀ — км/ч (можно вводить в м/с и узлах, пересчёт автоматический);
I — м⁴; D — кН; моменты — кН·м.

**Откуда брать данные.** L, B, T, Tн и Cb берутся при посадке, соответствующей расчётному случаю
нагрузки для момента на тихой воде Mтв. I — момент инерции эквивалентного бруса при проектных
толщинах и редукционных коэффициентах, равных единице.

**Допущения этой версии.**
- Если D не задано, оно оценивается как 9,81·ρ·Cb·L·B·T. Это приближение.
- Эпюра Nдв построена по рис. 2.2.10 (узлы 0 / 0,15L / 0,30L / 0,40L / 0,60L / 0,70L / 0,85L / 1,0L).
- Если ωк/σ > 1,4, Правила не дают ψ: Mв и Mу считаются, а kр, Mдв и Nдв — нет.

**Пока не реализовано.** Классы «М-СП», «М-ПР», «О-ПР» (п. 2.2.11), минимум Mдв для
грузовых операций (п. 2.2.15), расчёт Mтв.

Расчёт справочный: соответствие требованиям Правил подтверждает расчётчик и РКО.
""")
