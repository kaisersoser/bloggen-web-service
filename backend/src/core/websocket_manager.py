"""
WebSocket Connection Manager

Handles WebSocket connections for real-time task updates, replacing SSE
with more reliable bidirectional communication.
"""

import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class WebSocketMessage(BaseModel):
    type: str
    task_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()
        super().__init__(**data)

class ConnectionInfo(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    websocket: WebSocket
    user_id: str
    task_ids: Set[str]
    connected_at: datetime
    last_ping: Optional[datetime] = None

class WebSocketManager:
    """
    Manages WebSocket connections for real-time task updates.
    
    Features:
    - Multiple connections per user
    - Task-specific subscriptions
    - Automatic connection cleanup
    - Authentication integration
    - Heartbeat/ping support
    """
    
    def __init__(self):
        # Active connections: connection_id -> ConnectionInfo
        self.connections: Dict[str, ConnectionInfo] = {}
        
        # Task subscriptions: task_id -> set of connection_ids
        self.task_subscriptions: Dict[str, Set[str]] = {}
        
        # User connections: user_id -> set of connection_ids
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Redis manager for pub/sub (set by main app)
        self._redis_manager = None
        
        # Redis subscribers per user
        self._redis_subscribers: Dict[str, Any] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    def set_redis_manager(self, redis_manager):
        """Set the Redis manager for pub/sub integration."""
        self._redis_manager = redis_manager
    
    async def _handle_redis_update(self, task_update):
        """Handle Redis task update by broadcasting to WebSocket connections."""
        try:
            # Convert Redis message to WebSocket message
            websocket_message = WebSocketMessage(
                type="task_update",
                task_id=task_update.task_id,
                data={
                    'status': task_update.status,
                    'step': task_update.phase,
                    'progress': task_update.progress,
                    'details': task_update.details,
                    'timestamp': task_update.timestamp
                }
            )
            
            # Broadcast to all connections subscribed to this task
            await self.broadcast_to_task(task_update.task_id, websocket_message)
            
        except Exception as e:
            logger.error(f"❌ Error handling Redis update: {e}")
    
    async def _setup_redis_subscription(self, user_id: str):
        """Set up Redis subscription for a user."""
        if not self._redis_manager or user_id in self._redis_subscribers:
            return
            
        try:
            # Create Redis subscriber for this user
            subscriber = await self._redis_manager.create_subscriber(
                subscriber_id=f"websocket_user_{user_id}",
                callback=self._handle_redis_update
            )
            
            # Subscribe to user updates
            await subscriber.subscribe_to_user(user_id)
            
            self._redis_subscribers[user_id] = subscriber
            logger.info(f"📡 Set up Redis subscription for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to set up Redis subscription for user {user_id}: {e}")
    
    async def _cleanup_redis_subscription(self, user_id: str):
        """Clean up Redis subscription when user has no more connections."""
        if user_id not in self._redis_subscribers or not self._redis_manager:
            return
            
        try:
            subscriber = self._redis_subscribers[user_id]
            await self._redis_manager.remove_subscriber(f"websocket_user_{user_id}")
            del self._redis_subscribers[user_id]
            
            logger.info(f"📡 Cleaned up Redis subscription for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup Redis subscription for user {user_id}: {e}")
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str) -> bool:
        """
        Accept a new WebSocket connection and register it.
        
        Args:
            websocket: The WebSocket connection
            connection_id: Unique identifier for this connection
            user_id: ID of the authenticated user
            
        Returns:
            bool: True if connection was successful
        """
        try:
            await websocket.accept()
            
            async with self._lock:
                # Store connection info
                self.connections[connection_id] = ConnectionInfo(
                    websocket=websocket,
                    user_id=user_id,
                    task_ids=set(),
                    connected_at=datetime.utcnow()
                )
                
                # Track user connections
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
                
                # Set up Redis subscription for this user if first connection
                if len(self.user_connections[user_id]) == 1:
                    await self._setup_redis_subscription(user_id)
            
            # Send welcome message
            await self.send_to_connection(connection_id, WebSocketMessage(
                type="connected",
                data={"message": "WebSocket connected successfully"}
            ))
            
            logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection {connection_id}: {e}")
            return False
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect and clean up a WebSocket connection.
        
        Args:
            connection_id: The connection to disconnect
        """
        async with self._lock:
            connection_info = self.connections.get(connection_id)
            if not connection_info:
                return
            
            user_id = connection_info.user_id
            
            # Remove from task subscriptions
            for task_id in connection_info.task_ids.copy():
                await self._unsubscribe_from_task_unsafe(connection_id, task_id)
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    # Clean up Redis subscription when user has no more connections
                    await self._cleanup_redis_subscription(user_id)
                    del self.user_connections[user_id]
            
            # Remove connection
            del self.connections[connection_id]
            
            logger.info(f"WebSocket connection disconnected: {connection_id} for user {user_id}")
    
    async def subscribe_to_task(self, connection_id: str, task_id: str) -> bool:
        """
        Subscribe a connection to receive updates for a specific task.
        
        Args:
            connection_id: The connection to subscribe
            task_id: The task to subscribe to
            
        Returns:
            bool: True if subscription was successful
        """
        async with self._lock:
            connection_info = self.connections.get(connection_id)
            if not connection_info:
                return False
            
            # Add to connection's task list
            connection_info.task_ids.add(task_id)
            
            # Add to task subscriptions
            if task_id not in self.task_subscriptions:
                self.task_subscriptions[task_id] = set()
            self.task_subscriptions[task_id].add(connection_id)
            
            logger.debug(f"Connection {connection_id} subscribed to task {task_id}")
            return True
    
    async def unsubscribe_from_task(self, connection_id: str, task_id: str):
        """
        Unsubscribe a connection from task updates.
        
        Args:
            connection_id: The connection to unsubscribe
            task_id: The task to unsubscribe from
        """
        async with self._lock:
            await self._unsubscribe_from_task_unsafe(connection_id, task_id)
    
    async def _unsubscribe_from_task_unsafe(self, connection_id: str, task_id: str):
        """Internal unsubscribe method (assumes lock is held)."""
        connection_info = self.connections.get(connection_id)
        if connection_info:
            connection_info.task_ids.discard(task_id)
        
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: Target connection
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        connection_info = self.connections.get(connection_id)
        if not connection_info:
            return False
        
        try:
            await connection_info.websocket.send_text(message.model_dump_json())
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to connection {connection_id}: {e}")
            # Connection is probably dead, remove it
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_task(self, task_id: str, message: WebSocketMessage):
        """
        Broadcast a message to all connections subscribed to a task.
        
        Args:
            task_id: The task to broadcast to
            message: Message to broadcast
        """
        # Ensure task_id is set in the message
        message.task_id = task_id
        
        connection_ids = self.task_subscriptions.get(task_id, set()).copy()
        
        if not connection_ids:
            logger.debug(f"No connections subscribed to task {task_id}")
            return
        
        # Send to all subscribed connections
        failed_connections = []
        for connection_id in connection_ids:
            success = await self.send_to_connection(connection_id, message)
            if not success:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        if failed_connections:
            async with self._lock:
                for connection_id in failed_connections:
                    await self._unsubscribe_from_task_unsafe(connection_id, task_id)
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """
        Send a message to all connections for a specific user.
        
        Args:
            user_id: Target user
            message: Message to send
        """
        connection_ids = self.user_connections.get(user_id, set()).copy()
        
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)
    
    async def handle_ping(self, connection_id: str):
        """
        Handle ping from a connection (for heartbeat).
        
        Args:
            connection_id: Connection that sent the ping
        """
        connection_info = self.connections.get(connection_id)
        if connection_info:
            connection_info.last_ping = datetime.utcnow()
            
            # Send pong response
            await self.send_to_connection(connection_id, WebSocketMessage(
                type="pong",
                data={"timestamp": datetime.utcnow().isoformat()}
            ))
    
    async def cleanup_stale_connections(self, max_age_minutes: int = 60):
        """
        Remove connections that haven't been active recently.
        
        Args:
            max_age_minutes: Maximum age for inactive connections
        """
        cutoff_time = datetime.utcnow().timestamp() - (max_age_minutes * 60)
        stale_connections = []
        
        async with self._lock:
            for connection_id, connection_info in self.connections.items():
                last_activity = connection_info.last_ping or connection_info.connected_at
                if last_activity.timestamp() < cutoff_time:
                    stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            await self.disconnect(connection_id)
            logger.info(f"Cleaned up stale connection: {connection_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current connections.
        
        Returns:
            dict: Connection statistics
        """
        return {
            "total_connections": len(self.connections),
            "unique_users": len(self.user_connections),
            "active_tasks": len(self.task_subscriptions),
            "connections_by_user": {
                user_id: len(connection_ids) 
                for user_id, connection_ids in self.user_connections.items()
            }
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()
