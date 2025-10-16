#!/usr/bin/env python3
"""
Railway-specific database connection diagnostics.

This script helps diagnose why Railway cannot connect to Supabase
even though the connection works locally.
"""

import asyncio
import os
import socket
import sys

try:
    import asyncpg
except ImportError:
    print("❌ asyncpg not installed")
    sys.exit(1)


async def test_railway_connectivity():
    """Test connection with Railway-specific diagnostics."""
    
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    print("=" * 70)
    print("RAILWAY DATABASE CONNECTION DIAGNOSTICS")
    print("=" * 70)
    print()
    
    # Extract hostname from URL
    host = None
    port = None
    if "@" in database_url and ":" in database_url:
        try:
            after_at = database_url.split("@")[1]
            host_port = after_at.split("/")[0]
            if ":" in host_port:
                host, port_str = host_port.rsplit(":", 1)
                port = int(port_str)
            else:
                host = host_port
                port = 5432
        except:
            pass
    
    if not host:
        print("❌ Could not extract hostname from DATABASE_URL")
        return False
    
    print(f"🌐 Target: {host}:{port}")
    print()
    
    # DNS Resolution Test
    print("1️⃣ DNS Resolution Test")
    print("-" * 70)
    try:
        addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        print(f"✅ DNS resolution successful: {len(addrs)} address(es) found")
        for addr in addrs:
            family = "IPv6" if addr[0] == socket.AF_INET6 else "IPv4"
            ip = addr[4][0]
            print(f"   {family}: {ip}")
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    print()
    
    # TCP Connection Test
    print("2️⃣ TCP Connection Test")
    print("-" * 70)
    print(f"Attempting TCP connection to {host}:{port}...")
    
    # Try IPv4 first
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print(f"✅ IPv4 TCP connection successful")
        sock.close()
    except Exception as e:
        print(f"❌ IPv4 TCP connection failed: {e}")
        
        # Try IPv6 if IPv4 fails
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(10)
            # Extract IPv6 address from getaddrinfo results
            ipv6_addrs = [a[4][0] for a in addrs if a[0] == socket.AF_INET6]
            if ipv6_addrs:
                sock.connect((ipv6_addrs[0], port))
                print(f"✅ IPv6 TCP connection successful")
                sock.close()
            else:
                print(f"⚠️ No IPv6 address available to test")
        except Exception as e2:
            print(f"❌ IPv6 TCP connection also failed: {e2}")
            print()
            print("🚨 NETWORK ISSUE DETECTED:")
            print("   Cannot establish TCP connection to Supabase pooler")
            print("   This is why Railway deployment fails with 'Network is unreachable'")
            print()
            print("   Possible causes:")
            print("   - Railway region cannot route to this Supabase region")
            print("   - Firewall or network policy blocking connection")
            print("   - Supabase pooler experiencing issues")
            return False
    print()
    
    # PostgreSQL Connection Test
    print("3️⃣ PostgreSQL Connection Test")
    print("-" * 70)
    try:
        print("Creating connection pool...")
        pool = await asyncio.wait_for(
            asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=1,
                command_timeout=10,
                timeout=10,
            ),
            timeout=15
        )
        print("✅ Connection pool created")
        
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT version()")
            print(f"✅ Query successful")
            print(f"   PostgreSQL: {result[:60]}...")
        
        await pool.close()
        print()
        print("=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("Your DATABASE_URL is working correctly!")
        print("If Railway still fails, the issue is Railway-specific network routing.")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print()
        print("🔍 Debug Info:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        return False


def main():
    success = asyncio.run(test_railway_connectivity())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
