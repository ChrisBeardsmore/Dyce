import pandas as pd

def create_input_dataframe(num_rows=10):
    base_cols = ["Site Name", "Post Code", "Annual KWH"]
    durations = [12, 24, 36]
    all_cols = base_cols.copy()

    for d in durations:
        all_cols += [
            f"Base Standing Charge ({d}m)", f"Base Unit Rate ({d}m)",
            f"Standing Charge Uplift ({d}m)", f"Uplift Unit Rate ({d}m)",
            f"TAC £({d}m)", f"Margin £({d}m)"
        ]

    df = pd.DataFrame([
        {col: "" if col in ["Site Name", "Post Code"] else 0 for col in all_cols}
        for _ in range(num_rows)
    ])
    
    return df, all_cols
