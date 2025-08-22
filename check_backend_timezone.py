#!/usr/bin/env python3

import os
import sys
import requests
import json
from datetime import datetime
import time

def check_backend_timezone():
    """Check what timezone the backend is using for JWT validation"""
    
    print("🕐 Backend Timezone Investigation")
    print("=" * 50)
    
    # First, let's see what the backend reports for current time
    try:
        response = requests.get("https://localhost:5000/health", verify=False)
        if response.status_code == 200:
            health_data = response.json()
            backend_timestamp = health_data.get('timestamp')
            print(f"🏥 Backend health timestamp: {backend_timestamp}")
            
            # Parse the backend timestamp
            if backend_timestamp:
                # Remove microseconds and parse
                backend_time_clean = backend_timestamp.split('.')[0]
                backend_dt = datetime.fromisoformat(backend_time_clean)
                print(f"📅 Backend reports time as: {backend_dt}")
                print(f"📅 This appears to be: {'UTC' if 'T' in backend_timestamp else 'Local'} time")
                
    except Exception as e:
        print(f"❌ Failed to get backend health: {e}")
    
    # Compare with our local times
    print(f"\n🌍 Local Time Comparison:")
    print(f"   System local time: {datetime.now()}")
    print(f"   System UTC time:   {datetime.utcnow()}")
    print(f"   Timezone offset:   {time.timezone} seconds ({time.timezone/3600} hours)")
    print(f"   Current TZ name:   {time.tzname}")
    
    # Check environment variables that might affect timezone
    print(f"\n🔧 Environment Variables:")
    for var in ['TZ', 'TIMEZONE', 'LC_TIME', 'LANG']:
        value = os.getenv(var, 'Not set')
        print(f"   {var}: {value}")

if __name__ == "__main__":
    check_backend_timezone()
