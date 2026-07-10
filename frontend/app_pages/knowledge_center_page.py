from __future__ import annotations

"""Knowledge Center — ingest/search/list/delete via knowledge API."""

import streamlit as st

from frontend.utils.workspace_api import get_workspace_clients, show_api_error


def render_knowledge_center(client=None) -> None:
    st.header("Knowledge Center")
    st.caption("Manage RAG knowledge documents through `/api/v1/knowledge/*`.")

    knowledge = get_workspace_clients()["knowledge"]

    tab_ingest, tab_search, tab_docs = st.tabs(["Ingest", "Search", "Documents"])

    with tab_ingest:
        title = st.text_input("Title")
        content = st.text_area("Content", height=180)
        source = st.text_input("Source", value="manual")
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
                    st.success(
                        f"Ingested `{result.get('document_id')}` "
                        f"({result.get('chunk_count', 0)} chunks)"
                    )
                except Exception as exc:
                    show_api_error(exc)

    with tab_search:
        query = st.text_input("Search query", key="knowledge_search_query")
        top_k = st.slider("Top K", min_value=1, max_value=20, value=5)
        if st.button("Search knowledge"):
            if not query.strip():
                st.warning("Enter a search query.")
            else:
                try:
                    result = knowledge.search(query.strip(), top_k=top_k)
                    st.write(f"Found {result.get('chunk_count', 0)} chunks")
                    for chunk in result.get("chunks") or []:
                        st.markdown(
                            f"**{chunk.get('chunk_id')}** · relevance={chunk.get('relevance')}"
                        )
                        st.write(chunk.get("content") or "")
                        st.divider()
                except Exception as exc:
                    show_api_error(exc)

    with tab_docs:
        if st.button("Refresh documents"):
            st.session_state.pop("knowledge_docs_cache", None)
        try:
            docs_payload = st.session_state.get("knowledge_docs_cache")
            if docs_payload is None:
                docs_payload = knowledge.list_documents()
                st.session_state["knowledge_docs_cache"] = docs_payload
            docs = docs_payload.get("documents") or []
            st.write(f"{docs_payload.get('count', len(docs))} documents")
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
                            st.success("Deleted")
                            st.rerun()
                        except Exception as exc:
                            show_api_error(exc)
        except Exception as exc:
            show_api_error(exc)
