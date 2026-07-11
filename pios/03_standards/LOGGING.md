# Logging

- Use project logging utilities under `backend/logging`
- Include request/dataset/job identifiers when available
- Avoid logging raw PII payloads or API keys
- Prefer structured messages for monitoring correlation
- Frontend: use Streamlit-friendly user messages; do not dump secrets to the UI
