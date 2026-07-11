from __future__ import annotations

"""Knowledge Center — ingest/search/list/delete via knowledge API."""

import streamlit as st

from frontend.components.ux_states import empty_state, page_intro, section_header, success_banner
from frontend.utils.workspace_api import get_workspace_clients, show_api_error


def render_knowledge_center(client=None) -> None:
    page_intro(
        "Knowledge Center",
        "Manage RAG knowledge documents through `/api/v1/knowledge/*`.",
        workflow_index=4,
    )

    knowledge = get_workspace_clients()["knowledge"]

    tab_ingest, tab_search, tab_docs = st.tabs(["Ingest", "Search", "Documents"])

    with tab_ingest:
        section_header("Add knowledge", "Title and content are required")
        title = st.text_input("Title")
        content = st.text_area("Content", height=180)
        c1, c2 = st.columns(2)
        with c1:
            source = st.text_input("Source", value="manual")
        with c2:
            tags_raw = st.text_input("Tags (comma-separated)", value="")
        if st.button("Ingest document", type="primary"):
            if not title.strip() or not content.strip():
                st.warning("Title and content are required.")
            else:
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                try:
                    result = knowledge.ingest(
                        title=title.strip(),
                        content=content.strip(),
                        source=source.strip() or "manual",
                        tags=tags,
                    )
                    success_banner(
                        f"Ingested `{result.get('document_id')}` "
                        f"({result.get('chunk_count', 0)} chunks)"
                    )
                except Exception as exc:
                    show_api_error(exc)

    with tab_search:
        section_header("Search", "Filter relevance with Top K")
        row = st.columns([3, 1, 1])
        with row[0]:
            query = st.text_input("Search query", key="knowledge_search_query", label_visibility="collapsed", placeholder="Search knowledge…")
        with row[1]:
            top_k = st.number_input("Top K", min_value=1, max_value=20, value=5)
        with row[2]:
            run_search = st.button("Search", type="primary", use_container_width=True)

        if run_search:
            if not query.strip():
                st.warning("Enter a search query.")
            else:
                try:
                    result = knowledge.search(query.strip(), top_k=int(top_k))
                    chunks = result.get("chunks") or []
                    st.caption(f"Found {result.get('chunk_count', len(chunks))} chunks")
                    if not chunks:
                        empty_state(
                            "No matches",
                            "Try a broader query or ingest more documents first.",
                            key="knowledge_search_empty",
                        )
                    else:
                        preview_col, list_col = st.columns([2, 1])
                        selected = st.session_state.get("knowledge_preview_idx", 0)
                        with list_col:
                            st.markdown("**Results**")
                            for i, chunk in enumerate(chunks):
                                label = f"{chunk.get('chunk_id') or i} · {chunk.get('relevance', '')}"
                                if st.button(label, key=f"kc_chunk_{i}", use_container_width=True):
                                    st.session_state["knowledge_preview_idx"] = i
                                    selected = i
                        with preview_col:
                            st.markdown("**Preview**")
                            idx = min(int(st.session_state.get("knowledge_preview_idx", selected) or 0), len(chunks) - 1)
                            chunk = chunks[idx]
                            st.markdown(
                                f"**{chunk.get('chunk_id')}** · relevance={chunk.get('relevance')}"
                            )
                            st.write(chunk.get("content") or "")
                except Exception as exc:
                    show_api_error(exc)

    with tab_docs:
        section_header("Documents", "List and delete ingested knowledge")
        if st.button("Refresh documents"):
            st.session_state.pop("knowledge_docs_cache", None)
        try:
            docs_payload = st.session_state.get("knowledge_docs_cache")
            if docs_payload is None:
                docs_payload = knowledge.list_documents()
                st.session_state["knowledge_docs_cache"] = docs_payload
            docs = docs_payload.get("documents") or []
            st.caption(f"{docs_payload.get('count', len(docs))} documents")
            if not docs:
                empty_state(
                    "No documents yet",
                    "Ingest a document from the Ingest tab to build your knowledge base.",
                    key="knowledge_docs_empty",
                )
            for doc in docs:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(
                        f"**{doc.get('title')}** (`{doc.get('document_id')}`) · "
                        f"source={doc.get('source')}"
                    )
                with c2:
                    if st.button("Delete", key=f"del_{doc.get('document_id')}"):
                        try:
                            knowledge.delete(str(doc.get("document_id")))
                            st.session_state.pop("knowledge_docs_cache", None)
                            success_banner("Deleted")
                            st.rerun()
                        except Exception as exc:
                            show_api_error(exc)
        except Exception as exc:
            show_api_error(exc)
