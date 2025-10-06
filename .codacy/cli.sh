#!/usr/bin/env bash

fatal() {
    local msg="${1:-fatal error}"
    echo "fatal: $msg" >&2
    exit 1
}

set -eo pipefail

# Set up paths first
bin_name="codacy-cli-v2"

# Determine OS-specific paths
os_name=$(uname)
arch=$(uname -m)

case "$arch" in
"x86_64")
  arch="amd64"
  ;;
"x86")
  arch="386"
  ;;
"aarch64"|"arm64")
  arch="arm64"
  ;;
esac

if [ -z "$CODACY_CLI_V2_TMP_FOLDER" ]; then
    if [ "$(uname)" = "Linux" ]; then
        CODACY_CLI_V2_TMP_FOLDER="$HOME/.cache/codacy/codacy-cli-v2"
    elif [ "$(uname)" = "Darwin" ]; then
        CODACY_CLI_V2_TMP_FOLDER="$HOME/Library/Caches/Codacy/codacy-cli-v2"
    else
        CODACY_CLI_V2_TMP_FOLDER=".codacy-cli-v2"
    fi
fi

version_file="$CODACY_CLI_V2_TMP_FOLDER/version.yaml"


get_version_from_yaml() {
    if [ -f "$version_file" ]; then
        local version=""
        # Try yq first if available
        if command -v yq > /dev/null 2>&1; then
            version=$(yq e '.version' "$version_file" 2>/dev/null)
        fi
        # Fallback to grep/awk with robust parsing
        if [ -z "$version" ] || [ "$version" = "null" ]; then
            # Match version: line and extract value, removing quotes
            version=$(grep -E '^[[:space:]]*version[[:space:]]*:' "$version_file" | awk -F': *' '{print $2}' | tr -d '"' | tr -d "'" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        fi
        if [ -n "$version" ] && [ "$version" != "null" ]; then
            echo "$version"
            return 0
        fi
    fi
    return 1
}

get_latest_version() {
    local response
    local curl_exit_code
    
    if [ -n "$GH_TOKEN" ]; then
        response=$(curl -Lq --fail --header "Authorization: Bearer $GH_TOKEN" "https://api.github.com/repos/codacy/codacy-cli-v2/releases/latest" 2>&1)
        curl_exit_code=$?
    else
        response=$(curl -Lq --fail "https://api.github.com/repos/codacy/codacy-cli-v2/releases/latest" 2>&1)
        curl_exit_code=$?
    fi

    # Check curl exit status
    if [ $curl_exit_code -ne 0 ]; then
        echo "Error: Failed to fetch latest version from GitHub API (curl exit code: $curl_exit_code)" >&2
        echo "Response: $response" >&2
        fatal "Unable to determine latest Codacy CLI version"
    fi

    # Check if response is empty
    if [ -z "$response" ]; then
        echo "Error: Empty response from GitHub API" >&2
        fatal "Unable to determine latest Codacy CLI version"
    fi

    # Check for rate limit before parsing
    handle_rate_limit "$response"

    # Validate response contains tag_name
    if ! echo "$response" | grep -q '"tag_name"'; then
        echo "Error: GitHub API response does not contain tag_name" >&2
        echo "Response: $response" >&2
        fatal "Invalid response from GitHub API"
    fi

    # Extract version
    local version=$(echo "$response" | grep -m 1 '"tag_name"' | cut -d'"' -f4)
    if [ -z "$version" ]; then
        echo "Error: Failed to parse tag_name from GitHub API response" >&2
        fatal "Unable to extract version from GitHub API"
    fi

    echo "$version"
}

handle_rate_limit() {
    local response="$1"
    if echo "$response" | grep -q "API rate limit exceeded"; then
          fatal "Error: GitHub API rate limit exceeded. Please try again later"
    fi
}

download_file() {
    local url="$1"

    echo "Downloading from URL: ${url}"
    if command -v curl > /dev/null 2>&1; then
        curl -# -LS "$url" -O
    elif command -v wget > /dev/null 2>&1; then
        wget "$url"
    else
        fatal "Error: Could not find curl or wget, please install one."
    fi
}

download() {
    local url="$1"
    local output_folder="$2"

    if [ ! -d "$output_folder" ]; then
        fatal "Download target directory does not exist: $output_folder"
    fi
    cd "$output_folder" || fatal "Failed to cd to $output_folder"
    download_file "$url" || fatal "Failed to download $url"
    cd - > /dev/null || true
}

download_cli() {
    # OS name lower case
    suffix=$(echo "$os_name" | tr '[:upper:]' '[:lower:]')

    local bin_folder="$1"
    local bin_path="$2"
    local version="$3"

    if [ ! -f "$bin_path" ]; then
        echo "📥 Downloading CLI version $version..."

        remote_file="codacy-cli-v2_${version}_${suffix}_${arch}.tar.gz"
        url="https://github.com/codacy/codacy-cli-v2/releases/download/${version}/${remote_file}"
        checksum_file="${remote_file}.sha256"
        checksum_url="${url}.sha256"

        # Download tarball
        download "$url" "$bin_folder"

        # Attempt to download checksum file
        echo "🔐 Attempting to download checksum file..."
        cd "$bin_folder" || fatal "Failed to cd to $bin_folder for checksum verification"
        
        if command -v curl > /dev/null 2>&1; then
            curl -sSL "$checksum_url" -o "$checksum_file" 2>/dev/null || echo "⚠️  Warning: Could not download checksum file, skipping verification"
        elif command -v wget > /dev/null 2>&1; then
            wget -q "$checksum_url" -O "$checksum_file" 2>/dev/null || echo "⚠️  Warning: Could not download checksum file, skipping verification"
        fi

        # Verify checksum if file was downloaded
        if [ -f "$checksum_file" ]; then
            echo "🔍 Verifying checksum..."
            if command -v sha256sum > /dev/null 2>&1; then
                sha256sum -c "$checksum_file" || fatal "Checksum verification failed for $remote_file"
            elif command -v shasum > /dev/null 2>&1; then
                shasum -a 256 -c "$checksum_file" || fatal "Checksum verification failed for $remote_file"
            else
                echo "⚠️  Warning: No checksum tool available (sha256sum or shasum), skipping verification"
            fi
            echo "✅ Checksum verified successfully"
        fi

        # Extract tarball
        tar xzf "$remote_file" -C "." || fatal "Failed to extract $remote_file"
        cd - > /dev/null || true
    fi
}

# Warn if CODACY_CLI_V2_VERSION is set and update is requested
if [ -n "$CODACY_CLI_V2_VERSION" ] && [ "$1" = "update" ]; then
    echo "⚠️  Warning: Performing update with forced version $CODACY_CLI_V2_VERSION"
    echo "    Unset CODACY_CLI_V2_VERSION to use the latest version"
fi

# Ensure version.yaml exists and is up to date
if [ ! -f "$version_file" ] || [ "$1" = "update" ]; then
    echo "ℹ️  Fetching latest version..."
    version=$(get_latest_version)
    mkdir -p "$CODACY_CLI_V2_TMP_FOLDER"
    echo "version: \"$version\"" > "$version_file"
fi

# Set the version to use
if [ -n "$CODACY_CLI_V2_VERSION" ]; then
    version="$CODACY_CLI_V2_VERSION"
else
    version=$(get_version_from_yaml)
fi


# Set up version-specific paths
bin_folder="${CODACY_CLI_V2_TMP_FOLDER}/${version}"

mkdir -p "$bin_folder"
bin_path="$bin_folder"/"$bin_name"

# Download the tool if not already installed
download_cli "$bin_folder" "$bin_path" "$version"
chmod +x "$bin_path"

run_command="$bin_path"
if [ ! -x "$run_command" ]; then
    fatal "Codacy cli v2 binary not found or not executable at: $run_command"
fi

if [ "$#" -eq 1 ] && [ "$1" = "download" ]; then
    echo "Codacy cli v2 download succeeded"
else
    "$run_command" "$@"
fi