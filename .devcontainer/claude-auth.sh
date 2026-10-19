#!/usr/bin/env bash
# Let Claude Code in this container use the architect's long-lived token, so
# each new container needs no /login (docs/adr/0006). Called from post-create.sh.
# The token stays on the host in ~/.config/claude-agent/oauth-token
# (from 'claude setup-token') and is mounted read-only at /mnt/claude-agent.
set -euo pipefail
token_file=/mnt/claude-agent/oauth-token

real="$(command -v claude || true)"
if [ -z "$real" ] || [ "$real" = /usr/local/bin/claude ]; then
  echo "claude-auth: Claude Code is not installed. Skipped."
  exit 0
fi

# The wrapper reads the token at each start, so a new token needs no rebuild.
sudo tee /usr/local/bin/claude >/dev/null <<WRAPPER
#!/usr/bin/env bash
if [ -z "\${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ -r $token_file ]; then
  CLAUDE_CODE_OAUTH_TOKEN="\$(cat $token_file)"
  export CLAUDE_CODE_OAUTH_TOKEN
fi
exec $real "\$@"
WRAPPER
sudo chmod +x /usr/local/bin/claude

# Skip the first-run screens in a fresh container.
[ -f "$HOME/.claude.json" ] || echo '{"hasCompletedOnboarding": true}' >"$HOME/.claude.json"

if [ -r "$token_file" ]; then
  echo "claude-auth: on. Claude Code uses the token from the host."
else
  echo "claude-auth: off. Run 'claude setup-token' on the host and save the token in ~/.config/claude-agent/oauth-token."
fi
