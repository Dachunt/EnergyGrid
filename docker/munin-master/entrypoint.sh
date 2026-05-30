#!/bin/sh
set -e

MUNIN_USER="${MUNIN_USER:-munin}"

# Fix permissions on runtime volumes (docker volumes may reset ownership)
chown -R "$MUNIN_USER:$MUNIN_USER" /var/lib/munin /var/log/munin /var/www/munin /run/munin 2>/dev/null || true

# Run munin cron once at startup to generate initial graphs
su -s /bin/sh "$MUNIN_USER" -c "munin-cron" 2>&1 || true

# Start munin master html generation loop in background
(
  while true; do
    su -s /bin/sh "$MUNIN_USER" -c "munin-cron" 2>&1 || true
    sleep 300  # every 5 minutes
  done
) &

# Start Apache
httpd -D FOREGROUND -f /etc/apache2/httpd.conf
