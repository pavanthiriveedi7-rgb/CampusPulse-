from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="CampusPulse",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    @import url(
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
    );

    html, body, [class*="css"] {
        font-family: "Inter", sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background: #f8fafc;
    }

    [data-testid="stSidebar"] {
        background: #0b1220;
    }

    [data-testid="stSidebar"] * {
        color: #e2e8f0;
    }

    h1, h2, h3 {
        color: #0f172a;
    }

    .brand-title {
        color: white;
        font-size: 24px;
        font-weight: 800;
    }

    .brand-subtitle {
        color: #94a3b8;
        font-size: 12px;
    }

    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 22px;
        min-height: 135px;
        box-shadow: 0 8px 25px rgba(15, 23, 42, 0.06);
    }

    .metric-label {
        color: #64748b;
        font-size: 13px;
        font-weight: 600;
    }

    .metric-value {
        color: #0f172a;
        font-size: 31px;
        font-weight: 800;
        margin-top: 8px;
    }

    .metric-change {
        font-size: 13px;
        font-weight: 600;
        margin-top: 8px;
    }

    .welcome-box {
        background: linear-gradient(135deg, #172554, #2563eb);
        border-radius: 22px;
        padding: 28px;
        color: white;
        margin-bottom: 25px;
    }

    .welcome-title {
        color: white;
        font-size: 28px;
        font-weight: 800;
    }

    .welcome-text {
        color: #dbeafe;
        margin-top: 8px;
    }

    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


DATA_PATH = Path("data/R23_R24_structured.xlsx")


GRADE_POINTS = {
    "O": 10,
    "S": 10,
    "A+": 9,
    "A": 8,
    "B": 7,
    "C": 6,
    "D": 5,
    "E": 4,
    "F": 0,
    "ABSENT": 0,
    "AB": 0,
    "WH": 0,
    "MP": 0,
    "COMPLE": 0,
}


@st.cache_data
def load_raw_data():
    """Load the CSV file."""

    if not DATA_PATH.exists():
        return None

    try:
        return pd.read_csv(
            DATA_PATH,
            header=None,
            dtype=str,
            encoding="utf-8",
            on_bad_lines="skip",
        )
    except UnicodeDecodeError:
        return pd.read_csv(
            DATA_PATH,
            header=None,
            dtype=str,
            encoding="latin1",
            on_bad_lines="skip",
        )


@st.cache_data
def extract_result_rows(raw_data):
    """Find rows containing hall-ticket, subject, grade, and credits."""

    columns = [
        "RegdNo",
        "Subcode",
        "Subject",
        "Internals",
        "Grade",
        "Credits",
    ]

    if raw_data is None or raw_data.empty:
        return pd.DataFrame(columns=columns)

    records = []

    for _, row in raw_data.iterrows():
        values = [
            str(value).strip()
            for value in row.tolist()
            if pd.notna(value) and str(value).strip()
        ]

        if len(values) < 6:
            continue

        for i in range(len(values) - 5):
            hall_ticket = values[i]
            subcode = values[i + 1]
            subject = values[i + 2]
            internals = values[i + 3]
            grade = values[i + 4].upper()
            credits_text = values[i + 5]

            is_hall_ticket = (
                len(hall_ticket) >= 8
                and hall_ticket[0].isdigit()
                and "MC" in hall_ticket.upper()
            )

            is_subcode = (
                subcode.startswith("R")
                and len(subcode) >= 5
            )

            is_grade = grade in GRADE_POINTS

            try:
                credits = float(credits_text)
            except ValueError:
                continue

            if (
                is_hall_ticket
                and is_subcode
                and is_grade
                and credits >= 0
            ):
                records.append(
                    {
                        "RegdNo": hall_ticket,
                        "Subcode": subcode,
                        "Subject": subject,
                        "Internals": internals,
                        "Grade": grade,
                        "Credits": credits,
                    }
                )

    if not records:
        return pd.DataFrame(columns=columns)

    result = pd.DataFrame(records).drop_duplicates()

    result["GradePoint"] = result["Grade"].map(GRADE_POINTS)

    failed_grades = {"F", "ABSENT", "AB", "WH", "MP"}

    result["Status"] = result["Grade"].apply(
        lambda grade: (
            "Needs Attention"
            if grade in failed_grades
            else "Passed"
        )
    )

    return result.reset_index(drop=True)


def calculate_sgpa(student_results):
    """Calculate credit-weighted SGPA."""

    if student_results.empty:
        return 0.0

    failed_grades = {"F", "ABSENT", "AB", "WH", "MP"}

    passed = student_results[
        ~student_results["Grade"].isin(failed_grades)
    ]

    if passed.empty:
        return 0.0

    total_credits = passed["Credits"].sum()

    if total_credits == 0:
        return 0.0

    total_points = (
        passed["GradePoint"] * passed["Credits"]
    ).sum()

    return round(total_points / total_credits, 2)


def metric_card(label, value, description, color="#10b981"):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-change" style="color:{color}">
                {description}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        """
        <div>
            <div class="brand-title">🎓 CampusPulse</div>
            <div class="brand-subtitle">
                Academic Intelligence Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Results Explorer",
            "SGPA / CGPA Studio",
            "Backlog Center",
            "Performance Analytics",
            "AI Academic Coach",
        ],
    )

    st.divider()
    st.caption("Student Portal")
    st.caption("Prototype Version 1.0")


raw_data = load_raw_data()
result_data = extract_result_rows(raw_data)


if page == "Overview":
    st.markdown(
        """
        <div class="welcome-box">
            <div class="welcome-title">Good evening 👋</div>
            <div class="welcome-text">
                Track your results, credits, SGPA, CGPA, and academic progress.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    hall_ticket = st.text_input(
        "Enter Hall-Ticket Number",
        placeholder="Example: 23MC1A4459",
    ).strip().upper()

    if hall_ticket and not result_data.empty:
        selected_results = result_data[
            result_data["RegdNo"].str.upper() == hall_ticket
        ]
    else:
        selected_results = result_data

    if hall_ticket and selected_results.empty:
        st.warning("No result records found.")

    sgpa = calculate_sgpa(selected_results)

    failed_grades = {"F", "ABSENT", "AB", "WH", "MP"}

    if selected_results.empty:
        passed_credits = 0
        backlog_count = 0
        subject_count = 0
    else:
        passed = selected_results[
            ~selected_results["Grade"].isin(failed_grades)
        ]

        passed_credits = round(float(passed["Credits"].sum()), 2)
        backlog_count = int(
            selected_results["Grade"].isin(failed_grades).sum()
        )
        subject_count = len(selected_results)

    st.markdown("### Academic Snapshot")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card(
            "Calculated SGPA",
            f"{sgpa:.2f}" if not selected_results.empty else "—",
            "Prototype calculation",
        )

    with col2:
        metric_card(
            "Subjects",
            subject_count,
            "Records detected",
            "#2563eb",
        )

    with col3:
        metric_card(
            "Credits Earned",
            passed_credits,
            "From passed subjects",
            "#7c3aed",
        )

    with col4:
        metric_card(
            "Backlogs",
            backlog_count,
            "Needs attention"
            if backlog_count
            else "No backlog detected",
            "#f59e0b"
            if backlog_count
            else "#10b981",
        )

    st.markdown("### Academic Records")

    if selected_results.empty:
        st.info(
            "Enter a hall-ticket number or upload the CSV file to view results."
        )
    else:
        st.dataframe(
            selected_results[
                [
                    "RegdNo",
                    "Subcode",
                    "Subject",
                    "Grade",
                    "Credits",
                    "Status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


elif page == "Results Explorer":
    st.title("Results Explorer")
    st.write("Search your academic records.")

    if raw_data is None:
        st.error(
            "CSV file not found. Confirm that it exists at "
            "data/combinepdf.csv."
        )
    else:
        hall_ticket = st.text_input(
            "Search by Hall-Ticket Number",
            placeholder="Example: 23MC1A4459",
        ).strip().upper()

        filtered_data = result_data.copy()

        if hall_ticket:
            filtered_data = filtered_data[
                filtered_data["RegdNo"].str.upper() == hall_ticket
            ]

        if filtered_data.empty:
            st.info("No structured result records found.")
        else:
            st.success(
                f"{len(filtered_data)} result records found."
            )

            st.dataframe(
                filtered_data,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download Results",
                data=filtered_data.to_csv(index=False),
                file_name="student_results.csv",
                mime="text/csv",
            )

        with st.expander("Show raw CSV preview"):
            st.dataframe(
                raw_data.head(50),
                use_container_width=True,
            )


elif page == "SGPA / CGPA Studio":
    st.title("SGPA / CGPA Studio")

    hall_ticket = st.text_input(
        "Hall-Ticket Number",
        placeholder="Example: 23MC1A4459",
    ).strip().upper()

    if hall_ticket:
        student_results = result_data[
            result_data["RegdNo"].str.upper() == hall_ticket
        ]

        if student_results.empty:
            st.warning("No records found.")
        else:
            sgpa = calculate_sgpa(student_results)

            col1, col2, col3 = st.columns(3)

            with col1:
                metric_card(
                    "Calculated SGPA",
                    f"{sgpa:.2f}",
                    "Credit-weighted",
                )

            with col2:
                passed = student_results[
                    ~student_results["Grade"].isin(
                        {"F", "ABSENT", "AB", "WH", "MP"}
                    )
                ]

                metric_card(
                    "Passed Credits",
                    passed["Credits"].sum(),
                    "Credits completed",
                    "#7c3aed",
                )

            with col3:
                metric_card(
                    "Total Subjects",
                    len(student_results),
                    "Records detected",
                    "#2563eb",
                )

            st.markdown("### Calculation Details")

            st.dataframe(
                student_results[
                    [
                        "Subcode",
                        "Subject",
                        "Grade",
                        "GradePoint",
                        "Credits",
                        "Status",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.info(
                "This is a prototype SGPA calculation. Confirm the official "
                "grade-point rules before using it as an official result."
            )


elif page == "Backlog Center":
    st.title("Backlog Center")

    hall_ticket = st.text_input(
        "Hall-Ticket Number",
        placeholder="Example: 23MC1A4459",
    ).strip().upper()

    if hall_ticket:
        student_results = result_data[
            result_data["RegdNo"].str.upper() == hall_ticket
        ]

        backlog_data = student_results[
            student_results["Grade"].isin(
                {"F", "ABSENT", "AB", "WH", "MP"}
            )
        ]

        if backlog_data.empty:
            st.success("No backlog records detected.")
        else:
            st.warning(
                f"{len(backlog_data)} record(s) need attention."
            )

            st.dataframe(
                backlog_data[
                    [
                        "Subcode",
                        "Subject",
                        "Grade",
                        "Credits",
                        "Status",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )


elif page == "Performance Analytics":
    st.title("Performance Analytics")

    if result_data.empty:
        st.info("No structured result data is available.")
    else:
        grade_counts = (
            result_data["Grade"]
            .value_counts()
            .rename_axis("Grade")
            .reset_index(name="Count")
        )

        chart = px.bar(
            grade_counts,
            x="Grade",
            y="Count",
            color="Grade",
            title="Grade Distribution",
        )

        chart.update_layout(
            height=420,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(
            chart,
            use_container_width=True,
        )


elif page == "AI Academic Coach":
    st.title("AI Academic Coach")

    st.info(
        "AI recommendations will be added after results are separated "
        "by student, semester, regulation, and examination session."
    )

    st.markdown("### Planned Features")

    st.write("• Subject-risk detection")
    st.write("• Target SGPA calculation")
    st.write("• Weekly study plan")
    st.write("• Backlog improvement suggestions")
    st.write("• Academic performance prediction")


st.divider()

st.caption(
    "CampusPulse is a prototype. Calculated values are not official "
    "university results."
)
