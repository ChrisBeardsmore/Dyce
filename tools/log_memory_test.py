from shared.sqlite_utils import get_connection, create_memory_table, log_gpt_memory, get_memory

conn = get_connection()
create_memory_table(conn)  # Create the memory table if it doesn't exist

# Add a memory entry
log_gpt_memory(conn, app="gas", message="Updated LDZ mapping logic.")

# Print recent logs
logs = get_memory(conn, app="gas")
for row in logs:
    print(row)
