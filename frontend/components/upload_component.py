import streamlit as st
from requests import HTTPError, RequestException

from frontend.api_client.backend_client import BackendClient
from frontend.components.ux_states import page_intro, success_banner


def render_upload(client: BackendClient) -> None:
    page_intro(
        "Upload Dataset",
        "Choose a CSV or Excel file to begin. Next steps: Clean → Dashboard → AI Insights.",
        workflow_index=0,
    )
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xlsm"],
        help="Required: .csv, .xlsx, or .xlsm. Max size follows server MAX_UPLOAD_SIZE_MB.",
    )

    if uploaded_file is not None:
        st.caption(f"Selected: **{uploaded_file.name}** · {uploaded_file.size:,} bytes")
        render_status = st.empty()
        render_status.info("Ready to upload — click the button below.")

    if st.button("Upload dataset", disabled=uploaded_file is None, type="primary"):
        try:
            with st.spinner("Uploading and validating file…"):
                result = client.upload_csv(uploaded_file)
            success_banner(result.get("message") or "Upload complete.")
            st.caption(f"Dataset ID: `{result['dataset_id']}`")
            st.session_state["selected_dataset_id"] = result["dataset_id"]
            st.session_state["active_dataset_id"] = result["dataset_id"]
            c1, c2 = st.columns(2)
            if c1.button("Go to Data Cleaning", use_container_width=True):
                from frontend.utils.session_state import navigate_to

                navigate_to("Data Cleaning")
                st.rerun()
            if c2.button("Open Dashboard", use_container_width=True):
                from frontend.utils.session_state import navigate_to

                navigate_to("Dashboard")
                st.rerun()
        except HTTPError:
            st.error("Upload failed. Check that the file is a valid CSV or Excel workbook, then retry.")
        except RequestException:
            st.error(
                "Backend upload is unavailable. Use **Dataset Preview** for local upload, "
                "or start the API and try again."
            )
