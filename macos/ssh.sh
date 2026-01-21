#!/bin/bash
set -euo pipefail

# Source shared print functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/print_utils.sh"

print_header "🔐 SSH Setup"
# Configuration
EMAIL="ichbinevan@gmail.com"
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_CONFIG="$HOME/.ssh/config"

# Create .ssh directory if it doesn't exist
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Check if SSH key already exists
print_section "SSH Key"
if [ -f "$SSH_KEY" ]; then
    print_info "SSH key already exists at $SSH_KEY"
else
    print_action "Generating new SSH key..."
    ssh-keygen -t ed25519 -C "$EMAIL" -f "$SSH_KEY" -N "" >/dev/null 2>&1
    print_success "SSH key generated"
fi

# Ensure both private and public keys exist
if [ ! -f "${SSH_KEY}.pub" ]; then
    print_warn "Public key not found. Something went wrong with key generation."
    exit 1
fi

# Start ssh-agent only if not already running
if ! pgrep -u "$USER" ssh-agent >/dev/null; then
    eval "$(ssh-agent -s)" >/dev/null 2>&1
fi

# Create/update SSH config, preserving any existing custom configuration
print_section "SSH Config"
if [ ! -f "$SSH_CONFIG" ]; then
    print_action "Creating SSH config..."
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
        print_info "SSH config already contains our settings"
    fi
fi
chmod 600 "$SSH_CONFIG"

# Add key to ssh-agent only if not already added (idempotent)
print_section "SSH Agent"
if ssh-add -l 2>/dev/null | grep -q "$SSH_KEY" || ssh-add -l 2>/dev/null | grep -q "$(ssh-keygen -lf "$SSH_KEY" 2>/dev/null | awk '{print $2}')"; then
    print_info "SSH key already in ssh-agent"
else
    print_action "Adding SSH key to ssh-agent..."
    ssh-add --apple-use-keychain "$SSH_KEY" 2>/dev/null || {
        # If ssh-agent isn't running, start it and try again
        eval "$(ssh-agent -s)" >/dev/null 2>&1
        ssh-add --apple-use-keychain "$SSH_KEY" 2>/dev/null || print_warn "Could not add key to ssh-agent"
    }
    print_success "SSH key added to ssh-agent"
fi

# Copy public key to clipboard
print_action "Copying public key to clipboard..."
pbcopy < "${SSH_KEY}.pub"
print_success "Public key copied to clipboard"

printf "\n"
printf "  Next steps:\n"
printf "  1. Go to GitHub.com → Settings → SSH and GPG keys\n"
printf "  2. Click 'New SSH key'\n"
printf "  3. Paste your key (it's already in your clipboard)\n"
printf "  4. Give it a title (e.g., 'MacBook Pro')\n"
printf "\n"
printf "  Test your SSH connection with: ssh -T git@github.com\n"