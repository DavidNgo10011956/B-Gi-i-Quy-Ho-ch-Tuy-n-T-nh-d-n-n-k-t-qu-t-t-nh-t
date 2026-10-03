"""
lp_engine.py
============
Core engine for the Linear Programming Solver toolkit.

Responsibilities:
  * Parse friendly constraint strings such as "2x1 + 3x2 <= 100"
    (the unicode forms "≤", "≥" and "−" are accepted too).
  * Build an LPModel: 1-8 decision variables, 1-12 constraints,
    non-negativity assumed automatically.
  * Solve it with SciPy's HiGHS solver (scipy.optimize.linprog).
  * Reproduce the "by hand" corner-point method for ANY number of
    variables: every combination of n boundaries (constraint lines /
    planes plus the axes x_j = 0) is intersected, the feasible
    intersection points are kept, and Z is evaluated at each corner.
    With 2 variables this is exactly the graphical method from the
    teaching slides; with 3-8 variables it is the same idea in
    cao hơn dimensions.
  * Detect infeasible / unbounded / multiple-optimal / degenerate cases.
  * Report sensitivity information from HiGHS: the shadow price of every
    constraint and the reduced cost of every variable left at zero.
  * Produce a human-readable, step-by-step explanation of the solution.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from itertools import combinations, islice
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import linprog

MAX_VARIABLES = 8
MAX_CONSTRAINTS = 12
TOL = 1e-7
CORNER_ROWS_SHOWN = 10          # corner points listed in the report for 3+ variables


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class Constraint:
    coeffs: List[float]
    sense: str          # '<=', '>=' or '='
    rhs: float
    label: str = ""

    def render(self, var_names: List[str], include_label: bool = True) -> str:
        lhs = _join_terms(self.coeffs, var_names) or "0"
        tag = f"   ({self.label})" if (include_label and self.label) else ""
        return f"{lhs} {self.sense} {_num(self.rhs)}{tag}"

    def name(self, var_names: List[str]) -> str:
        """Short display name: the label if given, else the equation."""
        if self.label:
            return self.label
        return self.render(var_names, include_label=False)


@dataclass
class LPModel:
    var_names: List[str]
    objective: List[float]
    goal: str                       # 'max' or 'min'
    constraints: List[Constraint]

    def __post_init__(self):
        self.goal = self.goal.strip().lower()
        if self.goal not in ("max", "min"):
            raise ValueError("mục tiêu phải là 'max' hoặc 'min'.")
        n = len(self.var_names)
        if not (1 <= n <= MAX_VARIABLES):
            raise ValueError(
                f"Công cụ này hỗ trợ từ 1 đến {MAX_VARIABLES} biến quyết định (đã nhập {n})."
            )
        if len(set(self.var_names)) != n:
            raise ValueError("Tên các biến phải khác nhau.")
        if len(self.constraints) == 0:
            raise ValueError("Cần ít nhất một ràng buộc.")
        if len(self.constraints) > MAX_CONSTRAINTS:
            raise ValueError(
                f"Công cụ này hỗ trợ tối đa {MAX_CONSTRAINTS} ràng buộc "
                f"(received {len(self.constraints)})."
            )
        if len(self.objective) != n:
            raise ValueError(
                f"Hàm mục tiêu có {len(self.objective)} hệ số nhưng có {n} biến."
            )
        if not all(math.isfinite(v) for v in self.objective):
            raise ValueError("Các hệ số của hàm mục tiêu phải là các số hữu hạn.")
        for i, c in enumerate(self.constraints, start=1):
            if len(c.coeffs) != n:
                raise ValueError(f"Ràng buộc {i} có số hệ số khác với số biến.")
            if c.sense not in ("<=", ">=", "="):
                raise ValueError(f"Ràng buộc {i} có dấu không xác định '{c.sense}'.")
            if not all(math.isfinite(v) for v in c.coeffs) or not math.isfinite(c.rhs):
                raise ValueError(f"Ràng buộc {i} chứa một giá trị không phải là số hữu hạn.")

    @property
    def n_vars(self) -> int:
        return len(self.var_names)

    def objective_expr(self) -> str:
        return _join_terms(self.objective, self.var_names) or "0"

    def objective_str(self) -> str:
        return f"{'Tối đa hóa' if self.goal == 'max' else 'Tối thiểu hóa'}  Z = {self.objective_expr()}"


@dataclass
class LPSolution:
    status: str                                  # optimal | multiple_optimal | infeasible | unbounded | error
    x: Optional[List[float]]
    objective_value: Optional[float]
    slack: Optional[List[float]]
    binding: Optional[List[bool]]
    message: str
    corner_points: Optional[List[Tuple[float, ...]]] = None   # every vertex of the feasible region
    corner_values: Optional[List[float]] = None               # Z at each vertex
    candidates_checked: int = 0                                # boundary combinations tried
    degenerate: bool = False                                   # more boundaries than needed meet at the optimum
    shadow_prices: Optional[List[float]] = None                # dZ per +1 unit of each constraint's RHS
    reduced_costs: Optional[List[float]] = None                # dZ per unit a zero variable is forced in

    @property
    def is_solved(self) -> bool:
        return self.status in ("optimal", "multiple_optimal")


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #

_TERM_RE = re.compile(r"^([+-]?\d*\.?\d*)\*?([a-zA-Z_]\w*)$")

_UNICODE_FIXES = {
    "\u2212": "-",      # − minus sign
    "\u2013": "-",      # – en dash
    "\u2264": "<=",     # ≤
    "\u2265": ">=",     # ≥
    "\u00d7": "*",      # ×
    "\u00b7": "*",      # ·
}


def _normalise(text: str) -> str:
    for bad, good in _UNICODE_FIXES.items():
        text = text.replace(bad, good)
    # accept the reversed spellings people often type
    text = text.replace("=<", "<=").replace("=>", ">=").replace("==", "=")
    return text


def parse_linear_expression(expr: str, var_names: List[str]) -> List[float]:
    """Parse '2x1 + 3.5x2 - x3' into a coefficient list ordered like var_names."""
    expr = _normalise(expr).replace(" ", "")
    if not expr:
        raise ValueError("Biểu thức trống.")
    coeffs = {v: 0.0 for v in var_names}
    tokens = re.findall(r"[+-]?[^+-]+", expr)
    for tok in tokens:
        m = _TERM_RE.match(tok)
        if not m:
            if re.fullmatch(r"[+-]?\d*\.?\d+", tok):
                raise ValueError(
                    f"'{tok}' is a plain number on the variable side. Move constants to the "
                    "right-hand side, e.g.  2x + y <= 100."
                )
            raise ValueError(f"Không thể phân tích hạng tử '{tok}'.")
        coef_str, var = m.group(1), m.group(2)
        if var not in coeffs:
            raise ValueError(f"Biến '{var}' không được nhận dạng. Cần một trong các biến {var_names}.")
        if coef_str in ("", "+"):
            coef = 1.0
        elif coef_str == "-":
            coef = -1.0
        else:
            try:
                coef = float(coef_str)
            except ValueError:
                raise ValueError(f"Không thể đọc số trong hạng tử '{tok}'.") from None
        coeffs[var] += coef
    return [coeffs[v] for v in var_names]


def parse_constraint(line: str, var_names: List[str]) -> Constraint:
    """Parse 'x1 + 2x2 <= 100 # label' into a Constraint."""
    label = ""
    if "#" in line:
        line, label = line.split("#", 1)
        label = label.strip()
    line = _normalise(line)
    # A strict '<' or '>' can't be modelled exactly in LP; treat it as '<=' / '>='.
    for sense, stored in (("<=", "<="), (">=", ">="), ("=", "="), ("<", "<="), (">", ">=")):
        if sense in line:
            lhs, rhs = line.split(sense, 1)
            if not lhs.strip():
                raise ValueError("Vế trái đang trống — hãy đặt các biến trước dấu bất đẳng thức.")
            coeffs = parse_linear_expression(lhs, var_names)
            try:
                rhs_val = float(rhs.strip())
            except ValueError:
                raise ValueError(
                    f"Right-hand side '{rhs.strip()}' must be a single number. "
                    "Keep all variables on the left, e.g.  x - y >= 0."
                ) from None
            return Constraint(coeffs=coeffs, sense=stored, rhs=rhs_val, label=label)
    raise ValueError(f"Ràng buộc '{line.strip()}' phải chứa <=, >= hoặc =.")


def parse_objective(text: str, var_names: List[str]) -> List[float]:
    """Accept either '40x + 30y' or '40, 30' for the objective coefficients."""
    text = _normalise(text).strip()
    if "=" in text:                       # tolerate "Z = 40x + 30y" / "max Z = ..."
        text = text.split("=", 1)[1]
    else:                                 # tolerate a leading "max" / "min" word
        text = re.sub(r"^\s*(max|min)\w*\s+", "", text, flags=re.IGNORECASE)
    if not text.strip():
        raise ValueError("Hàm mục tiêu đang trống.")
    if re.search(r"[a-zA-Z_]", text):
        return parse_linear_expression(text, var_names)
    try:
        values = [float(p) for p in re.split(r"[,;\s]+", text.strip()) if p]
    except ValueError:
        raise ValueError("Hãy nhập hàm mục tiêu dạng 40x + 30y hoặc danh sách số như 40, 30.") from None
    if len(values) != len(var_names):
        raise ValueError(f"Cần {len(var_names)} hệ số của hàm mục tiêu, nhưng đã nhập {len(values)}.")
    return values


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #

def _num(x: float) -> str:
    r = round(x)
    if abs(x - r) < 1e-9:
        return str(int(r))
    return f"{x:.4g}"


def _term(a: float, v: str) -> str:
    if abs(a - 1) < 1e-9:
        return f"+ {v}"
    if abs(a + 1) < 1e-9:
        return f"- {v}"
    sign = "+" if a >= 0 else "-"
    return f"{sign} {_num(abs(a))}{v}"


def _join_terms(coeffs: Sequence[float], var_names: Sequence[str]) -> str:
    """Join signed terms into 'a - b + c' form, no double signs, no leading '+'."""
    parts = [_term(a, v) for a, v in zip(coeffs, var_names) if abs(a) > TOL]
    text = " ".join(parts)
    if text.startswith("+ "):
        text = text[2:]
    elif text.startswith("- "):
        text = "-" + text[2:]
    return text


def format_point(point: Sequence[float], var_names: Sequence[str] | None = None) -> str:
    """(40, 20) for 2 variables; (t = 20, c = 0, d = 10) when names are given."""
    if var_names is None:
        return "(" + ", ".join(_num(v) for v in point) + ")"
    return "(" + ", ".join(f"{n} = {_num(v)}" for n, v in zip(var_names, point)) + ")"


# --------------------------------------------------------------------------- #
# Corner-point (vertex) enumeration -- works for any number of variables
# --------------------------------------------------------------------------- #

def _arrays(model: LPModel):
    A = np.array([c.coeffs for c in model.constraints], dtype=float)
    b = np.array([c.rhs for c in model.constraints], dtype=float)
    senses = [c.sense for c in model.constraints]
    return A, b, senses


def _feasible_mask(P: np.ndarray, A: np.ndarray, b: np.ndarray, senses: List[str],
                   upper: Optional[np.ndarray] = None, tol: float = 1e-6) -> np.ndarray:
    """Vectorised check: which rows of P satisfy every constraint (and x >= 0)?"""
    mask = (P >= -tol).all(axis=1)
    if upper is not None:
        mask &= (P <= upper + tol * np.maximum(1.0, np.abs(upper))).all(axis=1)
    lhs = P @ A.T
    scale = tol * np.maximum(1.0, np.abs(b))
    for i, s in enumerate(senses):
        if s == "<=":
            mask &= lhs[:, i] <= b[i] + scale[i]
        elif s == ">=":
            mask &= lhs[:, i] >= b[i] - scale[i]
        else:
            mask &= np.abs(lhs[:, i] - b[i]) <= scale[i]
    return mask


def feasible_vertices(model: LPModel, upper: Optional[Sequence[float]] = None,
                      chunk: int = 20000) -> Tuple[np.ndarray, int]:
    """Return (vertices, number_of_combinations_tried).

    Each vertex of an n-variable feasible region is a point where n boundary
    hyperplanes meet. We try every combination of n boundaries drawn from
    the constraints and the axes x_j = 0 (plus the box x_j = upper_j when
    `upper` is given -- used by the plots to clip unbounded regions), solve
    the n x n system, and keep the solutions that satisfy every constraint.
    Worst case (8 variables, 12 constraints) is C(20, 8) = 125,970 small
    systems, solved in vectorised batches.
    """
    n = model.n_vars
    A, b, senses = _arrays(model)

    H_parts, h_parts = [A, np.eye(n)], [b, np.zeros(n)]
    up = None
    if upper is not None:
        up = np.asarray(upper, dtype=float)
        H_parts.append(np.eye(n))
        h_parts.append(up)
    H = np.vstack(H_parts)
    h = np.concatenate(h_parts)

    total = math.comb(len(H), n)
    row_norms = np.linalg.norm(H, axis=1)
    combos = combinations(range(len(H)), n)
    found = []
    while True:
        batch = list(islice(combos, chunk))
        if not batch:
            break
        idx = np.array(batch)
        M = H[idx]                                  # (k, n, n)
        r = h[idx]                                  # (k, n)
        norms = row_norms[idx].prod(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = np.abs(np.linalg.det(M)) / np.where(norms > 0, norms, np.inf)
        ok = ratio > 1e-9                           # boundaries genuinely cross at one point
        if not ok.any():
            continue
        P = np.linalg.solve(M[ok], r[ok][..., None])[..., 0]
        found.append(P[_feasible_mask(P, A, b, senses, up)])

    if not found or sum(len(f) for f in found) == 0:
        return np.empty((0, n)), total

    pts = np.round(np.vstack(found), 6) + 0.0       # "+ 0.0" turns -0.0 into 0.0
    pts = np.unique(pts, axis=0)
    return pts, total


def order_polygon(points: np.ndarray) -> np.ndarray:
    """Order 2-D points counter-clockwise around their centroid (for drawing)."""
    if len(points) < 3:
        return points
    c = points.mean(axis=0)
    ang = np.arctan2(points[:, 1] - c[1], points[:, 0] - c[0])
    return points[np.argsort(ang)]


def enumerate_corner_points(model: LPModel):
    """The corner-point method for any number of variables.

    Returns (corner_points, corner_values, combinations_tried).
    2 variables  -> points ordered around the region (ready to draw a polygon).
    3+ variables -> points ordered best Z first (ready to list in a report).
    """
    pts, total = feasible_vertices(model)
    if len(pts) == 0:
        return [], [], total

    obj = np.array(model.objective, dtype=float)
    if model.n_vars == 2:
        pts = order_polygon(pts)
    else:
        vals = pts @ obj
        order = np.argsort(-vals if model.goal == "max" else vals, kind="stable")
        pts = pts[order]
    values = (pts @ obj).tolist()
    return [tuple(float(v) for v in p) for p in pts], values, total


def _check_alternate_optima(model: LPModel, obj_val: float, corner_values) -> bool:
    if not corner_values:
        return False
    best = max(corner_values) if model.goal == "max" else min(corner_values)
    tol = 1e-6 * max(1.0, abs(best))
    count = sum(1 for v in corner_values if abs(v - best) < tol and abs(v - obj_val) < tol)
    return count > 1


# --------------------------------------------------------------------------- #
# Solving
# --------------------------------------------------------------------------- #

def _build_matrices(model: LPModel):
    A_ub, b_ub, A_eq, b_eq = [], [], [], []
    for c in model.constraints:
        if c.sense == "<=":
            A_ub.append(c.coeffs)
            b_ub.append(c.rhs)
        elif c.sense == ">=":
            A_ub.append([-a for a in c.coeffs])
            b_ub.append(-c.rhs)
        else:
            A_eq.append(c.coeffs)
            b_eq.append(c.rhs)
    return (A_ub or None, b_ub or None, A_eq or None, b_eq or None)


def solve(model: LPModel) -> LPSolution:
    n = model.n_vars
    c = np.array(model.objective, dtype=float)
    c_signed = -c if model.goal == "max" else c   # linprog always minimizes
    A_ub, b_ub, A_eq, b_eq = _build_matrices(model)
    bounds = [(0, None)] * n

    # The by-hand corner-point method runs for every model, so the report can
    # show the corners even when the problem turns out infeasible or unbounded.
    corners, corner_vals, tried = enumerate_corner_points(model)
    common = dict(corner_points=corners, corner_values=corner_vals, candidates_checked=tried)

    res = linprog(c_signed, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")

    if res.status == 2:
        return LPSolution(
            status="infeasible", x=None, objective_value=None, slack=None, binding=None,
            message="Không có điểm nào đồng thời thỏa mãn tất cả các ràng buộc: bài toán không khả thi.",
            **common,
        )
    if res.status == 3:
        return LPSolution(
            status="unbounded", x=None, objective_value=None, slack=None, binding=None,
            message="The objective can be improved without limit inside the feasible region: "
                    "the problem is unbounded.",
            **common,
        )
    if res.status != 0:
        return LPSolution(
            status="error", x=None, objective_value=None, slack=None, binding=None,
            message=f"Bộ giải không tìm được nghiệm ({res.message}).",
            **common,
        )

    x = [max(0.0, v) for v in res.x.tolist()]   # clip tiny negative numerical noise
    x = [0.0 if abs(v) < 1e-9 else v for v in x]
    obj_val = float(np.dot(c, x))

    slacks, binding = [], []
    for cons in model.constraints:
        lhs = sum(a * xi for a, xi in zip(cons.coeffs, x))
        if cons.sense == "<=":
            s = cons.rhs - lhs
        elif cons.sense == ">=":
            s = lhs - cons.rhs
        else:
            s = 0.0
        tol = 1e-6 * max(1.0, abs(cons.rhs))
        slacks.append(0.0 if abs(s) < tol else s)
        binding.append(abs(s) < tol)

    shadow, reduced = _sensitivity(model, res)

    # Degenerate: more boundaries pass through the optimum than are needed to pin it down.
    active = sum(binding) + sum(1 for v in x if abs(v) < 1e-9)
    degenerate = active > n

    status = "multiple_optimal" if _check_alternate_optima(model, obj_val, corner_vals) else "optimal"
    message = (
        "Đã tìm thấy nghiệm tối ưu."
        if status == "optimal"
        else "Multiple optimal solutions exist: more than one corner point (and every point "
             "between them) achieves the same best value of Z."
    )

    return LPSolution(
        status=status, x=x, objective_value=obj_val, slack=slacks, binding=binding,
        message=message, degenerate=degenerate, shadow_prices=shadow, reduced_costs=reduced,
        **common,
    )


def _clean(v: float) -> float:
    return 0.0 if abs(v) < 1e-9 else float(v)


def _sensitivity(model: LPModel, res) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    """Shadow prices and reduced costs in the user's own terms (for Z, max or min).

    HiGHS reports marginals for the problem it actually solved: always a
    minimisation, with every '>=' row negated into a '<=' row. Undoing those
    two sign flips gives dZ / d(rhs) for each constraint as the user wrote it,
    and dZ per unit of a zero variable forced into the plan.
    """
    try:
        ineq = list(res.ineqlin.marginals) if getattr(res, "ineqlin", None) is not None else []
        eq = list(res.eqlin.marginals) if getattr(res, "eqlin", None) is not None else []
        lower = list(res.lower.marginals)
    except AttributeError:
        return None, None                          # older SciPy without marginals
    goal_sign = -1.0 if model.goal == "max" else 1.0
    shadow, i_ub, i_eq = [], 0, 0
    for c in model.constraints:
        if c.sense == "=":
            m, i_eq = eq[i_eq], i_eq + 1
        else:
            m, i_ub = ineq[i_ub], i_ub + 1
        row_sign = -1.0 if c.sense == ">=" else 1.0
        shadow.append(_clean(goal_sign * row_sign * m))
    reduced = [_clean(goal_sign * m) for m in lower]
    return shadow, reduced


# --------------------------------------------------------------------------- #
# Step-by-step explanation
# --------------------------------------------------------------------------- #

def _corner_step(model: LPModel, solution: LPSolution) -> str:
    n, m = model.n_vars, len(model.constraints)
    corners = solution.corner_points or []

    if n == 2:
        header = "Bước 2 -- Các điểm góc của miền khả thi"
        if not corners:
            return (header + "\nKhông có cặp đường biên nào tạo ra một điểm thỏa mãn tất cả "
                    "các ràng buộc: miền khả thi rỗng.")
        rows = [f"   {format_point(p)}  ->  Z = {_num(v)}"
                for p, v in zip(corners, solution.corner_values)]
        return (header + "\nCho từng đường biên giao với các đường biên khác; giữ lại các điểm "
                "thỏa mãn tất cả ràng buộc rồi tính Z tại từng điểm:\n" + "\n".join(rows))

    header = "Bước 2 -- Các điểm góc (đỉnh) của miền khả thi"
    if n == 1:
        intro = (
            f"Với một biến quyết định, miền khả thi là một khoảng trên trục số {model.var_names[0]}, "
            f"và các 'điểm góc' là hai đầu mút của khoảng. Mỗi một trong {m + 1} biên "
            f"(các ràng buộc và {model.var_names[0]} = 0) được giải riêng"
        )
    else:
        what = "không gian 3 chiều" if n == 3 else f"không gian {n} chiều"
        drawable = "có thể được vẽ như một khối" if n == 3 else "không thể vẽ trực tiếp trên mặt phẳng"
        intro = (
            f"Với {n} biến quyết định, miền khả thi nằm trong {what}, nên nó {drawable}. "
            f"Ý tưởng điểm góc vẫn giống hệt trường hợp 2 chiều. Mỗi điểm góc là nơi {n} biên "
            f"giao nhau (ràng buộc hoặc các trục {model.var_names[0]} = 0, ...). "
            f"Đã xét C({m}+{n}, {n}) = {solution.candidates_checked:,} tổ hợp của {n} biên"
        )
    if not corners:
        return (header + "\n" + intro + ", nhưng không có điểm giao nào thỏa mãn tất cả "
                "các ràng buộc: miền khả thi rỗng.")

    shown = min(CORNER_ROWS_SHOWN, len(corners))
    rows = [f"   {i + 1:>2}. {format_point(p, model.var_names)}  ->  Z = {_num(v)}"
            for i, (p, v) in enumerate(zip(corners[:shown], solution.corner_values[:shown]))]
    more = (f"\n   ... và còn {len(corners) - shown} điểm góc có Z "
            f"{'thấp hơn' if model.goal == 'max' else 'cao hơn'}." if len(corners) > shown else "")
    return (header + "\n" + intro + f"; có {len(corners)} điểm thỏa mãn mọi ràng buộc. "
            f"Z tại {shown} điểm góc tốt nhất:\n" + "\n".join(rows) + more
            + "\nHiGHS (bộ giải simplex / điểm trong của SciPy) được dùng để xác nhận nghiệm tối ưu.")


def step_by_step(model: LPModel, solution: LPSolution) -> List[str]:
    steps = []

    model_lines = [model.objective_str(), "với các ràng buộc:"]
    model_lines += ["   " + c.render(model.var_names) for c in model.constraints]
    model_lines.append("   " + ", ".join(model.var_names) + " >= 0")
    steps.append("Bước 1 -- Mô hình\n" + "\n".join(model_lines))

    steps.append(_corner_step(model, solution))

    if solution.is_solved:
        assignment = ", ".join(f"{v} = {_num(x)}" for v, x in zip(model.var_names, solution.x))
        extra = ""
        if solution.status == "multiple_optimal":
            extra += "\n   (Có nhiều nghiệm tối ưu — mọi điểm nằm giữa các điểm góc đồng tối ưu đều có cùng giá trị tối ưu.)"
        if solution.degenerate:
            extra += "\n   (Điểm góc suy biến — có nhiều đường biên đi qua điểm này hơn số đường cần thiết để xác định nó.)"
        steps.append(
            "Bước 3 -- Nghiệm tối ưu\n"
            f"   {assignment}\n"
            f"   Z = {_num(solution.objective_value)}" + extra
        )
        binding_names = [c.name(model.var_names)
                         for c, b in zip(model.constraints, solution.binding) if b]
        slack_rows = [
            f"   {c.label or f'Ràng buộc {i+1}'}: "
            + ("phần dư" if c.sense == ">=" else "độ dư") + f" = {_num(s)}"
            for i, (c, s) in enumerate(zip(model.constraints, solution.slack))
        ]
        steps.append(
            "Bước 4 -- Ràng buộc chặt và độ dư\n"
            + (f"Ràng buộc chặt (đúng tại giới hạn): {', '.join(binding_names)}\n" if binding_names
               else "Không có ràng buộc nào chặt đúng tại nghiệm tối ưu này.\n")
            + "\n".join(slack_rows)
        )
        sens = _sensitivity_step(model, solution)
        if sens:
            steps.append(sens)
    else:
        steps.append(f"Bước 3 -- Kết quả\n   {solution.message}")

    return steps


def _sensitivity_step(model: LPModel, solution: LPSolution) -> Optional[str]:
    if solution.shadow_prices is None:
        return None
    names = [c.label or f"Ràng buộc {i + 1}" for i, c in enumerate(model.constraints)]
    width = min(max(len(n) for n in names), 32)
    rows = []
    for name, sp in zip(names, solution.shadow_prices):
        if sp == 0:
            effect = "không giới hạn nghiệm — thay đổi nhỏ không làm Z thay đổi"
        else:
            direction = "làm tăng" if sp > 0 else "làm giảm"
            effect = f"tăng 1 đơn vị ở vế phải {direction} Z một lượng {_num(abs(sp))}"
        rows.append(f"   {name[:width]:<{width}}  {_num(sp):>9}   {effect}")
    lines = ["Bước 5 -- Phân tích độ nhạy (giá bóng)",
             "Z thay đổi bao nhiêu khi vế phải của một ràng buộc tăng 1 đơn vị, trong khi "
             "các ràng buộc khác giữ nguyên (chỉ đúng với thay đổi nhỏ):"] + rows
    rc_rows = [f"   {v}: buộc đưa 1 đơn vị vào phương án làm Z thay đổi {_num(rc)}"
               for v, x, rc in zip(model.var_names, solution.x, solution.reduced_costs or [])
               if abs(x) < 1e-9 and rc != 0]
    if rc_rows:
        worse = "thấp hơn" if model.goal == "max" else "cao hơn"
        lines.append(f"Chi phí giảm — các biến bằng 0 (sử dụng chúng sẽ làm Z {worse}):")
        lines += rc_rows
    if solution.degenerate:
        lines.append("   Lưu ý: nghiệm tối ưu bị suy biến, nên một số giá bóng chỉ đúng theo một chiều thay đổi.")
    return "\n".join(lines)

