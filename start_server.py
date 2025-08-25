#!/usr/bin/env python3
"""
Travel Planner Backend Server Startup Script

This script handles server startup with proper validation and error handling.
"""

import os
import sys
import socket
import asyncio
import logging
import signal
import time
from pathlib import Path
from typing import Optional

# Add server directory to Python path
server_dir = Path(__file__).parent
sys.path.insert(0, str(server_dir))

from config.config import get_settings, validate_environment, get_environment_info
from database.db import init_db, check_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerStartup:
    """Server startup manager"""
    
    def __init__(self):
        self.settings = get_settings()
        self.server_process = None
        self.shutdown_event = asyncio.Event()
    
    def check_port_availability(self, port: int, host: str = "localhost") -> bool:
        """Check if port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection fails
        except Exception as e:
            logger.warning(f"Could not check port {port}: {e}")
            return True  # Assume available if we can't check
    
    def validate_startup_requirements(self) -> bool:
        """Validate all startup requirements"""
        logger.info("Validating startup requirements...")
        
        # Check environment configuration
        if not validate_environment():
            logger.error("Environment validation failed")
            return False
        
        # Check port availability
        if not self.check_port_availability(self.settings.PORT, self.settings.HOST):
            logger.error(f"Port {self.settings.PORT} is already in use")
            return False
        
        # Check database directory
        db_path = Path(self.settings.DATABASE_PATH)
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create database directory: {e}")
            return False
        
        # Check upload directory
        upload_path = Path(self.settings.UPLOAD_PATH)
        try:
            upload_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create upload directory: {e}")
            return False
        
        # Check log directory
        log_path = Path(self.settings.LOG_FILE).parent
        try:
            log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create log directory: {e}")
            return False
        
        logger.info("Startup requirements validated successfully")
        return True
    
    async def initialize_database(self) -> bool:
        """Initialize database connection"""
        logger.info("Initializing database...")
        
        try:
            await init_db()
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    async def check_database_health(self) -> bool:
        """Check database health"""
        logger.info("Checking database health...")
        
        try:
            is_healthy = await check_db_connection()
            if is_healthy:
                logger.info("Database health check passed")
                return True
            else:
                logger.error("Database health check failed")
                return False
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()
        logger.info("Shutdown signal received")
    
    def print_startup_info(self):
        """Print startup information"""
        env_info = get_environment_info()
        
        print("\n" + "="*60)
        print("🚀 Travel Planner Backend Server")
        print("="*60)
        print(f"📱 App Name: {env_info['app_name']}")
        print(f"🔢 Version: {env_info['app_version']}")
        print(f"🌐 Host: {env_info['host']}")
        print(f"🔌 Port: {env_info['port']}")
        print(f"🗄️  Database: {env_info['database_path']}")
        print(f"📁 Uploads: {env_info['upload_path']}")
        print(f"📊 Log Level: {env_info['log_level']}")
        print(f"🔒 Debug Mode: {env_info['debug']}")
        print(f"🌍 CORS Origins: {', '.join(env_info['cors_origins'])}")
        print("="*60)
        print(f"📚 API Documentation: http://{env_info['host']}:{env_info['port']}/docs")
        print(f"🔍 Health Check: http://{env_info['host']}:{env_info['port']}/health")
        print("="*60 + "\n")
    
    async def startup_sequence(self) -> bool:
        """Execute startup sequence"""
        logger.info("Starting Travel Planner Backend Server...")
        
        # Print startup information
        self.print_startup_info()
        
        # Validate requirements
        if not self.validate_startup_requirements():
            logger.error("Startup requirements validation failed")
            return False
        
        # Initialize database
        if not await self.initialize_database():
            logger.error("Database initialization failed")
            return False
        
        # Check database health
        if not await self.check_database_health():
            logger.error("Database health check failed")
            return False
        
        logger.info("Startup sequence completed successfully")
        return True
    
    async def run_server(self):
        """Run the server"""
        try:
            # Execute startup sequence
            if not await self.startup_sequence():
                logger.error("Startup sequence failed, exiting")
                return False
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Start server
            logger.info(f"Starting server on {self.settings.HOST}:{self.settings.PORT}")
            
            # Import and run uvicorn
            import uvicorn
            
            config = uvicorn.Config(
                "main:app",
                host=self.settings.HOST,
                port=self.settings.PORT,
                reload=self.settings.DEBUG,
                log_level=self.settings.LOG_LEVEL.lower(),
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            # Start server in background
            server_task = asyncio.create_task(server.serve())
            
            # Wait for shutdown signal
            await self.wait_for_shutdown()
            
            # Graceful shutdown
            logger.info("Initiating graceful shutdown...")
            server.should_exit = True
            
            # Wait for server to stop
            try:
                await asyncio.wait_for(server_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Server shutdown timeout, forcing exit")
            
            logger.info("Server shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            return False

async def main():
    """Main entry point"""
    startup_manager = ServerStartup()
    
    try:
        success = await startup_manager.run_server()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

def run_sync():
    """Run server synchronously (for compatibility)"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run server
    run_sync()
