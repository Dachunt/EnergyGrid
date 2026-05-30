FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    munin-node munin-common libnet-cidr-perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install custom munin plugins
RUN mkdir -p /usr/lib/munin/plugins/custom && \
    cp munin-plugins/* /usr/lib/munin/plugins/custom/ && \
    for p in /usr/lib/munin/plugins/custom/*; do \
      ln -sf "$p" "/etc/munin/plugins/$(basename $p)" ; \
    done

# Allow munin-master to connect (docker network subnet) and force IPv4
RUN sed -i "/^#cidr_allow/s/^#//" /etc/munin/munin-node.conf && \
    sed -i "s/^cidr_allow.*$/cidr_allow 127.0.0.1\\/32 10.0.0.0\\/8 172.16.0.0\\/12 192.168.0.0\\/16/" /etc/munin/munin-node.conf && \
    echo 'allow 172\.\d+\.\d+\.\d+' >> /etc/munin/munin-node.conf && \
    echo 'allow 10\.\d+\.\d+\.\d+' >> /etc/munin/munin-node.conf && \
    echo 'allow 192\.168\.\d+\.\d+' >> /etc/munin/munin-node.conf && \
    sed -i "s/^#host_name.*$/host_name energygrid-backend/" /etc/munin/munin-node.conf && \
    sed -i "s/^host \\*$/host 0.0.0.0/" /etc/munin/munin-node.conf

EXPOSE 8000 4949

CMD mkdir -p /run/munin && munin-node & sleep 2 && uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
