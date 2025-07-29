#!/usr/bin/env python3
"""
Example Usage of Industrial Marking System
Demonstrates practical implementation for Matthews-style marking operations
"""

import asyncio
import time
import json
from datetime import datetime

# Import the main system components
from main import IndustrialMarkingSystem
from network_services.tcp_server import NetworkMessage

async def run_marking_example():
    """
    Demonstrate the complete marking workflow
    """
    print("=" * 60)
    print("Industrial Marking System Example")
    print("Demonstrates Matthews-style marking operations")
    print("=" * 60)
    
    # Example product data for different industries
    automotive_product = {
        "product_type": "automotive_component",
        "part_number": "MT-123456-AB", 
        "serial_number": "AUTO2024001",
        "supplier_code": "MATT",
        "production_date": "20240115",
        "shift_code": "A",
        "plant_code": "CRB01"
    }
    
    medical_device = {
        "product_type": "medical_device",
        "device_identifier": "01234567890123",
        "serial_number": "MDI001",
        "lot_number": "LOT240115",
        "expiry_date": "2026-01-15",
        "udi_code": "01234567890123172601151021240115"
    }
    
    food_packaging = {
        "product_type": "food_packaging",
        "serial_number": "FP0001",
        "production_date": "15/01/24",
        "expiry_date": "15/07/24",
        "shift_code": "B",
        "line_number": "3"
    }
    
    products = [
        ("Automotive Component", automotive_product),
        ("Medical Device", medical_device),
        ("Food Packaging", food_packaging)
    ]
    
    for product_name, product_data in products:
        print(f"\n--- Processing {product_name} ---")
        
        # Simulate marking request
        marking_request = NetworkMessage(
            message_id=f"req_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            message_type="marking_request",
            payload={"product_data": product_data}
        )
        
        print(f"Product Data: {json.dumps(product_data, indent=2)}")
        print(f"Marking Status: SIMULATED SUCCESS")
        print(f"Compliance: Industry-specific validation applied")
        
        # Simulate processing time
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("Example completed - System ready for production use")
    print("=" * 60)

def demonstrate_lua_integration():
    """
    Show how the Lua plugin system would work
    """
    print("\n--- Lua Plugin Integration Example ---")
    
    # This demonstrates the Lua integration concept
    lua_plugin_config = {
        "automotive": {
            "validation_rules": ["part_number", "serial_number", "supplier_code"],
            "marking_template": "P/N: {PART_NUMBER}\nS/N: {SERIAL_NUMBER}\nSUP: {SUPPLIER_CODE}",
            "compliance_standards": ["IATF16949", "ISO9001"]
        }
    }
    
    print("Lua Plugin Configuration:")
    print(json.dumps(lua_plugin_config, indent=2))
    
    print("\nLua plugins provide:")
    print("- Industry-specific validation logic")
    print("- Custom marking templates")
    print("- Regulatory compliance checking")
    print("- Real-time performance optimization")

def show_hardware_integration():
    """
    Demonstrate hardware integration capabilities
    """
    print("\n--- Hardware Integration Example ---")
    
    hardware_config = {
        "plc_interface": {
            "protocol": "modbus_tcp",
            "ip_address": "192.168.1.100",
            "port": 502,
            "discrete_inputs": {
                "product_present": 0,
                "system_ready": 1,
                "emergency_stop": 2
            },
            "discrete_outputs": {
                "marking_start": 0,
                "status_led": 1,
                "error_indicator": 2
            }
        }
    }
    
    print("Hardware Configuration:")
    print(json.dumps(hardware_config, indent=2))
    
    print("\nHardware capabilities:")
    print("- Modbus TCP/RTU communication")
    print("- Discrete I/O control")
    print("- Real-time sensor monitoring")
    print("- Production line integration")

def main():
    """
    Main example runner
    """
    try:
        print("Starting Industrial Marking System Example...")
        
        # Show different aspects of the system
        demonstrate_lua_integration()
        show_hardware_integration()
        
        # Run the async marking example
        asyncio.run(run_marking_example())
        
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"Example error: {e}")

if __name__ == "__main__":
    main() 