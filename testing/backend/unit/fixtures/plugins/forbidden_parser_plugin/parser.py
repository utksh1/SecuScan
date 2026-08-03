def parse(output: str) -> dict:
    # Forbidden: exec
    exec("raise ValueError('sandbox exec test')")
    return {"findings": []}
