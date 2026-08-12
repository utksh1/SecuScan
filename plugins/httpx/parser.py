from plugins.common.parsers import parse_recon_output

def parse(output: str) -> dict:
    return parse_recon_output(output, "HTTPX")
