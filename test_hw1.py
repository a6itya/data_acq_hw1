import json
import subprocess

import pandas as pd
from streamlit.testing.v1 import AppTest

import hw1
from user_definition import *


def test_retrieve_data_from_gcs():
    """retrieve_data_from_gcs should return every row from the file in the bucket."""
    data = hw1.retrieve_data_from_gcs(GCP_BUCKET_NAME, GCP_FILE_NAME)
    fields = list(data)
    fields.sort()
    assert isinstance(data, dict)
    assert len(data["results"]) == 15
    assert ["company_dict", "job_title", "results"] == fields


def test_summarize_distribution():
    """
    Test summarize_distribution with dataframe,
    column name, and top_x
    """
    df = pd.DataFrame([{"skills": ["python", "sql"],
                               "job_title" : "data scientist"},
                              {"skills": ["python", "sql", "data pipeline"],
                               "job_title" : "data scientist"},
                              {"skills": ["python"],
                               "job_title" : "AI engineer"}])
    assert hw1.summarize_distribution(df, "skills", 2) == {"python":3, "sql": 2}


def test_dashboard_all_companies_checked():
    """With every checkbox on (the default), all 15 postings should show,
    deduplicated by link, with a working link column."""
    at = AppTest.from_file("hw1.py").run()
    assert at.title[0].value == "Data Engineer Listings and Skills"
    assert all(cb.value for cb in at.sidebar.checkbox)
    assert len(at.dataframe) == 1
    df = at.dataframe[0].value
    assert set(df.columns) == {"date", "title", "skills", "link"}
    assert len(df) == 15
    assert df["link"].is_unique


def test_dashboard_filter_by_single_company(monkeypatch):
    """Unchecking every company except one should leave only that
    company's postings."""
    monkeypatch.setattr(hw1.st, "checkbox",
                        lambda label, **kwargs: label == "Anthropic")

    at = AppTest.from_file("hw1.py").run()
    df = at.dataframe[0].value

    assert len(df) > 0
    assert all("greenhouse.io/anthropic" in link for link in df["link"])


def test_dashboard_no_companies_selected(monkeypatch):
    """Unchecking every company should show an empty table, not every
    row."""
    monkeypatch.setattr(hw1.st, "checkbox", lambda *a, **k: False)

    at = AppTest.from_file("hw1.py").run()
    df = at.dataframe[0].value

    assert df.empty


def test_dashboard_sorted_newest_first():
    at = AppTest.from_file("hw1.py").run()
    df = at.dataframe[0].value

    dates = list(df["date"])
    assert dates == sorted(dates, reverse=True)


def test_dashboard_shows_skill_chart():
    """The skills bar chart (st.bar_chart) should render below the table."""
    at = AppTest.from_file("hw1.py").run()
    # st.bar_chart isn't a typed AppTest widget
    # it shows up as an UnknownElement wrapping 
    # an ArrowVegaLiteChart proto.
    chart_protos = [el.proto for el in at.main
                    if type(el).__name__ == "UnknownElement"]
    assert any(proto.DESCRIPTOR.name == "ArrowVegaLiteChart"
              for proto in chart_protos)


def test_dashboard_uses_link_column():
    at = AppTest.from_file("hw1.py").run()
    # Streamlit's dataframe widget stores per-column display config as a
    # JSON string on proto.columns.
    # LinkColumn shows up as {"type_config": {"type": "link"}} under its column name.
    columns_config = json.loads(at.dataframe[0].proto.columns)
    assert columns_config.get("link", {}).get("type_config", {}).get("type") == "link"


def test_hw1_pep8():
    """Ensure code passes pycodestyle with fewer than 5 issues."""
    result = subprocess.run(
        ["pycodestyle", "hw1.py"],
        capture_output=True,
        text=True,
    )
    errors = result.stdout.strip().splitlines()
    assert len(errors) < 5, f"Too many PEP8 issues:\n{errors}"
