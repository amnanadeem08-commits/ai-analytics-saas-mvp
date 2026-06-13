import streamlit as st
from requests import HTTPError, RequestException

from frontend.api_client.backend_client import BackendClient


def render_upload(client: BackendClient) -> None:
    st.header("Upload Dataset")
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xlsm"])

    if uploaded_file is not None:
        st.caption(f"Selected file: {uploaded_file.name}")

    if st.button("Upload dataset", disabled=uploaded_file is None):
        try:
            result = client.upload_csv(uploaded_file)
            st.success(result["message"])
            st.code(result["dataset_id"])
            st.session_state["selected_dataset_id"] = result["dataset_id"]
        except HTTPError as exc:
            detail = exc.response.json().get("detail", str(exc)) if exc.response is not None else str(exc)
            st.error(f"Upload failed: {detail}")
        except RequestException as exc:
            st.error(f"Could not connect to backend: {exc}")
