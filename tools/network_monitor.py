"""
Network Monitoring Tool for Industrial Marking Systems
Demonstrates network analysis, protocol debugging, and monitoring capabilities
Similar to Wireshark functionality for industrial environments
"""

import socket
import struct
import time
import threading
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import logging

@dataclass
class NetworkPacket:
    timestamp: float
    source_ip: str
    dest_ip: str
    source_port: int
    dest_port: int
    protocol: str
    payload_size: int
    raw_data: bytes
    decoded_content: Optional[Dict] = None

@dataclass
class ConnectionSummary:
    source_ip: str
    dest_ip: str
    port: int
    protocol: str
    packet_count: int
    total_bytes: int
    first_seen: float
    last_seen: float
    connection_state: str

class IndustrialNetworkMonitor:
    """
    Network monitoring tool for industrial marking systems
    Captures and analyzes network traffic for debugging and optimization
    """
    
    def __init__(self, interface: str = "0.0.0.0", capture_port: int = None):
        self.interface = interface
        self.capture_port = capture_port
        self.is_monitoring = False
        self.captured_packets = []
        self.connection_summary = defaultdict(lambda: {
            'packet_count': 0,
            'total_bytes': 0,
            'first_seen': None,
            'last_seen': None
        })
        self.protocol_stats = defaultdict(int)
        self.logger = logging.getLogger(__name__)
        
        # Industrial protocol parsers
        self.protocol_parsers = {
            'modbus': self._parse_modbus_packet,
            'ethernet_ip': self._parse_ethernet_ip_packet,
            'marking_system': self._parse_marking_system_packet
        }
        
        # Monitoring filters
        self.filters = {
            'port_filter': None,
            'ip_filter': None,
            'protocol_filter': None,
            'content_filter': None
        }

    def start_monitoring(self, duration: Optional[float] = None):
        """
        Start network packet capture
        """
        self.is_monitoring = True
        self.logger.info(f"Starting network monitoring on {self.interface}")
        
        # Start packet capture thread
        capture_thread = threading.Thread(target=self._capture_packets, daemon=True)
        capture_thread.start()
        
        # Start analysis thread
        analysis_thread = threading.Thread(target=self._analyze_traffic, daemon=True)
        analysis_thread.start()
        
        if duration:
            # Stop monitoring after specified duration
            threading.Timer(duration, self.stop_monitoring).start()

    def _capture_packets(self):
        """
        Capture network packets using raw socket
        """
        try:
            # Create raw socket for packet capture
            if self.capture_port:
                # Monitor specific port using TCP socket
                self._monitor_tcp_port()
            else:
                # Monitor all traffic (requires admin privileges)
                self._monitor_raw_traffic()
                
        except Exception as e:
            self.logger.error(f"Packet capture error: {e}")

    def _monitor_tcp_port(self):
        """
        Monitor specific TCP port for marking system traffic
        """
        try:
            # Create listening socket
            monitor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            monitor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            monitor_socket.bind((self.interface, self.capture_port))
            monitor_socket.listen(5)
            monitor_socket.settimeout(1.0)
            
            self.logger.info(f"Monitoring TCP port {self.capture_port}")
            
            while self.is_monitoring:
                try:
                    client_socket, client_address = monitor_socket.accept()
                    # Handle connection in separate thread
                    connection_thread = threading.Thread(
                        target=self._handle_monitored_connection,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    connection_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_monitoring:
                        self.logger.error(f"Connection accept error: {e}")
                        
        except Exception as e:
            self.logger.error(f"TCP monitoring error: {e}")

    def _handle_monitored_connection(self, client_socket: socket.socket, client_address: Tuple):
        """
        Handle and monitor individual connection
        """
        connection_key = f"{client_address[0]}:{client_address[1]}"
        
        try:
            while self.is_monitoring:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Create packet record
                packet = NetworkPacket(
                    timestamp=time.time(),
                    source_ip=client_address[0],
                    dest_ip=self.interface,
                    source_port=client_address[1],
                    dest_port=self.capture_port,
                    protocol="TCP",
                    payload_size=len(data),
                    raw_data=data
                )
                
                # Try to decode content
                packet.decoded_content = self._decode_packet_content(data)
                
                # Store packet if it passes filters
                if self._passes_filters(packet):
                    self.captured_packets.append(packet)
                    self._update_connection_stats(packet)
                
        except Exception as e:
            self.logger.error(f"Connection monitoring error: {e}")
        finally:
            client_socket.close()

    def _monitor_raw_traffic(self):
        """
        Monitor raw network traffic (requires administrative privileges)
        """
        try:
            # Create raw socket (Linux/Unix)
            raw_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
            
            while self.is_monitoring:
                raw_data, addr = raw_socket.recvfrom(65565)
                
                # Parse Ethernet frame
                packet = self._parse_raw_packet(raw_data)
                if packet and self._passes_filters(packet):
                    self.captured_packets.append(packet)
                    self._update_connection_stats(packet)
                    
        except OSError as e:
            # Fallback to UDP monitoring if raw sockets not available
            self.logger.warning(f"Raw socket not available: {e}. Using UDP monitoring.")
            self._monitor_udp_traffic()

    def _monitor_udp_traffic(self):
        """
        Monitor UDP traffic as fallback
        """
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.bind(('', 0))  # Bind to any available port
            udp_socket.settimeout(1.0)
            
            while self.is_monitoring:
                try:
                    data, addr = udp_socket.recvfrom(4096)
                    
                    packet = NetworkPacket(
                        timestamp=time.time(),
                        source_ip=addr[0],
                        dest_ip="localhost",
                        source_port=addr[1],
                        dest_port=0,
                        protocol="UDP",
                        payload_size=len(data),
                        raw_data=data
                    )
                    
                    packet.decoded_content = self._decode_packet_content(data)
                    
                    if self._passes_filters(packet):
                        self.captured_packets.append(packet)
                        self._update_connection_stats(packet)
                        
                except socket.timeout:
                    continue
                    
        except Exception as e:
            self.logger.error(f"UDP monitoring error: {e}")

    def _parse_raw_packet(self, raw_data: bytes) -> Optional[NetworkPacket]:
        """
        Parse raw network packet
        """
        try:
            # Parse Ethernet header (14 bytes)
            eth_header = struct.unpack('!6s6sH', raw_data[:14])
            eth_protocol = socket.ntohs(eth_header[2])
            
            # Check if IP packet
            if eth_protocol == 8:  # IPv4
                return self._parse_ip_packet(raw_data[14:])
                
        except Exception as e:
            self.logger.debug(f"Raw packet parsing error: {e}")
            
        return None

    def _parse_ip_packet(self, ip_data: bytes) -> Optional[NetworkPacket]:
        """
        Parse IP packet
        """
        try:
            # Parse IP header
            ip_header = struct.unpack('!BBHHHBBH4s4s', ip_data[:20])
            
            source_ip = socket.inet_ntoa(ip_header[8])
            dest_ip = socket.inet_ntoa(ip_header[9])
            protocol = ip_header[6]
            
            # Parse TCP/UDP header
            if protocol == 6:  # TCP
                return self._parse_tcp_packet(ip_data[20:], source_ip, dest_ip)
            elif protocol == 17:  # UDP
                return self._parse_udp_packet(ip_data[20:], source_ip, dest_ip)
                
        except Exception as e:
            self.logger.debug(f"IP packet parsing error: {e}")
            
        return None

    def _parse_tcp_packet(self, tcp_data: bytes, source_ip: str, dest_ip: str) -> Optional[NetworkPacket]:
        """
        Parse TCP packet
        """
        try:
            tcp_header = struct.unpack('!HHLLBBHHH', tcp_data[:20])
            source_port = tcp_header[0]
            dest_port = tcp_header[1]
            
            # Extract payload
            payload = tcp_data[20:]
            
            packet = NetworkPacket(
                timestamp=time.time(),
                source_ip=source_ip,
                dest_ip=dest_ip,
                source_port=source_port,
                dest_port=dest_port,
                protocol="TCP",
                payload_size=len(payload),
                raw_data=payload
            )
            
            packet.decoded_content = self._decode_packet_content(payload)
            return packet
            
        except Exception as e:
            self.logger.debug(f"TCP packet parsing error: {e}")
            
        return None

    def _decode_packet_content(self, data: bytes) -> Optional[Dict]:
        """
        Decode packet content based on known protocols
        """
        try:
            # Try to decode as JSON (marking system protocol)
            if data.startswith(b'{'):
                return json.loads(data.decode('utf-8'))
                
            # Try to decode as Modbus
            if len(data) >= 8 and data[2:4] == b'\x00\x00':
                return self._parse_modbus_packet(data)
                
            # Try to decode as text
            try:
                text = data.decode('utf-8')
                if text.isprintable():
                    return {"content_type": "text", "data": text}
            except UnicodeDecodeError:
                pass
                
            # Return hex representation for binary data
            return {
                "content_type": "binary",
                "hex_data": data.hex(),
                "ascii_preview": ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[:32])
            }
            
        except Exception as e:
            self.logger.debug(f"Content decoding error: {e}")
            
        return None

    def _parse_modbus_packet(self, data: bytes) -> Dict:
        """
        Parse Modbus TCP packet
        """
        if len(data) < 8:
            return {"protocol": "modbus", "error": "packet too short"}
            
        try:
            # Modbus TCP header
            transaction_id = struct.unpack('>H', data[0:2])[0]
            protocol_id = struct.unpack('>H', data[2:4])[0]
            length = struct.unpack('>H', data[4:6])[0]
            unit_id = data[6]
            function_code = data[7]
            
            return {
                "protocol": "modbus",
                "transaction_id": transaction_id,
                "protocol_id": protocol_id,
                "length": length,
                "unit_id": unit_id,
                "function_code": function_code,
                "function_name": self._get_modbus_function_name(function_code)
            }
            
        except Exception as e:
            return {"protocol": "modbus", "error": str(e)}

    def _get_modbus_function_name(self, function_code: int) -> str:
        """
        Get Modbus function name from code
        """
        function_names = {
            1: "Read Coils",
            2: "Read Discrete Inputs",
            3: "Read Holding Registers",
            4: "Read Input Registers",
            5: "Write Single Coil",
            6: "Write Single Register",
            15: "Write Multiple Coils",
            16: "Write Multiple Registers"
        }
        return function_names.get(function_code, f"Unknown ({function_code})")

    def _parse_ethernet_ip_packet(self, data: bytes) -> Dict:
        """
        Parse EtherNet/IP packet
        """
        return {"protocol": "ethernet_ip", "data": data.hex()[:32]}

    def _parse_marking_system_packet(self, data: bytes) -> Dict:
        """
        Parse custom marking system protocol
        """
        try:
            # Assume JSON-based protocol
            content = json.loads(data.decode('utf-8'))
            return {
                "protocol": "marking_system",
                "message_type": content.get("message_type"),
                "payload_size": len(content.get("payload", {})),
                "timestamp": content.get("timestamp")
            }
        except:
            return {"protocol": "marking_system", "error": "decode failed"}

    def _passes_filters(self, packet: NetworkPacket) -> bool:
        """
        Check if packet passes configured filters
        """
        if self.filters['port_filter'] and packet.dest_port != self.filters['port_filter']:
            return False
            
        if self.filters['ip_filter'] and self.filters['ip_filter'] not in [packet.source_ip, packet.dest_ip]:
            return False
            
        if self.filters['protocol_filter'] and packet.protocol != self.filters['protocol_filter']:
            return False
            
        return True

    def _update_connection_stats(self, packet: NetworkPacket):
        """
        Update connection statistics
        """
        connection_key = f"{packet.source_ip}:{packet.source_port}->{packet.dest_ip}:{packet.dest_port}"
        
        stats = self.connection_summary[connection_key]
        stats['packet_count'] += 1
        stats['total_bytes'] += packet.payload_size
        
        if stats['first_seen'] is None:
            stats['first_seen'] = packet.timestamp
        stats['last_seen'] = packet.timestamp
        
        self.protocol_stats[packet.protocol] += 1

    def _analyze_traffic(self):
        """
        Continuously analyze captured traffic
        """
        while self.is_monitoring:
            try:
                # Perform analysis every 10 seconds
                time.sleep(10)
                
                if self.captured_packets:
                    self._detect_anomalies()
                    self._generate_performance_metrics()
                    
            except Exception as e:
                self.logger.error(f"Traffic analysis error: {e}")

    def _detect_anomalies(self):
        """
        Detect network anomalies and potential issues
        """
        # Check for unusual traffic patterns
        recent_packets = [p for p in self.captured_packets if time.time() - p.timestamp < 60]
        
        if len(recent_packets) > 1000:
            self.logger.warning("High traffic volume detected")
            
        # Check for failed connections
        error_packets = [p for p in recent_packets if p.decoded_content and 
                        isinstance(p.decoded_content, dict) and 
                        'error' in p.decoded_content]
        
        if len(error_packets) > 10:
            self.logger.warning(f"High error rate detected: {len(error_packets)} errors in last minute")

    def _generate_performance_metrics(self):
        """
        Generate network performance metrics
        """
        if not self.captured_packets:
            return
            
        recent_packets = [p for p in self.captured_packets if time.time() - p.timestamp < 300]
        
        metrics = {
            "packets_per_minute": len(recent_packets) / 5,
            "average_packet_size": sum(p.payload_size for p in recent_packets) / len(recent_packets),
            "protocol_distribution": dict(self.protocol_stats),
            "connection_count": len(self.connection_summary)
        }
        
        self.logger.info(f"Network metrics: {metrics}")

    def set_filter(self, filter_type: str, value):
        """
        Set monitoring filter
        """
        if filter_type in self.filters:
            self.filters[filter_type] = value
            self.logger.info(f"Set {filter_type} filter to {value}")

    def get_capture_summary(self) -> Dict:
        """
        Get summary of captured traffic
        """
        return {
            "total_packets": len(self.captured_packets),
            "protocol_stats": dict(self.protocol_stats),
            "connection_count": len(self.connection_summary),
            "capture_duration": time.time() - (self.captured_packets[0].timestamp if self.captured_packets else time.time()),
            "filters_active": {k: v for k, v in self.filters.items() if v is not None}
        }

    def export_capture(self, filename: str, format: str = "json"):
        """
        Export captured packets to file
        """
        try:
            if format == "json":
                with open(filename, 'w') as f:
                    capture_data = {
                        "summary": self.get_capture_summary(),
                        "packets": [asdict(p) for p in self.captured_packets]
                    }
                    json.dump(capture_data, f, indent=2, default=str)
                    
            self.logger.info(f"Capture exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")

    def stop_monitoring(self):
        """
        Stop network monitoring
        """
        self.is_monitoring = False
        self.logger.info("Network monitoring stopped")

    def get_connection_details(self, connection_key: str) -> Optional[Dict]:
        """
        Get detailed information about specific connection
        """
        if connection_key in self.connection_summary:
            stats = self.connection_summary[connection_key]
            return {
                "connection": connection_key,
                "statistics": stats,
                "duration": stats['last_seen'] - stats['first_seen'] if stats['first_seen'] else 0,
                "average_packet_size": stats['total_bytes'] / stats['packet_count'] if stats['packet_count'] else 0
            }
        return None 