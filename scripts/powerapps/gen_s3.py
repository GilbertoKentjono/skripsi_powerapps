PAGE = 500

def gen(table, scale, status_expr):
    lines = []
    for start in range(0, scale, PAGE):
        end = start + PAGE
        lines.append(
            f"    Collect(colResult, Filter({table}, Seq > {start} && Seq <= {end}));"
        )
    return "\n".join(lines)

sql = {
    "SQL_5k": ("TestDataset5k", 5000),
    "SQL_10k": ("TestDataset10k", 10000),
}
dv = {
    "DV_5k": ("TestDatasets", 5000),
    "DV_10k": ("TestDataset10ks", 10000),
}

for key, (table, scale) in {**sql, **dv}.items():
    print(f'\n=== {key} ===')
    print(f'    "{key}", (')
    print("    Clear(colResult);")
    print(gen(table, scale, None))
    print("    ),")