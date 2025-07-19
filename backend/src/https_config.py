"""
HTTPS Server Configuration for Flask Backend

This module provides HTTPS server configuration for local development.
"""

import os
import ssl
import logging
from pathlib import Path


def get_ssl_context():
    """
    Get SSL context for HTTPS server
    
    Returns:
        ssl.SSLContext or None: SSL context if certificates exist
    """
    # Look for certificates in multiple locations
    cert_paths = [
        # Same directory as main.py
        ('localhost.pem', 'localhost-key.pem'),
        # Frontend certs directory
        ('../frontend-nextjs/blog-generator-ui/certs/localhost.pem', 
         '../frontend-nextjs/blog-generator-ui/certs/localhost-key.pem'),
        # Root certs directory
        ('../../certs/localhost.pem', '../../certs/localhost-key.pem'),
    ]
    
    for cert_file, key_file in cert_paths:
        cert_path = Path(__file__).parent / cert_file
        key_path = Path(__file__).parent / key_file
        
        if cert_path.exists() and key_path.exists():
            try:
                # Create SSL context
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                context.load_cert_chain(str(cert_path), str(key_path))
                
                logging.info(f"🔒 HTTPS certificates found: {cert_path}")
                return context
                
            except Exception as e:
                logging.warning(f"Failed to load SSL certificates: {e}")
                continue
    
    # If no certificates found, log instructions
    logging.warning("🚨 No HTTPS certificates found!")
    logging.warning("To enable HTTPS in development:")
    logging.warning("1. Run: cd ../frontend-nextjs/blog-generator-ui")
    logging.warning("2. Run: ./setup-local-https.sh")
    logging.warning("3. Or manually set up mkcert certificates")
    
    return None


def should_use_https():
    """
    Determine if HTTPS should be used based on environment
    
    Returns:
        bool: True if HTTPS should be used
    """
    # Always use HTTPS if certificates are available
    return get_ssl_context() is not None


def get_server_config():
    """
    Get server configuration for Flask-SocketIO
    
    Returns:
        dict: Server configuration
    """
    ssl_context = get_ssl_context()
    
    config = {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': True
    }
    
    if ssl_context:
        config['ssl_context'] = ssl_context
        logging.info("🔒 Starting server with HTTPS")
    else:
        logging.warning("⚠️  Starting server with HTTP (certificates not found)")
    
    return config
