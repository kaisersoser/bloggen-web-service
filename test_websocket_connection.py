#!/usr/bin/env python3
"""
WebSocket connection test for debugging frontend connection issues.
"""
import asyncio
import websockets
import ssl
import json

async def test_websocket():
    # Create SSL context that doesn't verify certificates (for localhost)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Test WebSocket connection to the backend
    uri = "wss://localhost:5000/ws"
    
    try:
        print(f"Attempting to connect to {uri}...")
        async with websockets.connect(uri, ssl=ssl_context) as websocket:
            print("✅ WebSocket connection successful!")
            
            # Send a ping message
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            print("📤 Sent ping message")
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
