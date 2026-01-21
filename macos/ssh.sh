#!/bin/bash
set -euo pipefail

echo "Setting up SSH keys for Git and Homebrew..."

# Configuration
EMAIL="ichbinevan@gmail.com"
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_CONFIG="$HOME/.ssh/config"

# Create .ssh directory if it doesn't exist
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Check if SSH key already exists
if [ -f "$SSH_KEY" ]; then
    echo "SSH key already exists at $SSH_KEY"
else
    echo "Generating new SSH key..."
    ssh-keygen -t ed25519 -C "$EMAIL" -f "$SSH_KEY" -N ""
fi

# Ensure both private and public keys exist
if [ ! -f "${SSH_KEY}.pub" ]; then
    echo "Error: Public key not found. Something went wrong with key generation."
    exit 1
fi

# Start ssh-agent only if not already running
if ! pgrep -u "$USER" ssh-agent >/dev/null; then
    eval "$(ssh-agent -s)"
fi

# Create/update SSH config, preserving any existing custom configuration
if [ ! -f "$SSH_CONFIG" ]; then
    echo "Creating SSH config..."
    cat > "$SSH_CONFIG" <<EOL
Host github.com
    UseKeychain yes
    AddKeysToAgent yes
    IdentityFile ~/.ssh/id_ed25519
EOL
else
    # Check if our configuration is already present
    if ! grep -q "IdentityFile ~/.ssh/id_ed25519" "$SSH_CONFIG"; then
        echo "Updating SSH config..."
        cp "$SSH_CONFIG" "${SSH_CONFIG}.backup"
        cat >> "$SSH_CONFIG" <<EOL

# Added by setup script
Host *
    UseKeychain yes
    AddKeysToAgent yes
    IdentityFile ~/.ssh/id_ed25519
EOL
    else
        echo "SSH config already contains our settings"
    fi
fi
chmod 600 "$SSH_CONFIG"

# Add key to ssh-agent only if not already added (idempotent)
# Check if key is loaded in ssh-agent
if ssh-add -l 2>/dev/null | grep -q "$SSH_KEY" || ssh-add -l 2>/dev/null | grep -q "$(ssh-keygen -lf "$SSH_KEY" 2>/dev/null | awk '{print $2}')"; then
    echo "SSH key already in ssh-agent"
else
    echo "Adding SSH key to ssh-agent..."
    ssh-add --apple-use-keychain "$SSH_KEY" 2>/dev/null || {
        # If ssh-agent isn't running, start it and try again
        eval "$(ssh-agent -s)" >/dev/null 2>&1
        ssh-add --apple-use-keychain "$SSH_KEY" 2>/dev/null || echo "Warning: Could not add key to ssh-agent"
    }
fi

# Copy public key to clipboard
echo "Copying public key to clipboard..."
pbcopy < "${SSH_KEY}.pub"

echo "✓ SSH setup complete!"
echo
echo "Next steps:"
echo "1. Go to GitHub.com → Settings → SSH and GPG keys"
echo "2. Click 'New SSH key'"
echo "3. Paste your key (it's already in your clipboard)"
echo "4. Give it a title (e.g., 'MacBook Pro')"
echo
echo "Test your SSH connection with: ssh -T git@github.com"