#!/bin/bash

set -euo pipefail

CONFIG="/etc/healstrata/secrets.conf"
ENV_FILE="/opt/healstrata/secrets.env"

# Load OCI configuration
if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: $CONFIG does not exist"
    exit 1
fi

source "$CONFIG"

# Make sure required configuration exists
: "${COMPARTMENT_OCID:?COMPARTMENT_OCID is not set}"
: "${VAULT_OCID:?VAULT_OCID is not set}"

# Make sure the runtime directory exists
mkdir -p "$(dirname "$ENV_FILE")"

# Temporary file so we never leave a partially-written secrets file. It lives
# beside the target so the final mv is a rename on the same filesystem.
TEMP_FILE="$(mktemp "${ENV_FILE}.XXXXXX")"

cleanup() {
    rm -f "$TEMP_FILE"
}

trap cleanup EXIT

chmod 600 "$TEMP_FILE"

echo "Fetching secrets from OCI..."

SECRET_LIST="$(
    oci vault secret list \
        --compartment-id "$COMPARTMENT_OCID" \
        --vault-id "$VAULT_OCID" \
        --auth instance_principal \
        --all \
        --query 'data[]' \
        --output json
)"

# An empty response means the compartment or vault is wrong, or every secret is
# pending deletion. Writing an empty env file would silently take the app down.
if [[ -z "$SECRET_LIST" ]]; then
    echo "ERROR: no secrets returned for vault $VAULT_OCID" >&2
    exit 1
fi

WRITTEN=0

# Process substitution, not a pipe, so WRITTEN survives the loop.
while read -r secret; do

    SECRET_ID="$(echo "$secret" | jq -r '.id')"
    SECRET_NAME="$(echo "$secret" | jq -r '."secret-name"')"
    SECRET_LIFECYCLE_STATE="$(echo "$secret" | jq -r '."lifecycle-state"')"

    if [[ "$SECRET_LIFECYCLE_STATE" != "ACTIVE" ]]; then
        echo "Skipping $SECRET_NAME ($SECRET_LIFECYCLE_STATE)"
        continue
    fi

    # Docker's env-file parser rejects anything that is not a shell-style name,
    # and the failure would otherwise surface at container start.
    if [[ ! "$SECRET_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
        echo "WARNING: skipping $SECRET_NAME, not a valid environment variable name" >&2
        continue
    fi

    echo "Fetching $SECRET_NAME..."

    SECRET_VALUE="$(
        oci secrets secret-bundle get \
            --secret-id "$SECRET_ID" \
            --auth instance_principal \
            --query 'data."secret-bundle-content".content' \
            --raw-output |
        base64 --decode
    )"

    # Escape characters that could break Docker's env-file format.
    STRIPPED_VALUE="${SECRET_VALUE//$'\r'/}"
    STRIPPED_VALUE="${STRIPPED_VALUE//$'\n'/}"

    if [[ "$STRIPPED_VALUE" != "$SECRET_VALUE" ]]; then
        echo "WARNING: $SECRET_NAME contained line breaks that were stripped" >&2
    fi

    printf '%s=%s\n' "$SECRET_NAME" "$STRIPPED_VALUE" >> "$TEMP_FILE"

    WRITTEN=$((WRITTEN + 1))

done < <(jq -c '.[]' <<< "$SECRET_LIST")

if (( WRITTEN == 0 )); then
    echo "ERROR: no active secrets were written, leaving $ENV_FILE untouched" >&2
    exit 1
fi

# Replace the old secrets atomically
mv "$TEMP_FILE" "$ENV_FILE"

chmod 600 "$ENV_FILE"

echo "Secrets successfully synchronized ($WRITTEN written)."