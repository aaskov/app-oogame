#!/usr/bin/env bash
# Print a GitHub App installation token for the agent bot (docs/adr/0005).
# The token is scoped to this repository and is valid for one hour. The
# script caches it and gets a new token 5 minutes before it expires.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$here/../agent-bot.env"
key="${AGENT_BOT_KEY:-/mnt/agent-bot/private-key.pem}"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/agent-bot/token.json"
now="$(date +%s)"

if [ -f "$cache" ]; then
  expires="$(jq -r '.expires_at | fromdateiso8601' "$cache")"
  if (( expires - now > 300 )); then
    jq -r .token "$cache"
    exit 0
  fi
fi

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
header="$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)"
payload="$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' $((now - 60)) $((now + 540)) "$AGENT_BOT_APP_ID" | b64url)"
signature="$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$key" -binary | b64url)"
jwt="$header.$payload.$signature"

api() {
  curl -fsS -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" "$@"
}

installation="$(api "https://api.github.com/repos/$AGENT_BOT_REPO/installation" | jq -r .id)"
umask 077
mkdir -p "$(dirname "$cache")"
api -X POST "https://api.github.com/app/installations/$installation/access_tokens" \
  -d "{\"repositories\":[\"${AGENT_BOT_REPO#*/}\"]}" >"$cache.tmp"
mv "$cache.tmp" "$cache"
jq -r .token "$cache"
