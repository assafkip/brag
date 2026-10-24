#!/usr/bin/env bash
# say-play.sh - Play the audio /say synthesized, with speed/seek/pause controls.
#
# Pairs with say-last-response.py (kipi-core /say). /say writes a stable mp3 and
# does NOT auto-play; you run THIS so the player owns your terminal and your key
# presses drive it. mpv is the only common player with live speed control.
#
# Usage:
#   say-play                 # play the local file (mini speakers / ssh session)
#   say-play --remote HOST   # from your laptop: pull the file off HOST, play here
#                            # (HOST defaults to $KIPI_SAY_HOST if set)
#
# mpv keys: [ ] speed | <-/-> seek 5s | up/down 60s | space pause | q quit
set -euo pipefail

MP3="${HOME}/.config/kipi/say-last.mp3"

command -v mpv >/dev/null 2>&1 || {
  echo "say-play: mpv not installed. brew install mpv" >&2
  exit 1
}

if [[ "${1:-}" == "--remote" ]]; then
  host="${2:-${KIPI_SAY_HOST:-}}"
  if [[ -z "$host" ]]; then
    echo "say-play: need a host: say-play --remote <ssh-host> (or set KIPI_SAY_HOST)" >&2
    exit 1
  fi
  # Stream the remote file down the SSH pipe and play it locally.
  ssh "$host" "cat '$MP3'" | mpv -
  exit 0
fi

if [[ ! -f "$MP3" ]]; then
  echo "say-play: no audio at $MP3. Run /say first." >&2
  exit 1
fi
exec mpv "$MP3"
