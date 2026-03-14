import re
import os

def generate_env():
    cred_file = "credentials.md"
    env_file = ".env"
    
    if not os.path.exists(cred_file):
        print(f"Error: {cred_file} not found.")
        return

    with open(cred_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex to find values after specific labels
    mappings = {
        "SHOPIFY_STORE_DOMAIN": r"- \*\*Store Domain\*\*: `([^`]+)`",
        "SHOPIFY_CLIENT_ID": r"- \*\*Client ID\*\*: `([^`]+)`",
        "SHOPIFY_CLIENT_SECRET": r"- \*\*Client Secret\*\*: `([^`]+)`",
        "SHOPIFY_ACCESS_TOKEN": r"- \*\*Admin API Access Token\*\*: `([^`]+)`",
        "SHOPIFY_LOCATION_ID": r"- \*\*Location ID\*\*: `([^`]+)`",
        "YAMPI_USER_TOKEN": r"- \*\*User Token\*\*: `([^`]+)`",
        "YAMPI_USER_SECRET_KEY": r"- \*\*User Secret Key\*\*: `([^`]+)`",
        "YAMPI_MERCHANT_ALIAS": r"- \*\*Merchant Alias\*\*: `([^`]+)`"
    }

    env_lines = []
    for var_name, pattern in mappings.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1).strip()
            env_lines.append(f"{var_name}=\"{value}\"")
        else:
            print(f"Warning: Could not find value for {var_name}")

    with open(env_file, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines))
        
    
    print(f"Successfully generated {env_file} from {cred_file}.")

if __name__ == "__main__":
    generate_env()
