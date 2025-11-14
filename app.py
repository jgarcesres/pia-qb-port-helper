#!/usr/bin/env python3
"""
PIA qBittorrent Port Helper

Monitors the PIA WireGuard port file and automatically updates qBittorrent's
listening port via the WebUI API when the port changes.
"""

import os
import sys
import time
import json
import requests
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger


class QBittorrentAPI:
    """Handle qBittorrent WebUI API interactions."""
    
    def __init__(self, host: str, username: str = None, password: str = None, disable_auth: bool = False):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.disable_auth = disable_auth
        self.session = requests.Session()
        self.logged_in = False
        
    def login(self) -> bool:
        """Login to qBittorrent WebUI."""
        if self.disable_auth:
            logger.info("Authentication disabled, skipping login")
            self.logged_in = True
            return True
            
        try:
            response = self.session.post(
                f"{self.host}/api/v2/auth/login",
                data={"username": self.username, "password": self.password},
                timeout=10
            )
            
            if response.status_code == 200 and response.text == "Ok.":
                self.logged_in = True
                logger.info("Successfully logged in to qBittorrent")
                return True
            else:
                logger.error(f"Failed to login to qBittorrent: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to qBittorrent: {e}")
            return False
    
    def get_preferences(self) -> Optional[dict]:
        """Get current qBittorrent preferences."""
        if not self.logged_in:
            if not self.login():
                return None
                
        try:
            response = self.session.get(f"{self.host}/api/v2/app/preferences", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get preferences: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting preferences: {e}")
            return None
    
    def set_port(self, port: int) -> bool:
        """Set the listening port in qBittorrent."""
        if not self.logged_in:
            if not self.login():
                return False
                
        preferences = {
            "listen_port": port,
            "upnp": False,  # Disable UPnP when using VPN
            "random_port": False
        }
        
        try:
            response = self.session.post(
                f"{self.host}/api/v2/app/setPreferences",
                data={"json": json.dumps(preferences)},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully set qBittorrent port to {port}")
                return True
            else:
                logger.error(f"Failed to set port: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error setting port: {e}")
            return False


class PortFileHandler(FileSystemEventHandler):
    """Handle port file changes."""
    
    def __init__(self, port_file_path: str, qb_api: QBittorrentAPI):
        self.port_file_path = port_file_path
        self.qb_api = qb_api
        self.last_port = None
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.src_path == self.port_file_path and not event.is_directory:
            self.update_port()
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.src_path == self.port_file_path and not event.is_directory:
            self.update_port()
    
    def update_port(self):
        """Read the port file and update qBittorrent if the port changed."""
        try:
            
            if not os.path.exists(self.port_file_path):
                logger.warning(f"Port file {self.port_file_path} does not exist")
                return
                
            with open(self.port_file_path, 'r') as f:
                port_str = f.read().strip()
                
            if not port_str:
                # If we had a port before and now the file is empty, don't clear it
                if self.last_port is not None:
                    logger.warning(f"Port file is empty but previous port was {self.last_port}. Not clearing port from qBittorrent.")
                else:
                    logger.warning("Port file is empty")
                return
                
            try:
                port = int(port_str)
            except ValueError:
                logger.error(f"Invalid port number in file: {port_str}")
                return
                
            if port == self.last_port:
                logger.debug(f"Port unchanged: {port}")
                return
                
            logger.info(f"Port changed from {self.last_port} to {port}")
            
            if self.qb_api.set_port(port):
                self.last_port = port
            else:
                logger.error("Failed to update qBittorrent port")
                
        except Exception as e:
            logger.error(f"Error reading port file: {e}")


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration with loguru."""
    logger.remove()  # Remove default handler
    if log_level == "DEBUG":
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
    else: 
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            colorize=True
        )


def main():
    """Main application entry point."""
    # Configuration from environment variables
    QB_HOST = os.getenv("QB_HOST", "http://localhost:8080")
    QB_USERNAME = os.getenv("QB_USERNAME", "admin")
    QB_PASSWORD = os.getenv("QB_PASSWORD", "adminadmin")
    QB_DISABLE_AUTH = os.getenv("QB_DISABLE_AUTH", "false").lower() in ("true", "1", "yes")
    PORT_FILE = os.getenv("PORT_FILE", "/app/port.dat")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))
    
    setup_logging(log_level=LOG_LEVEL)
    
    logger.info("Starting PIA qBittorrent Port Helper")
    logger.info(f"qBittorrent Host: {QB_HOST}")
    logger.info(f"Authentication: {'Disabled' if QB_DISABLE_AUTH else 'Enabled'}")
    logger.info(f"Port File: {PORT_FILE}")
    
    # Initialize qBittorrent API
    qb_api = QBittorrentAPI(QB_HOST, QB_USERNAME, QB_PASSWORD, disable_auth=QB_DISABLE_AUTH)
    
    # Test connection
    if not qb_api.login():
        logger.error("Failed to connect to qBittorrent. Exiting.")
        sys.exit(1)
    
    # Create port file handler
    port_handler = PortFileHandler(PORT_FILE, qb_api)
    
    # Do initial port check and update if file exists
    if os.path.exists(PORT_FILE):
        logger.info("Checking initial port configuration")
        
        # Read the port from file
        try:
            with open(PORT_FILE, 'r') as f:
                file_port_str = f.read().strip()
            
            if file_port_str:
                file_port = int(file_port_str)
                
                # Get current qBittorrent port
                prefs = qb_api.get_preferences()
                if prefs:
                    current_port = prefs.get('listen_port')
                    
                    if current_port == file_port:
                        logger.info(f"Port already correctly set to {file_port}, no update needed")
                        port_handler.last_port = file_port  # Set last_port to avoid duplicate updates
                    else:
                        logger.info(f"Port mismatch: qBittorrent={current_port}, PIA file={file_port}. Updating...")
                        port_handler.update_port()
                else:
                    logger.warning("Could not read current qBittorrent preferences, performing update anyway")
                    port_handler.update_port()
            else:
                logger.warning("Port file is empty")
                
        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Error reading port file during initial check: {e}")
            
    else:
        logger.warning(f"Port file {PORT_FILE} does not exist yet. Waiting for it to be created.")
    
    # Setup file watcher
    observer = Observer()
    observer.schedule(port_handler, path=os.path.dirname(PORT_FILE), recursive=False)
    observer.start()
    
    logger.info("File watcher started. Monitoring for port changes...")
    
    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            
            # Periodic health check - verify we can still connect to qBittorrent
            prefs = qb_api.get_preferences()
            if prefs is None:
                logger.warning("Lost connection to qBittorrent, attempting to reconnect...")
                qb_api.logged_in = False
                if not qb_api.login():
                    logger.error("Failed to reconnect to qBittorrent")
            else:
                logger.debug(f"Current qBittorrent listening port: {prefs.get('listen_port', 'unknown')}")
                
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
    finally:
        observer.stop()
        observer.join()
        logger.info("Application stopped")


if __name__ == "__main__":
    main()
