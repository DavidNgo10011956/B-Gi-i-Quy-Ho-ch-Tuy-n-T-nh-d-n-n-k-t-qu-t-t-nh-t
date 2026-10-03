"""Input guide tables, example problems and terminal banner for the LP solver.

Laid out the same way as integral_input_guide.py so every program in the
toolkit shows its guide in the same format. The layout helpers (WIDTH, hr,
format_table) live in lp_utils.py and are shared with the integral guide:
    hr() · banner(show_special) · input / symbol / example tables ·
    a special-cases guide · a detector that returns a plain-English note.
"""

from __future__ import annotations

from lp_engine import MAX_CONSTRAINTS, MAX_VARIABLES   # single source of truth
from lp_utils import WIDTH, hr, format_table


# ---------------------------------------------------------------------------
# Special-case catalogue  (shown when the user wants the advanced guide)
# ---------------------------------------------------------------------------

SPECIAL_CASES: list[dict[str, str]] = [
    {
        "name": "Không khả thi",
        "symbol": "∅ miền",
        "meaning": "Các ràng buộc mâu thuẫn nhau — không có phương án nào thỏa mãn tất cả.",
        "spot": "Không có miền màu xanh và không có nghiệm tối ưu.",
        "example": "x + y <= 10 đồng thời với x + y >= 20",
    },
    {
        "name": "Không bị chặn",
        "symbol": "Z → ∞",
        "meaning": "Miền khả thi mở theo một hướng khiến Z có thể tiếp tục cải thiện vô hạn.",
        "spot": "Thường do thiếu giới hạn năng lực (max) hoặc yêu cầu tối thiểu (min).",
        "example": "max Z = x + y chỉ với x - y <= 10",
    },
    {
        "name": "Nhiều nghiệm tối ưu",
        "symbol": "Z bằng nhau",
        "meaning": "Hai hoặc nhiều điểm góc cho cùng Z tốt nhất — mọi điểm nằm giữa chúng cũng vậy.",
        "spot": "Đường hàm mục tiêu song song với một ràng buộc chặt.",
        "example": "max Z = 2x + 4y với x + 2y <= 10, x <= 6",
    },
    {
        "name": "Suy biến",
        "symbol": "đường biên dư",
        "meaning": "Có nhiều đường biên đi qua điểm tối ưu hơn số đường cần thiết để xác định điểm đó.",
        "spot": "Tại nghiệm tối ưu, một ràng buộc chặt đồng thời có một biến bằng 0.",
        "example": "max Z = 3x + 2y với x + y <= 4, x <= 4",
    },
    {
        "name": "Ràng buộc dư thừa",
        "symbol": "độ dư > 0",
        "meaning": "Ràng buộc không bao giờ chạm miền khả thi — bỏ nó đi không làm thay đổi kết quả.",
        "spot": "Đường của nó nằm hoàn toàn ngoài miền màu xanh; độ dư luôn dương.",
        "example": "x + y <= 8 làm cho 2x + 2y <= 20 trở thành dư thừa",
    },
]


def special_case_guide() -> str:
    """Trả về hướng dẫn cho các trường hợp đặc biệt / nâng cao."""
    lines: list[str] = [
        "",
        "CÁC TRƯỜNG HỢP ĐẶC BIỆT  (nâng cao — đa số bài tập có một nghiệm tối ưu rõ ràng)",
        "-" * 72,
        "Các trường hợp này được phát hiện tự động. Chương trình vẫn liệt kê mọi",
        "điểm góc tìm được và giải thích kết quả bằng ngôn ngữ dễ hiểu.",
        "",
    ]
    for case in SPECIAL_CASES:
        lines.append(f"  {case['name']:<18}  {case['symbol']}")
        lines.append(f"  {'':18}  Ý nghĩa       : {case['meaning']}")
        lines.append(f"  {'':18}  Cách nhận biết : {case['spot']}")
        lines.append(f"  {'':18}  Ví dụ          : {case['example']}")
        lines.append("")
    return "\n".join(lines)


def is_special_case(status: str, degenerate: bool = False) -> str | None:
    """Trả về giải thích tiếng Việt nếu kết quả thuộc trường hợp đặc biệt."""
    checks = {
        "infeasible": "Không khả thi — các ràng buộc mâu thuẫn nhau, nên không có phương án nào thỏa mãn tất cả. Hãy kiểm tra chiều của từng dấu <= / >=.",
        "unbounded": "Không bị chặn — Z có thể tiếp tục cải thiện vô hạn. Bài toán thực tế thường có một giới hạn chưa được nhập (năng lực, ngân sách, nhu cầu, ...).",
        "multiple_optimal": "Nhiều nghiệm tối ưu — hàm mục tiêu song song với một ràng buộc chặt, nên nhiều phương án cho cùng Z tốt nhất. Bất kỳ phương án nào trong số đó cũng đúng.",
    }
    notes = [checks[status]] if status in checks else []
    if degenerate:
        notes.append("Suy biến — có nhiều đường biên gặp nhau tại điểm tối ưu hơn mức cần thiết. Kết quả vẫn đúng; phương pháp simplex có thể dừng tạm tại đó.")
    return "\n".join(notes) if notes else None


# ---------------------------------------------------------------------------
# Example problems  (Basic = teaching-slide examples, larger ones use 3-8 variables)
# ---------------------------------------------------------------------------

def example_problems() -> list[dict]:
    return [
        # Basic -- from the "Linear Programming -- Teaching Notes" slide deck
        {
            "level": "Cơ bản",
            "name": "Ví dụ mẫu — Bài toán nhà máy",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [40, 30],
            "constraints": [
                "2x + y <= 100 # công suất máy 1",
                "x + 2y <= 80 # công suất máy 2",
            ],
        },
        {
            "level": "Cơ bản",
            "name": "Bài tập 1 — Khởi động",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [5, 4],
            "constraints": [
                "x + y <= 8",
                "2x + y <= 10",
            ],
        },
        {
            "level": "Cơ bản",
            "name": "Bài tập 2 — Lập kế hoạch sản xuất",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [60, 45],
            "constraints": [
                "3x + 2y <= 120 # lao động",
                "2x + 4y <= 160 # nguyên vật liệu",
            ],
        },
        {
            "level": "Cơ bản",
            "name": "Bài tập 3 — Phân bổ đất nông nghiệp",
            "var_names": ["w", "c"],
            "goal": "max",
            "objective": [500, 400],
            "constraints": [
                "w + c <= 100 # số hecta có sẵn",
                "3w + 2c <= 240 # lao động units",
            ],
        },
        # Intermediate -- 3 and 4 variables
        {
            "level": "Trung cấp",
            "name": "Xưởng nội thất (bàn, ghế, bàn làm việc)",
            "var_names": ["t", "c", "d"],
            "goal": "max",
            "objective": [70, 30, 90],
            "constraints": [
                "4t + 2c + 6d <= 240 # giờ mộc",
                "2t + c + 2d <= 100 # giờ hoàn thiện",
                "t + c + d <= 45 # sức chứa kho",
            ],
        },
        {
            "level": "Trung cấp",
            "name": "Bài toán dinh dưỡng — khẩu phần lành mạnh chi phí thấp nhất",
            "var_names": ["oats", "milk", "eggs", "beans"],
            "goal": "min",
            "objective": [0.3, 0.9, 0.5, 0.6],
            "constraints": [
                "10oats + 8milk + 13eggs + 15beans >= 60 # protein (g)",
                "380oats + 150milk + 155eggs + 340beans >= 2000 # năng lượng (kcal)",
                "10oats + 0milk + 0eggs + 16beans >= 25 # chất xơ (g)",
                "oats <= 4 # số khẩu phần yến mạch tối đa",
            ],
        },
        # Advanced -- 5 to 8 variables
        {
            "level": "Nâng cao",
            "name": "Danh mục đầu tư (5 quỹ, 100 nghìn USD)",
            "var_names": ["bonds", "blue", "growth", "intl", "cash"],
            "goal": "max",
            "objective": [0.04, 0.07, 0.11, 0.095, 0.02],
            "constraints": [
                "bonds + blue + growth + intl + cash = 100 # tổng vốn đầu tư (nghìn USD)",
                "growth + intl <= 40 # giới hạn tài sản rủi ro cao",
                "bonds + cash >= 25 # mức tối thiểu tài sản an toàn",
                "cash >= 5 # tiền mặt dự phòng",
                "growth - blue <= 0 # quỹ tăng trưởng không vượt quỹ blue-chip",
            ],
        },
        {
            "level": "Nâng cao",
            "name": "Vận chuyển — 2 nhà máy đến 3 cửa hàng",
            "var_names": ["a1", "a2", "a3", "b1", "b2", "b3"],
            "goal": "min",
            "objective": [4, 6, 9, 5, 3, 7],
            "constraints": [
                "a1 + a2 + a3 <= 250 # nguồn cung nhà máy A",
                "b1 + b2 + b3 <= 300 # nguồn cung nhà máy B",
                "a1 + b1 >= 150 # nhu cầu cửa hàng 1",
                "a2 + b2 >= 180 # nhu cầu cửa hàng 2",
                "a3 + b3 >= 170 # nhu cầu cửa hàng 3",
            ],
        },
        {
            "level": "Nâng cao",
            "name": "Phối hợp sản phẩm tiệm bánh (8 sản phẩm)",
            "var_names": ["bread", "rolls", "bagel", "croiss", "muffin", "cookie", "cake", "pie"],
            "goal": "max",
            "objective": [2.0, 1.5, 1.8, 2.6, 2.2, 1.2, 9.0, 7.5],
            "constraints": [
                "0.5bread + 0.3rolls + 0.4bagel + 0.35croiss + 0.25muffin + 0.1cookie + 1.2cake + 0.9pie <= 180 # bột mì (kg)",
                "0.05croiss + 0.04muffin + 0.03cookie + 0.3cake + 0.25pie + 0.01bread <= 30 # bơ (kg)",
                "0.1bread + 0.08rolls + 0.12bagel + 0.2croiss + 0.15muffin + 0.05cookie + 0.6cake + 0.5pie <= 90 # giờ lò nướng",
                "0.05bread + 0.05rolls + 0.1bagel + 0.25croiss + 0.1muffin + 0.04cookie + 0.8cake + 0.6pie <= 80 # lao động hours",
                "bread >= 60 # đơn hàng bánh mì cố định",
                "cake <= 20 # nhu cầu bánh kem",
                "pie <= 25 # nhu cầu bánh pie",
                "cookie >= 100 # hợp đồng bánh quy",
            ],
        },
        # Special -- the unusual outcomes described in the special-cases guide
        {
            "level": "Đặc biệt",
            "name": "Ví dụ không khả thi",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [1, 1],
            "constraints": [
                "x + y <= 10",
                "x + y >= 20",
            ],
        },
        {
            "level": "Đặc biệt",
            "name": "Ví dụ không bị chặn",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [1, 1],
            "constraints": [
                "x - y <= 10",
            ],
        },
        {
            "level": "Đặc biệt",
            "name": "Nghiệm tối ưu suy biến",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [3, 2],
            "constraints": [
                "x + y <= 4",
                "x <= 4",
            ],
        },
        {
            "level": "Đặc biệt",
            "name": "Nhiều nghiệm tối ưu",
            "var_names": ["x", "y"],
            "goal": "max",
            "objective": [2, 4],
            "constraints": [
                "x + 2y <= 10",
                "x <= 6",
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Standard input / symbol guides
# ---------------------------------------------------------------------------

def input_guide_rows() -> list[dict[str, str]]:
    """Professional guide table to reduce input errors."""
    return [
        {"Biểu thức toán học": "Max Z = 40x + 30y",   "Ý nghĩa": "hàm mục tiêu cần tối đa hóa",            "Cách nhập": "max, then 40x + 30y"},
        {"Biểu thức toán học": "Min C = 3a + 5b",     "Ý nghĩa": "hàm mục tiêu cần tối thiểu hóa",            "Cách nhập": "min, then 3a + 5b"},
        {"Biểu thức toán học": "Z = 40x + 30y",       "Ý nghĩa": "hàm mục tiêu dạng danh sách hệ số",       "Cách nhập": "40, 30"},
        {"Biểu thức toán học": "2x + y ≤ 100",        "Ý nghĩa": "không vượt quá (năng lực / giới hạn)",       "Cách nhập": "2x + y <= 100"},
        {"Biểu thức toán học": "x + 2y ≥ 40",         "Ý nghĩa": "ít nhất (yêu cầu tối thiểu)",           "Cách nhập": "x + 2y >= 40"},
        {"Biểu thức toán học": "x + y = 50",          "Ý nghĩa": "bằng đúng (tổng cố định)",            "Cách nhập": "x + y = 50"},
        {"Biểu thức toán học": "3x₁ + 2x₂ − x₃ ≤ 60", "Ý nghĩa": "ba biến, có dấu trừ",      "Cách nhập": "3x1 + 2x2 - x3 <= 60"},
        {"Biểu thức toán học": "0.5x + 1.25y ≤ 20",   "Ý nghĩa": "hệ số thập phân",             "Cách nhập": "0.5x + 1.25y <= 20"},
        {"Biểu thức toán học": "x ≤ 30",              "Ý nghĩa": "giới hạn cho một biến",       "Cách nhập": "x <= 30"},
        {"Biểu thức toán học": "x ≥ y",               "Ý nghĩa": "so sánh hai biến",            "Cách nhập": "x - y >= 0"},
        {"Biểu thức toán học": "2x + 3y ≤ 100 Labour","Ý nghĩa": "đặt tên nguồn lực để hiển thị trong báo cáo", "Cách nhập": "2x + 3y <= 100 # Labour"},
        {"Biểu thức toán học": "x₁, x₂, …, x₈",       "Ý nghĩa": f"1 to {MAX_VARIABLES} variable names",           "Cách nhập": "x1, x2, x3"},
        {"Biểu thức toán học": "x, y ≥ 0",            "Ý nghĩa": "điều kiện không âm",                   "Cách nhập": "tự động — không cần nhập"},
    ]


def symbol_guide_rows() -> list[dict[str, str]]:
    """Guide table explaining the symbols the constraint parser understands."""
    return [
        {"Symbol": "<=",    "Ý nghĩa": "nhỏ hơn hoặc bằng (≤)",      "Ví dụ": "2x + y <= 100"},
        {"Symbol": ">=",    "Ý nghĩa": "lớn hơn hoặc bằng (≥)",   "Ví dụ": "x + y >= 20"},
        {"Symbol": "=",     "Ý nghĩa": "bằng đúng",               "Ví dụ": "x + y = 50"},
        {"Symbol": "+  -",  "Ý nghĩa": "cộng / trừ các hạng tử",        "Ví dụ": "3x1 - x2 + 2x3"},
        {"Symbol": "*",     "Ý nghĩa": "phép nhân (không bắt buộc)",   "Ví dụ": "3*x và 3x đều được chấp nhận"},
        {"Symbol": ".",     "Ý nghĩa": "dấu thập phân",               "Ví dụ": "0.75x + 1.5y <= 12"},
        {"Symbol": ",",     "Ý nghĩa": "phân cách tên / số",   "Ví dụ": "x, y, z   hoặc   40, 30, 25"},
        {"Symbol": "#",     "Ý nghĩa": "bắt đầu nhãn tùy chọn",    "Ví dụ": "x + y <= 8 # hours"},
        {"Symbol": "<  >",  "Ý nghĩa": "được hiểu là <= / >= (LP không dùng bất đẳng thức nghiêm ngặt)", "Ví dụ": "x < 30 được giải như x <= 30"},
    ]


def example_rows() -> list[dict[str, str]]:
    """The example problems as table rows, grouped by difficulty."""
    rows = []
    for i, ex in enumerate(example_problems(), start=1):
        rows.append({
            "Mức độ": ex["level"],
            "Ví dụ": f"{i:>2}. {ex['name']}",
            "Kích thước": f"{len(ex['var_names'])} × {len(ex['constraints'])}",
        })
    return rows



def banner(show_special: bool = False) -> str:
    """Return the professional startup/help banner.

    Parameters
    ----------
    show_special:
        When True, append the special-cases reference section.
    """
    lines: list[str] = [
        hr(),
        f"{'PROFESSIONAL LINEAR PROGRAMMING SOLVER':^{WIDTH}}",
        f"{'Interactive Terminal Edition':^{WIDTH}}",
        f"{f'Up to {MAX_VARIABLES} decision variables · up to {MAX_CONSTRAINTS} constraints':^{WIDTH}}",
        hr(),
        "",
        "HƯỚNG DẪN NHẬP DỮ LIỆU",
        "",
    ]
    lines.extend(
        format_table(
            ["Biểu thức toán học", "Ý nghĩa", "Cách nhập"],
            input_guide_rows(),
            ["Biểu thức toán học", "Ý nghĩa", "Cách nhập"],
            [23, 33, 26],
        )
    )
    lines.extend(["", "HƯỚNG DẪN KÝ HIỆU", ""])
    lines.extend(
        format_table(
            ["Symbol", "Ý nghĩa", "Ví dụ"],
            symbol_guide_rows(),
            ["Symbol", "Ý nghĩa", "Ví dụ"],
            [10, 28, 36],
        )
    )
    lines.extend(["", "CÁC BÀI TOÁN VÍ DỤ ĐỂ THỬ", ""])
    lines.extend(
        format_table(
            ["Mức độ", "Ví dụ", "Biến × Ràng buộc"],
            example_rows(),
            ["Mức độ", "Ví dụ", "Kích thước"],
            [14, 50, 16],
        )
    )
    lines.extend(
        [
            "",
            "Lệnh:",
            "  example        - nạp một bài toán ví dụ ở trên",
            "  own            - tự xây dựng mô hình từng bước",
            "  help           - hiển thị lại hướng dẫn này",
            "  special        - xem hướng dẫn các trường hợp đặc biệt (không khả thi, không bị chặn, ...)",
            "  quit  / exit   - đóng chương trình",
            "",
            "Mẹo: Giữ các biến ở vế trái và chỉ một số ở vế phải của mỗi ràng buộc.",
            "Mẹo: Ứng dụng chấp nhận nhiều cách nhập — thử 3x + 2y ≤ 60 hoặc 3*x+2*y=<60.",
            "Mẹo: 2 biến sẽ vẽ miền khả thi; 3 biến vẽ 3D; 4–8 biến hiển thị biểu đồ nghiệm.",
            "Mẹo: Bước 5 của mỗi báo cáo liệt kê giá bóng — giá trị của việc có thêm 1 đơn vị nguồn lực.",
            "Mẹo: Gõ quit tại bất kỳ lời nhắc nào khi đang tạo mô hình để quay về menu.",
        ]
    )
    if show_special:
        lines.append(special_case_guide())
    lines.append(hr())
    return "\n".join(lines)
