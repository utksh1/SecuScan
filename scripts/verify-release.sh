#!/usr/bin/env bash
# SecuScan Release Artifact Verification Utility
# Validates artifact checksums and displays Sigstore signature verification instructions.

set -uo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 SecuScan Release Artifact Verification Utility${NC}"
echo "================================================="
echo ""

if [ ! -f "SHA256SUMS" ]; then
    echo -e "${RED}❌ ERROR: SHA256SUMS file not found in current directory!${NC}"
    echo "Please download SHA256SUMS along with the release archives first."
    exit 1
fi

echo -e "${YELLOW}1. Checking SHA256 Checksums...${NC}"
# Gracefully support both Linux sha256sum and macOS shasum -a 256
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum --check SHA256SUMS
else
    shasum -a 256 -c SHA256SUMS
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Checksums match perfectly!${NC}"
else
    echo -e "${RED}❌ ERROR: Checksum validation failed! The artifacts may be corrupted or modified.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}2. Sigstore Cryptographic Signature Verification${NC}"
echo "-------------------------------------------------"
echo "To verify the keyless OIDC signature on the SHA256SUMS baseline, run:"
echo ""
echo -e "  ${GREEN}pip install sigstore${NC}"
echo -e "  ${GREEN}sigstore verify identity \\"
echo "    --certificate SHA256SUMS.certificate \\"
echo "    --signature SHA256SUMS.sig \\"
echo "    --cert-identity \"https://github.com/utksh1/SecuScan/.github/workflows/release.yml@refs/tags/v*\" \\"
echo "    --cert-oidc-issuer \"https://token.actions.githubusercontent.com\" \\"
echo -e "    SHA256SUMS${NC}"
echo "-------------------------------------------------"
echo "Check the OIDC certificate and ensure the identity matches the official SecuScan workflow."
echo ""
