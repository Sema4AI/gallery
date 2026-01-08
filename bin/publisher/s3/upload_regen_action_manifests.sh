#!/bin/bash
set -e

# NOTES: THIS SCRIPT IS ONLY MEANT FOR PUSHING REGENERATED ACTION MANIFEST FILES TO S3
# 1. Requires AWS CICD account admin permissions
# 2. You must follow the README.md (the regen part can be done with AWS 'ReadOnlyAccess' -role)
# 3. Run: rcc run -t "Regen actions manifests"
# 4. Switch to admin role in AWS
# 5. Run this script
# 6. Verify the manifests via AWS S3 or in Studio

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GALLERY_DIR="$SCRIPT_DIR/../gallery"
S3_BASE_URL="s3://downloads.robocorp.com/gallery/actions"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS CLI is not configured or credentials have expired."
    echo ""
    echo "To configure AWS CLI:"
    echo "  1. You need to have 'ProductionAccountAdmin' role in AWS"
    echo "  2. Ensure AWS profile is configured in ~/.aws/"
    echo "  3. Run: export AWS_PROFILE=cicd-admin"
    echo "  4. Run: aws sso login --profile cicd-admin"
    echo ""
    echo "See s3/README.md for more details."
    exit 1
fi

echo "AWS CLI configured. Using identity:"
aws sts get-caller-identity --query 'Arn' --output text
echo ""

cd "$GALLERY_DIR"

echo "Uploading manifest.json..."
aws s3 cp manifest.json $S3_BASE_URL/manifest.json --cache-control max-age=120 --content-type "application/json"
sha256sum manifest.json | awk '{printf "%s", $1}' > manifest.sha256
aws s3 cp manifest.sha256 $S3_BASE_URL/manifest.sha256 --cache-control max-age=120 --content-type "text/plain"

echo "Uploading manifest_spcs.json..."
aws s3 cp manifest_spcs.json $S3_BASE_URL/manifest_spcs.json --cache-control max-age=120 --content-type "application/json"
sha256sum manifest_spcs.json | awk '{printf "%s", $1}' > manifest_spcs.sha256
aws s3 cp manifest_spcs.sha256 $S3_BASE_URL/manifest_spcs.sha256 --cache-control max-age=120 --content-type "text/plain"

echo "Done!"
