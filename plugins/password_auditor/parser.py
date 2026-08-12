from plugins.common.parsers import parse_scanner_output

def parse(output: str):
    return parse_scanner_output(output, "Password Auditor", max_lines=300)
