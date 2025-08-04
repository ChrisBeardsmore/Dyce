def calculate_tac_and_margin(kwh, base_sc, base_unit, uplift_sc, uplift_unit):
    capped_uplift_unit = min(float(uplift_unit), 3.000)
    capped_uplift_sc = min(float(uplift_sc), 100.0)

    sell_unit = base_unit + capped_uplift_unit
    sell_sc = base_sc + capped_uplift_sc

    base_tac = round((base_unit * kwh + base_sc * 365) / 100, 2)
    sell_tac = round((sell_unit * kwh + sell_sc * 365) / 100, 2)
    margin = round(sell_tac - base_tac, 2)

    return sell_tac, margin
