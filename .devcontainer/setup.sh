#!/bin/bash
# setup.sh - Automated persistent Codespace setup
set -e

# Update and install essential packages
sudo apt-get update && sudo apt-get install -y git curl vim

# Optional: Install Python and pip
sudo apt-get install -y python3 python3-pip

# Optional: Install Node.js and npm
sudo apt-get install -y nodejs npm

# Optional: Install Docker CLI (if needed)
sudo apt-get install -y docker.io

# Install Git LFS and initialize
sudo apt-get install -y git-lfs
git lfs install
# Install google-gemini-cli globally
if ! npm list -g | grep -q 'google-gemini-cli'; then
  echo "Installing google-gemini-cli globally..."
  npm install -g google-gemini-cli || echo "Warning: google-gemini-cli may not be published to npm. Manual install may be required."
fi
# Install Homebrew (Linuxbrew)
if ! command -v brew &> /dev/null; then
  echo "Installing Homebrew..."
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> "$HOME/.bashrc"
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Install the scandroid namespace so `from scandroid import …` works in any
# python/ipython invoked inside the Codespace. Mirrors the SessionStart hook
# Claude Code uses on local + remote sessions.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m pip install --user -e "$REPO_ROOT" \
  || python3 -m pip install --user --break-system-packages -e "$REPO_ROOT"

echo "Persistent Codespace environment is ready!"
