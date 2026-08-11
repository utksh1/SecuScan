from plugins.common.parsers import parse_line_based_output

def parse(output: str) -> dict:
    return parse_line_based_output(output, "Spider")
