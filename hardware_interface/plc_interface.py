"""
PLC Interface Module
Handles communication with industrial PLCs using Modbus TCP/RTU protocols
Demonstrates discrete I/O, industrial networking, and hardware integration
"""

import socket
import struct
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PLCConnectionType(Enum):
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    ETHERNET_IP = "ethernet_ip"

@dataclass
class IOPoint:
    address: int
    description: str
    data_type: str
    access: str  # 'read', 'write', 'read_write'

class PLCInterface:
    """
    Industrial PLC communication interface supporting multiple protocols
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.connection = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
        # Define I/O mapping for marking system
        self.discrete_inputs = {
            0: IOPoint(0, "Product Present Sensor", "bool", "read"),
            1: IOPoint(1, "System Ready", "bool", "read"),
            2: IOPoint(2, "Emergency Stop", "bool", "read"),
            3: IOPoint(3, "Marking Complete", "bool", "read")
        }
        
        self.discrete_outputs = {
            0: IOPoint(0, "Marking Start", "bool", "write"),
            1: IOPoint(1, "System Status LED", "bool", "write"),
            2: IOPoint(2, "Error Indicator", "bool", "write"),
            3: IOPoint(3, "Cycle Complete", "bool", "write")
        }
        
        self.analog_inputs = {
            0: IOPoint(0, "Line Speed", "float", "read"),
            1: IOPoint(1, "Print Quality Sensor", "float", "read")
        }

    def connect(self) -> bool:
        """
        Establish connection to PLC based on configuration
        """
        try:
            if self.config['protocol'] == PLCConnectionType.MODBUS_TCP.value:
                return self._connect_modbus_tcp()
            elif self.config['protocol'] == PLCConnectionType.MODBUS_RTU.value:
                return self._connect_modbus_rtu()
            else:
                self.logger.error(f"Unsupported protocol: {self.config['protocol']}")
                return False
                
        except Exception as e:
            self.logger.error(f"PLC connection failed: {e}")
            return False

    def _connect_modbus_tcp(self) -> bool:
        """
        Connect using Modbus TCP protocol
        """
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(self.config.get('timeout', 5.0))
            
            host = self.config['host']
            port = self.config.get('port', 502)
            
            self.connection.connect((host, port))
            self.is_connected = True
            
            self.logger.info(f"Connected to PLC via Modbus TCP: {host}:{port}")
            return True
            
        except socket.error as e:
            self.logger.error(f"Modbus TCP connection failed: {e}")
            return False

    def _connect_modbus_rtu(self) -> bool:
        """
        Connect using Modbus RTU protocol (serial)
        """
        # In production would use pyserial
        self.logger.info("Modbus RTU connection established")
        self.is_connected = True
        return True

    def read_discrete_input(self, address: int) -> Optional[bool]:
        """
        Read discrete input from PLC
        """
        if not self.is_connected:
            return None
            
        try:
            # Construct Modbus read discrete inputs request
            function_code = 0x02  # Read Discrete Inputs
            request = self._build_modbus_request(function_code, address, 1)
            
            self.connection.send(request)
            response = self.connection.recv(1024)
            
            return self._parse_discrete_response(response)
            
        except Exception as e:
            self.logger.error(f"Failed to read discrete input {address}: {e}")
            return None

    def write_discrete_output(self, address: int, value: bool) -> bool:
        """
        Write discrete output to PLC
        """
        if not self.is_connected:
            return False
            
        try:
            # Construct Modbus write single coil request
            function_code = 0x05  # Write Single Coil
            coil_value = 0xFF00 if value else 0x0000
            request = self._build_modbus_request(function_code, address, coil_value)
            
            self.connection.send(request)
            response = self.connection.recv(1024)
            
            return self._verify_write_response(response, address, coil_value)
            
        except Exception as e:
            self.logger.error(f"Failed to write discrete output {address}: {e}")
            return False

    def read_analog_input(self, address: int) -> Optional[float]:
        """
        Read analog input from PLC
        """
        if not self.is_connected:
            return None
            
        try:
            # Construct Modbus read input registers request
            function_code = 0x04  # Read Input Registers
            request = self._build_modbus_request(function_code, address, 1)
            
            self.connection.send(request)
            response = self.connection.recv(1024)
            
            raw_value = self._parse_register_response(response)
            if raw_value is not None:
                # Convert to engineering units based on configuration
                scale = self.config.get('analog_scale', {}).get(address, 1.0)
                offset = self.config.get('analog_offset', {}).get(address, 0.0)
                return (raw_value * scale) + offset
                
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to read analog input {address}: {e}")
            return None

    def _build_modbus_request(self, function_code: int, address: int, value: int) -> bytes:
        """
        Build Modbus TCP request packet
        """
        # Modbus TCP header
        transaction_id = 0x0001
        protocol_id = 0x0000
        length = 0x0006
        unit_id = self.config.get('unit_id', 1)
        
        # Modbus PDU
        starting_address = address
        quantity = value
        
        request = struct.pack('>HHHBBBHH',
                            transaction_id,
                            protocol_id,
                            length,
                            unit_id,
                            function_code,
                            starting_address,
                            quantity)
        
        return request

    def _parse_discrete_response(self, response: bytes) -> Optional[bool]:
        """
        Parse Modbus discrete input response
        """
        if len(response) < 9:
            return None
            
        # Skip header, get data byte
        data_byte = response[9]
        return bool(data_byte & 0x01)

    def _parse_register_response(self, response: bytes) -> Optional[int]:
        """
        Parse Modbus register response
        """
        if len(response) < 11:
            return None
            
        # Extract 16-bit register value
        register_value = struct.unpack('>H', response[9:11])[0]
        return register_value

    def _verify_write_response(self, response: bytes, address: int, value: int) -> bool:
        """
        Verify write operation response
        """
        # In production, would parse response to confirm write
        return len(response) > 0

    def get_system_status(self) -> Dict:
        """
        Get comprehensive system status from PLC
        """
        if not self.is_connected:
            return {"status": "disconnected"}
            
        status = {
            "connection": "connected",
            "discrete_inputs": {},
            "analog_inputs": {},
            "last_update": time.time()
        }
        
        # Read all discrete inputs
        for addr, point in self.discrete_inputs.items():
            value = self.read_discrete_input(addr)
            status["discrete_inputs"][point.description] = value
            
        # Read all analog inputs
        for addr, point in self.analog_inputs.items():
            value = self.read_analog_input(addr)
            status["analog_inputs"][point.description] = value
            
        return status

    def execute_marking_sequence(self) -> bool:
        """
        Execute marking sequence using discrete I/O
        """
        try:
            # Check if product is present
            product_present = self.read_discrete_input(0)
            if not product_present:
                self.logger.warning("No product detected for marking")
                return False
                
            # Check system ready
            system_ready = self.read_discrete_input(1)
            if not system_ready:
                self.logger.warning("System not ready for marking")
                return False
                
            # Start marking operation
            self.write_discrete_output(0, True)  # Marking Start
            self.write_discrete_output(1, True)  # Status LED
            
            # Wait for marking complete signal
            timeout = time.time() + 10.0  # 10 second timeout
            while time.time() < timeout:
                marking_complete = self.read_discrete_input(3)
                if marking_complete:
                    break
                time.sleep(0.1)
            else:
                self.logger.error("Marking operation timeout")
                self.write_discrete_output(2, True)  # Error indicator
                return False
                
            # Signal cycle complete
            self.write_discrete_output(3, True)
            time.sleep(0.5)
            self.write_discrete_output(3, False)
            
            self.logger.info("Marking sequence completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Marking sequence failed: {e}")
            self.write_discrete_output(2, True)  # Error indicator
            return False

    def disconnect(self):
        """
        Close PLC connection
        """
        if self.connection:
            self.connection.close()
            self.is_connected = False
            self.logger.info("PLC connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect() 