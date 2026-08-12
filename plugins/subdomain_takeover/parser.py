from plugins.common.parsers import parse_generic_output

def parse(output: str) -> dict:
    return parse_generic_output(output, "Subdomain Takeover")
