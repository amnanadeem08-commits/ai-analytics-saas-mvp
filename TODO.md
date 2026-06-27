# TODO - Phase 0.2: Data Quality Workspace (Recommendation-Driven)

## Completed
- [x] Architecture review for export pipeline (read-only)
- [x] Scope confirmed: Data Quality Workspace only
- [x] Edit plan approved (with `remove_duplicates` option + backward compatibility constraints)

## Phase 0.3: AI Business Column Suggestions (Local Session Only)

## Planned
- [ ] Create reusable recipe registry + engine
  - Create: `frontend/services/business_columns_service.py`
  - Responsibilities: detect recipes, validate dependencies, generate preview, and create columns on demand only
- [ ] Update Dataset UI (minimal logic in UI layer)
  - Modify: `frontend/app_pages/dataset_page.py`
  - Add a section: “AI Business Column Suggestions”
  - Show only when local dataframe exists
  - Require explicit user action: “Create Selected Business Columns”
  - Update only:
    - `st.session_state["active_dataframe"]`
    - `st.session_state["local_dataframes"][dataset_id]`
- [ ] Unit tests (pure helper)
  - Create: `tests/test_business_columns_service.py`
  - Validate recipe detection, dependency validation, preview generation, and existing-column protection

## Phase 0.2 Implementation Steps (incremental; no commit/push)
1. [x] Create/define new option: `remove_duplicates: true/false`
   - Update backend model: `backend/models/dataset_models.py`
   - Ensure default behavior unchanged when omitted

2. [x] Backend cleaning engine supports `remove_duplicates`
   - Update: `backend/services/data_cleaning_service.py`
   - Cleaning report must include user decision + action applied:
     - Duplicate detected
     - Duplicate removed (only if selected)
     - Duplicate ignored (if not selected)

3. [x] Local cleaning helper supports `remove_duplicates`
   - Update: `frontend/utils/local_helpers.py` (`_apply_local_cleaning_rules`)
   - Apply toggle consistently with backend
   - Ensure local cleaning report differentiates action applied vs ignored

4. [x] Unify Data Quality Workspace UI
   - Update: `frontend/app_pages/dataset_page.py`
   - New unified section containing:
     - Issues Detected
     - Recommended Fixes
     - User Selected Fixes (including duplicate toggle)
     - Cleaning Results (no auto-modification)
   - Ensure “recommendations first” UX and user-triggered apply

5. [ ] Regression + runtime validation
   - [ ] Run `pytest` (if tests exist)
   - [ ] Runtime checks:
     - `/health`
     - Upload dataset
     - Dataset preview
     - Data cleaning (duplicates on/off via toggle)
     - Local datasets (session state intact)

6. [ ] Final reporting
   - Provide:
     - TODO items completed
     - Files modified
     - Tests executed
     - Runtime validation results
     - `git status --short`
     - `git diff --stat`
