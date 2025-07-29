"""
TCP Server for Industrial Marking System
Handles network communication with client applications and monitoring systems
Demonstrates TCP/IP networking, protocol design, and industrial connectivity
"""

import socket
import threading
import json
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class NetworkMessage:
    message_id: str
    timestamp: str
    message_type: str
    payload: Dict
    client_id: str = ""

class MarkingSystemTCPServer:
    """
    TCP server for industrial marking system communication
    Supports multiple concurrent clients and various message types
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False
        self.clients = {}  # client_id: socket
        self.message_handlers = {}
        self.logger = logging.getLogger(__name__)
        
        # System status for client queries
        self.system_status = {
            "controller_status": "ready",
            "hardware_connected": True,
            "marks_completed": 0,
            "error_count": 0,
            "uptime": 0,
            "last_update": datetime.now().isoformat()
        }
        
        # Register default message handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """
        Register default message handlers for common operations
        """
        self.register_handler("status_request", self._handle_status_request)
        self.register_handler("marking_request", self._handle_marking_request)
        self.register_handler("configuration_update", self._handle_configuration_update)
        self.register_handler("system_command", self._handle_system_command)
        self.register_handler("heartbeat", self._handle_heartbeat)

    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a message handler for specific message types
        """
        self.message_handlers[message_type] = handler
        self.logger.info(f"Registered handler for message type: {message_type}")

    def start_server(self):
        """
        Start the TCP server and begin accepting connections
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.is_running = True
            self.logger.info(f"TCP Server started on {self.host}:{self.port}")
            
            # Start server monitoring thread
            monitoring_thread = threading.Thread(target=self._monitor_system, daemon=True)
            monitoring_thread.start()
            
            # Accept client connections
            while self.is_running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_id = f"client_{int(time.time())}_{client_address[1]}"
                    
                    self.clients[client_id] = {
                        "socket": client_socket,
                        "address": client_address,
                        "connected_at": datetime.now().isoformat(),
                        "last_activity": time.time()
                    }
                    
                    # Start client handler thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_id),
                        daemon=True
                    )
                    client_thread.start()
                    
                    self.logger.info(f"New client connected: {client_id} from {client_address}")
                    
                except socket.error as e:
                    if self.is_running:
                        self.logger.error(f"Error accepting client connection: {e}")
                        
        except Exception as e:
            self.logger.error(f"Failed to start TCP server: {e}")
            raise

    def _handle_client(self, client_socket: socket.socket, client_id: str):
        """
        Handle individual client connection
        """
        buffer = ""
        
        try:
            while self.is_running:
                # Receive data from client
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                
                # Process complete messages (assuming newline-delimited JSON)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._process_message(line.strip(), client_id)
                        
                # Update client activity timestamp
                self.clients[client_id]["last_activity"] = time.time()
                
        except socket.error as e:
            self.logger.warning(f"Client {client_id} connection error: {e}")
        finally:
            self._disconnect_client(client_id)

    def _process_message(self, message_data: str, client_id: str):
        """
        Process incoming message from client
        """
        try:
            # Parse JSON message
            message_dict = json.loads(message_data)
            message = NetworkMessage(**message_dict)
            message.client_id = client_id
            
            self.logger.debug(f"Received message: {message.message_type} from {client_id}")
            
            # Route message to appropriate handler
            handler = self.message_handlers.get(message.message_type)
            if handler:
                response = handler(message)
                if response:
                    self._send_response(client_id, response)
            else:
                self.logger.warning(f"No handler for message type: {message.message_type}")
                error_response = self._create_error_response(
                    message.message_id,
                    f"Unknown message type: {message.message_type}"
                )
                self._send_response(client_id, error_response)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from client {client_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message from {client_id}: {e}")

    def _handle_status_request(self, message: NetworkMessage) -> NetworkMessage:
        """
        Handle system status request
        """
        response_payload = {
            "system_status": self.system_status,
            "client_count": len(self.clients),
            "server_uptime": time.time() - self.system_status.get("start_time", time.time())
        }
        
        return NetworkMessage(
            message_id=f"response_{message.message_id}",
            timestamp=datetime.now().isoformat(),
            message_type="status_response",
            payload=response_payload
        )

    def _handle_marking_request(self, message: NetworkMessage) -> NetworkMessage:
        """
        Handle marking operation request
        """
        try:
            product_data = message.payload.get("product_data", {})
            
            # Validate marking request
            if not product_data.get("serial_number"):
                return self._create_error_response(
                    message.message_id,
                    "Missing required field: serial_number"
                )
            
            # Simulate marking operation
            marking_result = {
                "success": True,
                "mark_id": f"mark_{int(time.time())}",
                "completion_time": datetime.now().isoformat(),
                "product_data": product_data
            }
            
            # Update system statistics
            self.system_status["marks_completed"] += 1
            self.system_status["last_update"] = datetime.now().isoformat()
            
            return NetworkMessage(
                message_id=f"response_{message.message_id}",
                timestamp=datetime.now().isoformat(),
                message_type="marking_response",
                payload=marking_result
            )
            
        except Exception as e:
            return self._create_error_response(message.message_id, str(e))

    def _handle_configuration_update(self, message: NetworkMessage) -> NetworkMessage:
        """
        Handle system configuration updates
        """
        try:
            config_data = message.payload.get("configuration", {})
            
            # Validate and apply configuration
            # In production, would validate against schema
            self.logger.info(f"Configuration update received: {list(config_data.keys())}")
            
            return NetworkMessage(
                message_id=f"response_{message.message_id}",
                timestamp=datetime.now().isoformat(),
                message_type="configuration_response",
                payload={"success": True, "message": "Configuration updated"}
            )
            
        except Exception as e:
            return self._create_error_response(message.message_id, str(e))

    def _handle_system_command(self, message: NetworkMessage) -> NetworkMessage:
        """
        Handle system control commands
        """
        command = message.payload.get("command")
        
        if command == "shutdown":
            self.logger.info("Shutdown command received")
            threading.Timer(1.0, self.stop_server).start()
            
        elif command == "reset_statistics":
            self.system_status["marks_completed"] = 0
            self.system_status["error_count"] = 0
            
        elif command == "system_test":
            # Simulate system test
            pass
            
        return NetworkMessage(
            message_id=f"response_{message.message_id}",
            timestamp=datetime.now().isoformat(),
            message_type="command_response",
            payload={"success": True, "command": command}
        )

    def _handle_heartbeat(self, message: NetworkMessage) -> NetworkMessage:
        """
        Handle client heartbeat messages
        """
        return NetworkMessage(
            message_id=f"response_{message.message_id}",
            timestamp=datetime.now().isoformat(),
            message_type="heartbeat_response",
            payload={"server_time": datetime.now().isoformat()}
        )

    def _create_error_response(self, request_id: str, error_message: str) -> NetworkMessage:
        """
        Create standardized error response
        """
        return NetworkMessage(
            message_id=f"error_{request_id}",
            timestamp=datetime.now().isoformat(),
            message_type="error_response",
            payload={"error": error_message}
        )

    def _send_response(self, client_id: str, response: NetworkMessage):
        """
        Send response message to specific client
        """
        try:
            client_info = self.clients.get(client_id)
            if client_info:
                message_json = json.dumps(asdict(response)) + '\n'
                client_info["socket"].send(message_json.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Failed to send response to {client_id}: {e}")
            self._disconnect_client(client_id)

    def broadcast_message(self, message: NetworkMessage):
        """
        Broadcast message to all connected clients
        """
        message_json = json.dumps(asdict(message)) + '\n'
        disconnected_clients = []
        
        for client_id, client_info in self.clients.items():
            try:
                client_info["socket"].send(message_json.encode('utf-8'))
            except Exception as e:
                self.logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self._disconnect_client(client_id)

    def _disconnect_client(self, client_id: str):
        """
        Disconnect and clean up client
        """
        if client_id in self.clients:
            try:
                self.clients[client_id]["socket"].close()
            except:
                pass
            del self.clients[client_id]
            self.logger.info(f"Client {client_id} disconnected")

    def _monitor_system(self):
        """
        Monitor system status and broadcast updates
        """
        while self.is_running:
            try:
                # Update system status
                self.system_status["uptime"] = time.time() - self.system_status.get("start_time", time.time())
                self.system_status["client_count"] = len(self.clients)
                
                # Broadcast status update to monitoring clients
                status_update = NetworkMessage(
                    message_id=f"status_update_{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    message_type="status_broadcast",
                    payload={"system_status": self.system_status}
                )
                
                # Only broadcast if there are clients
                if self.clients:
                    self.broadcast_message(status_update)
                
                time.sleep(30)  # Broadcast every 30 seconds
                
            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")

    def stop_server(self):
        """
        Stop the TCP server and close all connections
        """
        self.is_running = False
        
        # Disconnect all clients
        for client_id in list(self.clients.keys()):
            self._disconnect_client(client_id)
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
            
        self.logger.info("TCP Server stopped")

    def get_client_info(self) -> Dict:
        """
        Get information about connected clients
        """
        return {
            client_id: {
                "address": info["address"],
                "connected_at": info["connected_at"],
                "last_activity": info["last_activity"]
            }
            for client_id, info in self.clients.items()
        } 