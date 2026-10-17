#!/usr/bin/env bash
# Make the agent bot the git and gh identity in this container (docs/adr/0005).
# Without an app ID or a key, the bot is off and nothing changes. This is the
# case in CI.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$here/../agent-bot.env"
key="${AGENT_BOT_KEY:-/mnt/agent-bot/private-key.pem}"

if [ -z "${AGENT_BOT_APP_ID:-}" ]; then
  echo "agent-bot: off. .devcontainer/agent-bot.env has no app ID."
  exit 0
fi
if [ ! -r "$key" ]; then
  echo "agent-bot: off. There is no key at ~/.config/agent-bot/private-key.pem on the host."
  exit 0
fi

bot="${AGENT_BOT_APP_SLUG}[bot]"
user_id="$(curl -fsS "https://api.github.com/users/${AGENT_BOT_APP_SLUG}%5Bbot%5D" | jq -r .id)"

git config --global user.name "$bot"
git config --global user.email "${user_id}+${bot}@users.noreply.github.com"
# The host uses SSH remotes. The container has no SSH key, so it uses HTTPS with the bot token.
git config --global url."https://github.com/".insteadOf "git@github.com-personal:"
git config --global --add url."https://github.com/".insteadOf "git@github.com:"
git config --global credential."https://github.com".helper "$here/git-credential.sh"

# gh in this container uses the bot token.
# shellcheck disable=SC2016 # The wrapper expands these at run time.
printf '#!/usr/bin/env bash\nGH_TOKEN="$(%q)" exec /usr/bin/gh "$@"\n' "$here/token.sh" |
  sudo tee /usr/local/bin/gh >/dev/null
sudo chmod +x /usr/local/bin/gh

"$here/token.sh" >/dev/null
echo "agent-bot: on. Git and gh in this container act as $bot."
