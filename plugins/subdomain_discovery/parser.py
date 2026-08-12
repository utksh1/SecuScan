from plugins.common.parsers import parse_recon_output

def parse(output: str):
    return parse_recon_output(output, "Subdomain Discovery", max_lines=200)
