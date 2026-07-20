import whois
import json
import sys
import argparse

def lookup(target):
    try:
        w = whois.whois(target)
        # Convert whois object to dict, handling datetime objects
        result = {}
        for key, value in w.items():
            if isinstance(value, list):
                result[key] = [str(v) if hasattr(v, 'isoformat') else v for v in value]
            elif hasattr(value, 'isoformat'):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WHOIS lookup tool using python-whois")
    parser.add_argument("target", help="Domain or IP to lookup")
    args = parser.parse_args()

    result = lookup(args.target)
    print(json.dumps(result, indent=2))
