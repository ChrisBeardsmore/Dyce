from shared.sqlite_utils import log_gpt_note

# 🧠 GPT writes a memory log to the app "contract"
log_gpt_note(
    app="contract",
    message="Credit scoring logic adjusted to apply new risk band thresholds."
)

print("✅ Memory log saved to dyce.db (app='contract')")
