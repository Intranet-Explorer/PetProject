#!/bin/sh
# Run the engine as a per-user launchd agent, so a two-week run survives a closed terminal, a crash or a reboot.
#   ./run.sh start [profile] | stop | status      (profile: live, the family on a one-hour world day; showcase, the same lives in turbo)
set -e
cd "$(dirname "$0")"
LABEL=com.pet.engine
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

case "$1" in
start)
  mkdir -p data "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>WorkingDirectory</key><string>$PWD</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/caffeinate</string><string>-i</string>
    <string>$(command -v uv)</string><string>run</string><string>python</string><string>-m</string><string>engine.server</string>
  </array>
  <key>EnvironmentVariables</key><dict><key>PET_PROFILE</key><string>$2</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>20</integer>
  <key>StandardOutPath</key><string>$PWD/data/server.log</string>
  <key>StandardErrorPath</key><string>$PWD/data/server.log</string>
</dict></plist>
PLIST
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do   # booting out takes a moment (the engine saves on its way down); starting too soon fails
    launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || break
    sleep 1
  done
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "started; view at http://localhost:8000, log in data/server.log" ;;
stop)
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "stopped and removed" ;;
status)
  launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state =|pid =|last exit" || echo "not running under launchd" ;;
*) echo "usage: $0 start [profile]|stop|status"; exit 1 ;;
esac
