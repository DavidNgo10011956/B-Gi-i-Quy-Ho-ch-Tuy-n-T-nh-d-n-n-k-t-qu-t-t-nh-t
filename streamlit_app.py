"""
streamlit_app.py
================
Web front end for the Linear Programming Solver toolkit.

It reuses the same modules as the terminal program (lp_app.py):
    lp_engine.py       -- parsing, solving, corner points, shadow prices
    lp_input_guide.py  -- example problems, input guides, special cases
    lp_plotting.py     -- the pictures (feasible region, 3-D region, plan)
    lp_utils.py        -- shared helpers

Run locally:
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Deploy: push this folder to GitHub and point Streamlit Community Cloud at
streamlit_app.py (see README.md).
"""

from __future__ import annotations

import io
import os
import sys

# Streamlit Cloud has no display: pick the non-GUI backend BEFORE pyplot is imported anywhere.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

# Make sibling modules importable however the app is launched.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lp_engine import (LPModel, MAX_CONSTRAINTS, MAX_VARIABLES, _num, format_point,  # noqa: E402
                       parse_constraint, parse_objective, solve, step_by_step)
from lp_input_guide import (SPECIAL_CASES, example_problems, input_guide_rows,  # noqa: E402
                            is_special_case, symbol_guide_rows)
from lp_plotting import plot_explanation, plot_model  # noqa: E402
from lp_utils import parse_name_list  # noqa: E402


st.set_page_config(page_title="Bộ giải Quy hoạch Tuyến tính", page_icon="📐", layout="wide")


# --------------------------------------------------------------------------- #
# Model building and solving
# --------------------------------------------------------------------------- #

def build_model(var_names, goal, objective_text, constraint_lines) -> LPModel:
    """Turn the text the user typed into an LPModel (raises ValueError on bad input)."""
    objective = parse_objective(objective_text, var_names)
    lines = [ln for ln in constraint_lines if ln.strip()]
    if not lines:
        raise ValueError("Hãy nhập ít nhất một ràng buộc.")
    if len(lines) > MAX_CONSTRAINTS:
        raise ValueError(f"Hỗ trợ tối đa {MAX_CONSTRAINTS} ràng buộc (bạn đã nhập {len(lines)}).")
    constraints = []
    for i, line in enumerate(lines, start=1):
        try:
            cons = parse_constraint(line, var_names)
        except ValueError as exc:
            raise ValueError(f"Ràng buộc {i} ({line.strip()}): {exc}") from None
        if not any(cons.coeffs):
            raise ValueError(f"Ràng buộc {i} ({line.strip()}) không có biến.")
        constraints.append(cons)
    return LPModel(var_names=var_names, objective=objective, goal=goal, constraints=constraints)


@st.cache_data(show_spinner=False)
def solve_cached(var_names: tuple, goal: str, objective_text: str, constraint_lines: tuple):
    """Solve once per distinct model; Streamlit reruns the script on every click."""
    model = build_model(list(var_names), goal, objective_text, list(constraint_lines))
    return model, solve(model)


def figure_png(model, solution):
    """Draw the matching picture and return (png_bytes, figure) or (None, None)."""
    fig = plot_model(model, solution)          # no save_path, no show -> just the figure
    if fig is None:
        return None, None
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    return buf.getvalue(), fig


# --------------------------------------------------------------------------- #
# Sidebar: choose an example or build your own
# --------------------------------------------------------------------------- #

EXAMPLES = example_problems()


def example_inputs():
    labels = [f"{ex['level']} · {ex['name']}" for ex in EXAMPLES]
    choice = st.sidebar.selectbox("Bài toán ví dụ", range(len(EXAMPLES)), format_func=lambda i: labels[i])
    ex = EXAMPLES[choice]
    objective_text = ", ".join(_num(c) for c in ex["objective"])
    st.sidebar.caption(f"{len(ex['var_names'])} biến × {len(ex['constraints'])} ràng buộc")
    return ex["var_names"], ex["goal"], objective_text, ex["constraints"]


def own_inputs():
    n = st.sidebar.number_input("Số biến quyết định", 1, MAX_VARIABLES, 2, step=1)
    default_names = "x, y" if n == 2 else ("x" if n == 1 else ", ".join(f"x{i}" for i in range(1, n + 1)))
    names_text = st.sidebar.text_input("Tên biến (cách nhau bằng dấu phẩy)", default_names, key=f"names_{n}")
    goal = st.sidebar.radio("Mục tiêu", ["max", "min"], horizontal=True,
                            format_func=lambda g: "Tối đa hóa" if g == "max" else "Tối thiểu hóa")
    objective_text = st.sidebar.text_input("Hàm mục tiêu Z =", "40x + 30y" if n == 2 else "",
                                           placeholder="ví dụ: 40x + 30y   hoặc   40, 30")
    constraints_text = st.sidebar.text_area(
        f"Các ràng buộc (mỗi dòng một ràng buộc, tối đa {MAX_CONSTRAINTS})",
        "2x + y <= 100 # Máy 1\nx + 2y <= 80 # Máy 2" if n == 2 else "",
        height=180,
        help="Dùng <=, >= hoặc =. Thêm nhãn sau dấu #. Điều kiện không âm được thêm tự động.",
    )
    var_names = parse_name_list(names_text)          # may raise ValueError -> shown in main area
    if len(var_names) != n:
        raise ValueError(f"Cần {n} tên biến, nhưng đã nhập {len(var_names)}.")
    return var_names, goal, objective_text, constraints_text.splitlines()


# --------------------------------------------------------------------------- #
# Result rendering
# --------------------------------------------------------------------------- #

STATUS_TEXT = {
    "optimal": ("Đã tìm thấy nghiệm tối ưu", "success"),
    "multiple_optimal": ("Có nhiều nghiệm tối ưu", "info"),
    "infeasible": ("Không khả thi — không có phương án nào thỏa mãn mọi ràng buộc", "error"),
    "unbounded": ("Không bị chặn — Z có thể cải thiện không giới hạn", "warning"),
    "error": ("Bộ giải không thể hoàn tất", "error"),
}


def show_status(solution):
    text, kind = STATUS_TEXT.get(solution.status, (solution.message, "info"))
    getattr(st, kind)(text)
    note = is_special_case(solution.status, solution.degenerate)
    if note:
        with st.expander("Giải thích trường hợp đặc biệt", expanded=True):
            for line in note.splitlines():
                st.markdown(f"- {line}")


def show_headline(model, solution):
    if not solution.is_solved:
        return
    cols = st.columns(min(model.n_vars, 4) + 1)
    cols[0].metric(f"Z tối ưu ({'tối đa' if model.goal == 'max' else 'tối thiểu'})", _num(solution.objective_value))
    for i, (name, value) in enumerate(zip(model.var_names, solution.x)):
        cols[(i % min(model.n_vars, 4)) + 1].metric(name, _num(value))


def steps_tab(model, solution):
    for step in step_by_step(model, solution):
        title, _, body = step.partition("\n")
        st.markdown(f"**{title.replace(' -- ', ' — ')}**")
        st.code(body, language=None)


def corners_tab(model, solution):
    if not solution.corner_points:
        st.write("Miền khả thi không có điểm góc (miền rỗng).")
        return
    rows = [dict(zip(model.var_names, p)) | {"Z": z}
            for p, z in zip(solution.corner_points, solution.corner_values)]
    df = pd.DataFrame(rows)
    if solution.is_solved:
        best = solution.objective_value
        df["Tối ưu"] = [("★" if abs(z - best) <= 1e-6 * max(1, abs(best)) else "") for z in df["Z"]]
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(f"Tìm thấy {len(df)} điểm góc từ {solution.candidates_checked:,} tổ hợp đường biên.")


def sensitivity_tab(model, solution):
    if not solution.is_solved:
        st.write("Thông tin độ nhạy chỉ có khi tồn tại nghiệm tối ưu.")
        return
    rows = []
    for i, cons in enumerate(model.constraints):
        rows.append({
            "Ràng buộc": cons.label or f"Ràng buộc {i + 1}",
            "Phương trình": cons.render(model.var_names, include_label=False),
            "Độ dư / phần dư": solution.slack[i],
            "Ràng buộc chặt": "có" if solution.binding[i] else "",
            "Giá bóng": solution.shadow_prices[i] if solution.shadow_prices else None,
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("Giá bóng = mức thay đổi của Z khi vế phải của ràng buộc đó tăng 1 đơn vị, "
               "trong khi các ràng buộc khác giữ nguyên (chỉ đúng với thay đổi nhỏ).")
    if solution.degenerate:
        st.warning("Nghiệm tối ưu bị suy biến, vì vậy các giá bóng này có thể chỉ đúng theo một chiều: "
                   "tăng và giảm vế phải có thể làm Z thay đổi với mức khác nhau. "
                   "Hãy giải lại mô hình với giá trị mới trước khi dựa vào giá bóng.")


def plot_tab(model, solution):
    if model.n_vars < 2:
        st.write("Với một biến thì không có miền 2D để vẽ — xem báo cáo từng bước.")
        return
    png, fig = figure_png(model, solution)
    if png is None:
        st.write("Không có hình phù hợp để vẽ cho kết quả này.")
        return
    st.pyplot(fig, width="stretch")
    plt.close(fig)                                  # free memory between reruns
    st.download_button("Tải đồ thị (PNG)", png, file_name="lp_plot.png", mime="image/png")
    st.markdown("**Hình này thể hiện điều gì**")
    st.text(plot_explanation(model, solution))


def guides_page():
    st.header("Hướng dẫn nhập dữ liệu")
    st.dataframe(pd.DataFrame(input_guide_rows()), width="stretch", hide_index=True)
    st.header("Hướng dẫn ký hiệu")
    st.dataframe(pd.DataFrame(symbol_guide_rows()), width="stretch", hide_index=True)
    st.header("Các trường hợp đặc biệt")
    df = pd.DataFrame(SPECIAL_CASES).rename(columns={
        "name": "Trường hợp", "symbol": "Ký hiệu", "meaning": "Ý nghĩa", "spot": "Cách nhận biết", "example": "Ví dụ"})
    st.dataframe(df, width="stretch", hide_index=True)


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

def main():
    st.title("Bộ giải Quy hoạch Tuyến tính")
    st.write(f"Giải mô hình có từ 1–{MAX_VARIABLES} biến quyết định và tối đa {MAX_CONSTRAINTS} "
             "ràng buộc, kèm các điểm góc, giá bóng và hình minh họa kết quả.")

    st.sidebar.header("Mô hình")
    mode = st.sidebar.radio("Bắt đầu từ", ["Bài toán ví dụ", "Tự xây dựng", "Hướng dẫn"])

    if mode == "Hướng dẫn":
        guides_page()
        return

    try:
        var_names, goal, objective_text, constraint_lines = (
            example_inputs() if mode == "Bài toán ví dụ" else own_inputs())
    except ValueError as exc:
        st.error(f"Lỗi dữ liệu nhập: {exc}")
        return

    # After the first Solve, results follow the sidebar inputs live (solving is cached).
    if st.sidebar.button("Giải", type="primary", width="stretch"):
        st.session_state["solved_once"] = True
    if not st.session_state.get("solved_once"):
        st.info("Chọn hoặc nhập mô hình trong thanh bên, sau đó nhấn **Giải**.")
        return

    key = (tuple(var_names), goal, objective_text, tuple(constraint_lines))

    try:
        with st.spinner("Đang giải…"):
            model, solution = solve_cached(*key)
    except ValueError as exc:
        st.error(f"Lỗi dữ liệu nhập: {exc}")
        return
    except Exception as exc:                        # never crash the page
        st.error(f"Lỗi bộ giải: {exc}")
        return

    show_status(solution)
    show_headline(model, solution)

    tabs = st.tabs(["Hình minh họa", "Từng bước", "Điểm góc", "Độ nhạy"])
    with tabs[0]:
        try:
            plot_tab(model, solution)
        except Exception as exc:                    # a plotting problem shouldn't hide the answer
            st.warning(f"Không thể vẽ đồ thị: {exc}")
    with tabs[1]:
        steps_tab(model, solution)
    with tabs[2]:
        corners_tab(model, solution)
    with tabs[3]:
        sensitivity_tab(model, solution)


main()
