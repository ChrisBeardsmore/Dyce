# 🔴 -----------------------------------------
# 🔴 Function: calculate_tac_and_margin
# 🔴 Purpose: Calculate the Total Annual Cost (TAC) for a customer, 
# 🔴          and compute Dyce's margin based on applied uplifts.
# 🔴 Inputs:
# 🔴   - kwh (float): Annual consumption in kilowatt-hours
# 🔴   - base_sc (float): Base standing charge (p/day)
# 🔴   - base_unit (float): Base unit rate (p/kWh)
# 🔴   - uplift_sc (float): Uplift to standing charge (p/day)
# 🔴   - uplift_unit (float): Uplift to unit rate (p/kWh)
# 🔴 Returns:
# 🔴   - sell_tac (float): Customer-facing Total Annual Cost (£)
# 🔴   - margin (float): Dyce £ margin per site/year
# 🔴 Notes:
# 🔴   - Uplift caps are enforced: 3.000p (unit), 100p (SC)
# 🔴   - 365-day standing charge assumed
# 🔴 -----------------------------------------
def calculate_tac_and_margin(
    kwh: float,
    base_sc: float,
    base_unit: float,
    uplift_sc: float,
    uplift_unit: float
) -> tuple[float, float]:
    """Apply capped uplifts and return customer TAC and Dyce margin."""

    # Cap uplifts to prevent extreme pricing
    capped_uplift_unit = min(float(uplift_unit), 3.000)
    capped_uplift_sc = min(float(uplift_sc), 100.0)

    # Calculate final sell prices
    sell_unit = base_unit + capped_uplift_unit
    sell_sc = base_sc + capped_uplift_sc

    # Base and sell TAC calculations (converted from pence to pounds)
    base_tac = round((base_unit * kwh + base_sc * 365) / 100, 2)
    sell_tac = round((sell_unit * kwh + sell_sc * 365) / 100, 2)

    # Dyce margin = uplifted TAC - base TAC
    margin = round(sell_tac - base_tac, 2)

    return sell_tac, margin
