"""Toy Streamlit app students can customize for STAT 386 projects."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import pandas as pd
import streamlit as st

from fbi_wanted_analysis.analysis import add, run_analysis_pipeline
from fbi_wanted_analysis.cleaning import run_cleaning_pipeling


def _sample_data() -> pd.DataFrame:
    """Small placeholder dataset for rapid UI feedback."""
    return pd.DataFrame(
        {
            "team": ["alpha", "beta", "gamma"],
            "metric_a": [0.72, 0.55, 0.91],
            "metric_b": [12, 9, 17],
        }
    )


def _run_with_capture(func) -> str:
    """Capture stdout from placeholder pipelines so Streamlit can display it."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        func()
    return buffer.getvalue().strip()


def main() -> None:
    st.set_page_config(page_title="STAT 386 Prototype", layout="wide")
    st.title("STAT 386 Project Prototype")
    st.write(
        "Use this template Streamlit app as a quick sandbox. Replace the sample data, "
        "plug in your cleaning pipeline, and surface the most important visuals for your final deliverable."
    )

    with st.sidebar:
        st.header("Controls")
        dataset_choice = st.selectbox("Dataset", ["Sample Data", "Upload CSV"])
        show_cleaning = st.checkbox("Preview cleaning pipeline output")
        show_analysis = st.checkbox("Preview analysis pipeline output")
        a = st.number_input("Toy add() input A", value=1)
        b = st.number_input("Toy add() input B", value=2)

    if dataset_choice == "Sample Data":
        df = _sample_data()
    else:
        uploaded = st.file_uploader("Upload a CSV file", type="csv")
        if uploaded:
            df = pd.read_csv(uploaded)
        else:
            st.info("No file uploaded yet. Falling back to the sample data so the widgets stay live.")
            df = _sample_data()

    st.subheader("Data Preview")
    st.dataframe(df, use_container_width=True)

    st.subheader("Quick Math Sandbox")
    st.write(
        "The package's `add` helper is wired up below so students can see how to surface custom utilities."
    )
    st.metric(label="add(a, b)", value=add(a, b))

    if show_cleaning:
        st.subheader("Cleaning Pipeline Output")
        cleaning_output = _run_with_capture(run_cleaning_pipeling)
        st.code(cleaning_output or "run_cleaning_pipeling() did not emit text.")
        st.caption("Replace run_cleaning_pipeling with your real preprocessing logic.")

    if show_analysis:
        st.subheader("Analysis Pipeline Output")
        analysis_output = _run_with_capture(run_analysis_pipeline)
        st.code(analysis_output or "run_analysis_pipeline() did not emit text.")
        st.caption("Swap this stub with charts, metrics, or model diagnostics from your project.")

    st.info(
        "Next steps: customize the sidebar controls, drop in Streamlit charts (st.bar_chart, st.map, etc.), "
        "and layer in explanations so stakeholders can self-serve results."
    )


if __name__ == "__main__":
    main()
