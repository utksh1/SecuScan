from plugins.common.parsers import parse_scanner_output

def parse(output: str) -> dict:
    return parse_scanner_output(output, "Fuzzer")
