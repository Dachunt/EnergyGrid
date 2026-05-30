FROM alpine:3.19

RUN apk add --no-cache apache2 apache2-utils munin munin-node curl perl-log-log4perl

RUN mkdir -p /run/apache2 /run/munin /var/www/munin /var/lib/munin /var/log/munin && \
    chown -R munin:munin /var/lib/munin /var/log/munin /var/www/munin /run/munin 2>/dev/null; true

COPY munin.conf /etc/munin/munin.conf
COPY httpd.conf /etc/apache2/httpd.conf

EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
