# PIA qBittorrent Port Helper

A Docker service that automatically monitors and updates qBittorrent's listening port when using Private Internet Access (PIA) VPN with WireGuard. This service ensures your qBittorrent client always uses the correct port provided by PIA's port forwarding feature.

## Overview

When using PIA VPN with port forwarding enabled, the VPN client writes the forwarded port number to a file. This service monitors that file and automatically updates qBittorrent's configuration via its WebUI API whenever the port changes, ensuring optimal connectivity and performance.

## Features

- **Automatic Port Updates**: Monitors PIA's port file and updates qBittorrent instantly when the port changes
- **Smart Port Handling**: Won't clear the port if the file becomes empty after having a value
- **Optional Authentication**: Works with qBittorrent instances that have localhost authentication disabled
- **Health Monitoring**: Periodic health checks to ensure qBittorrent connectivity
- **Robust Error Handling**: Automatic reconnection and error recovery
- **Beautiful Logging**: Uses loguru for colorized, structured logging
- **Docker Ready**: Lightweight container with multi-architecture support
- **Configurable**: All settings customizable via environment variables

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QB_HOST` | `http://qbittorrent:8080` | qBittorrent WebUI URL |
| `QB_USERNAME` | `admin` | qBittorrent WebUI username |
| `QB_PASSWORD` | `adminadmin` | qBittorrent WebUI password |
| `QB_DISABLE_AUTH` | `false` | Set to `true` to disable authentication (for qBittorrent with localhost auth disabled) |
| `PORT_FILE` | `/app/port.dat` | Path to PIA port file (mounted from host) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CHECK_INTERVAL` | `10` | Health check interval in seconds |

## Quick Start

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  pia-wireguard:
    image: thrnz/docker-wireguard-pia
    container_name: pia-wireguard
    cap_add:
      - NET_ADMIN
    environment:
      - LOC=us_east
      - USER=your_pia_username
      - PASS=your_pia_password
      - LOCAL_NETWORK=192.168.1.0/24
      - PORT_FORWARDING=1
    volumes:
      - ./wireguard:/etc/wireguard
    restart: unless-stopped

  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    container_name: qbittorrent
    network_mode: "service:pia-wireguard"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - WEBUI_PORT=8080
    volumes:
      - ./qbittorrent:/config
      - ./downloads:/downloads
    restart: unless-stopped
    depends_on:
      - pia-wireguard

  pia-qb-port-helper:
    image: ghcr.io/yourusername/pia-qb-port-helper:latest
    container_name: pia-qb-port-helper
    environment:
      - QB_HOST=http://localhost:8080
      - QB_USERNAME=admin
      - QB_PASSWORD=your_qb_password
      - LOG_LEVEL=INFO
    volumes:
      - ./wireguard/port.dat:/app/port.dat:ro
    network_mode: "service:pia-wireguard"
    restart: unless-stopped
    depends_on:
      - qbittorrent
```

### Using Docker Run

```bash
docker run -d \
  --name pia-qb-port-helper \
  --network container:pia-wireguard \
  -e QB_HOST=http://localhost:8080 \
  -e QB_USERNAME=admin \
  -e QB_PASSWORD=your_password \
  -v ./wireguard/port.dat:/app/port.dat:ro \
  ghcr.io/yourusername/pia-qb-port-helper:latest
```

### Using Without Authentication

If your qBittorrent instance has authentication disabled for localhost (common in container setups), you can disable authentication by setting `QB_DISABLE_AUTH=true`:

```bash
docker run -d \
  --name pia-qb-port-helper \
  --network container:pia-wireguard \
  -e QB_HOST=http://localhost:8080 \
  -e QB_DISABLE_AUTH=true \
  -v ./wireguard/port.dat:/app/port.dat:ro \
  ghcr.io/yourusername/pia-qb-port-helper:latest
```

Note: Username and password are not required when authentication is disabled.

## Building from Source

### Prerequisites

- Docker
- Git

### Build Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pia-qb-port-helper.git
   cd pia-qb-port-helper
   ```

2. Build the Docker image:
   ```bash
   docker build -t pia-qb-port-helper .
   ```

3. Run the container:
   ```bash
   docker run -d \
     --name pia-qb-port-helper \
     -e QB_HOST=http://your-qbittorrent:8080 \
     -e QB_USERNAME=admin \
     -e QB_PASSWORD=your_password \
     -v /path/to/wireguard/port.dat:/app/port.dat:ro \
     pia-qb-port-helper
   ```

## Development

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export QB_HOST=http://localhost:8080
   export QB_USERNAME=admin
   export QB_PASSWORD=adminadmin
   export PORT_FILE=./port.dat
   export LOG_LEVEL=DEBUG
   ```

3. Run the application:
   ```bash
   python app.py
   ```

### Testing

Create a test port file to verify functionality:

```bash
echo "12345" > port.dat
```

The service should detect the file and attempt to update qBittorrent.

## Troubleshooting

### Common Issues

1. **Connection Failed**: Ensure qBittorrent WebUI is accessible and credentials are correct
2. **Port File Not Found**: Verify the PIA WireGuard container is properly configured with `PORT_FORWARDING=1`
3. **Permission Denied**: Ensure the port file is readable by the container user

### Logs

Check container logs for detailed information:

```bash
docker logs pia-qb-port-helper
```

Enable debug logging for more verbose output:

```bash
docker run ... -e LOG_LEVEL=DEBUG ...
```

## Security Considerations

- Use strong passwords for qBittorrent WebUI
- Run containers with non-root users (implemented in Dockerfile)
- Keep the port file read-only in the container
- Regularly update the container image for security patches

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [PIA WireGuard Docker](https://github.com/thrnz/docker-wireguard-pia) for the VPN container
- [qBittorrent](https://www.qbittorrent.org/) for the excellent BitTorrent client
- [loguru](https://github.com/Delgan/loguru) for beautiful logging
