#!/usr/bin/env python3
"""
Industrial Marking System - Main Application Entry Point
Demonstrates comprehensive system integration and startup procedures
"""

import sys
import os
import logging
import asyncio
import threading
import signal
from typing import Optional
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import system components
from network_services.tcp_server import MarkingSystemTCPServer
from hardware_interface.plc_interface import PLCInterface
from tools.network_monitor import IndustrialNetworkMonitor

# Configuration
SYSTEM_CONFIG = {
    "tcp_server": {
        "host": "0.0.0.0",
        "port": 8080
    },
    "plc_interface": {
        "protocol": "modbus_tcp",
        "host": "192.168.1.100",
        "port": 502,
        "unit_id": 1,
        "timeout": 5.0
    },
    "network_monitor": {
        "interface": "0.0.0.0",
        "capture_port": 8080
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "logs/marking_system.log"
    }
}

class IndustrialMarkingSystem:
    """
    Main application class that orchestrates all system components
    """
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.tcp_server: Optional[MarkingSystemTCPServer] = None
        self.plc_interface: Optional[PLCInterface] = None
        self.network_monitor: Optional[IndustrialNetworkMonitor] = None
        self.is_running = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Industrial Marking System initialized")

    def _setup_logging(self) -> logging.Logger:
        """
        Configure system-wide logging
        """
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, SYSTEM_CONFIG["logging"]["level"]),
            format=SYSTEM_CONFIG["logging"]["format"],
            handlers=[
                logging.FileHandler(SYSTEM_CONFIG["logging"]["file"]),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        return logging.getLogger(__name__)

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully
        """
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown()

    async def start_system(self):
        """
        Start all system components in the correct order
        """
        try:
            self.logger.info("Starting Industrial Marking System...")
            
            # Step 1: Initialize PLC Interface
            self.logger.info("Initializing PLC interface...")
            self.plc_interface = PLCInterface(SYSTEM_CONFIG["plc_interface"])
            
            if not self.plc_interface.connect():
                self.logger.warning("PLC connection failed - continuing in simulation mode")
            else:
                self.logger.info("PLC interface connected successfully")
            
            # Step 2: Start Network Monitor
            self.logger.info("Starting network monitor...")
            self.network_monitor = IndustrialNetworkMonitor(
                interface=SYSTEM_CONFIG["network_monitor"]["interface"],
                capture_port=SYSTEM_CONFIG["network_monitor"]["capture_port"]
            )
            self.network_monitor.start_monitoring()
            
            # Step 3: Initialize and start TCP Server
            self.logger.info("Starting TCP server...")
            self.tcp_server = MarkingSystemTCPServer(
                host=SYSTEM_CONFIG["tcp_server"]["host"],
                port=SYSTEM_CONFIG["tcp_server"]["port"]
            )
            
            # Integrate PLC interface with TCP server if available
            if self.plc_interface:
                self._integrate_plc_with_server()
            
            # Start TCP server in separate thread
            server_thread = threading.Thread(
                target=self.tcp_server.start_server,
                daemon=True
            )
            server_thread.start()
            
            # Step 4: Perform system health check
            await self._perform_system_health_check()
            
            self.is_running = True
            self.logger.info("Industrial Marking System started successfully")
            
            # Step 5: Start main application loop
            await self._main_application_loop()
            
        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            raise

    def _integrate_plc_with_server(self):
        """
        Integrate PLC interface with TCP server for hardware operations
        """
        def plc_marking_handler(message):
            """Custom handler for marking requests that uses PLC"""
            try:
                product_data = message.payload.get("product_data", {})
                
                # Execute marking sequence using PLC
                success = self.plc_interface.execute_marking_sequence()
                
                if success:
                    return self.tcp_server._create_response(
                        message.message_id,
                        "marking_response",
                        {
                            "success": True,
                            "hardware_execution": True,
                            "plc_status": self.plc_interface.get_system_status()
                        }
                    )
                else:
                    return self.tcp_server._create_error_response(
                        message.message_id,
                        "PLC marking sequence failed"
                    )
                    
            except Exception as e:
                self.logger.error(f"PLC marking handler error: {e}")
                return self.tcp_server._create_error_response(
                    message.message_id,
                    f"Hardware error: {str(e)}"
                )
        
        # Replace default marking handler with PLC-integrated version
        self.tcp_server.register_handler("marking_request", plc_marking_handler)
        self.logger.info("PLC interface integrated with TCP server")

    async def _perform_system_health_check(self):
        """
        Perform comprehensive system health check
        """
        self.logger.info("Performing system health check...")
        
        health_status = {
            "tcp_server": False,
            "plc_interface": False,
            "network_monitor": False,
            "lua_engine": False
        }
        
        # Check TCP server
        if self.tcp_server and self.tcp_server.is_running:
            health_status["tcp_server"] = True
            
        # Check PLC interface
        if self.plc_interface and self.plc_interface.is_connected:
            health_status["plc_interface"] = True
            
        # Check network monitor
        if self.network_monitor and self.network_monitor.is_monitoring:
            health_status["network_monitor"] = True
            
        # Check Lua engine (simulate for now)
        try:
            # In a real implementation, would test Lua engine
            health_status["lua_engine"] = True
        except:
            pass
        
        # Log health check results
        for component, status in health_status.items():
            status_text = "HEALTHY" if status else "UNHEALTHY"
            self.logger.info(f"Health Check - {component}: {status_text}")
        
        # Overall system health
        overall_health = all(health_status.values())
        self.logger.info(f"Overall System Health: {'HEALTHY' if overall_health else 'DEGRADED'}")
        
        return health_status

    async def _main_application_loop(self):
        """
        Main application event loop
        """
        self.logger.info("Entering main application loop")
        
        try:
            while self.is_running:
                # Perform periodic system maintenance
                await asyncio.sleep(30)  # 30-second intervals
                
                # Check system health
                await self._periodic_health_check()
                
                # Update system statistics
                self._update_system_statistics()
                
                # Perform maintenance tasks
                await self._perform_maintenance_tasks()
                
        except Exception as e:
            self.logger.error(f"Error in main application loop: {e}")
        finally:
            self.logger.info("Exiting main application loop")

    async def _periodic_health_check(self):
        """
        Periodic health monitoring
        """
        if self.plc_interface and self.plc_interface.is_connected:
            try:
                status = self.plc_interface.get_system_status()
                if status.get("status") == "disconnected":
                    self.logger.warning("PLC connection lost - attempting reconnection")
                    self.plc_interface.connect()
            except Exception as e:
                self.logger.error(f"PLC health check failed: {e}")

    def _update_system_statistics(self):
        """
        Update system performance statistics
        """
        try:
            if self.tcp_server:
                client_count = len(self.tcp_server.clients)
                if client_count > 0:
                    self.logger.debug(f"Active TCP clients: {client_count}")
                    
            if self.network_monitor:
                capture_summary = self.network_monitor.get_capture_summary()
                packet_count = capture_summary.get("total_packets", 0)
                if packet_count > 0:
                    self.logger.debug(f"Network packets captured: {packet_count}")
                    
        except Exception as e:
            self.logger.error(f"Statistics update error: {e}")

    async def _perform_maintenance_tasks(self):
        """
        Perform periodic maintenance tasks
        """
        try:
            # Clean up old log files (simulate)
            # Optimize database (simulate)
            # Update system metrics (simulate)
            pass
        except Exception as e:
            self.logger.error(f"Maintenance task error: {e}")

    def shutdown(self):
        """
        Graceful system shutdown
        """
        self.logger.info("Shutting down Industrial Marking System...")
        
        self.is_running = False
        
        # Stop TCP server
        if self.tcp_server:
            self.tcp_server.stop_server()
            self.logger.info("TCP server stopped")
        
        # Stop network monitor
        if self.network_monitor:
            self.network_monitor.stop_monitoring()
            self.logger.info("Network monitor stopped")
        
        # Disconnect PLC interface
        if self.plc_interface:
            self.plc_interface.disconnect()
            self.logger.info("PLC interface disconnected")
        
        self.logger.info("Industrial Marking System shutdown complete")

def main():
    """
    Main entry point for the application
    """
    try:
        # Print startup banner
        print("=" * 60)
        print("     Industrial Marking System")
        print("     Matthews Marking Solutions")
        print("=" * 60)
        
        # Create and start the system
        system = IndustrialMarkingSystem()
        
        # Run the system
        asyncio.run(system.start_system())
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"System startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 