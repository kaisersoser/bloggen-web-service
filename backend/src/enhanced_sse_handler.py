"""
Enhanced SSE Endpoint with Redis Pub/Sub Support

This replaces the database polling approach with Redis-based real-time updates.
"""

import asyncio
import json
import logging
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

async def create_enhanced_sse_stream(task_id: str, user, task_manager):
    """
    Create an SSE stream that listens to Redis pub/sub for real-time updates
    instead of polling the database.
    """
    
    async def event_generator():
        last_sent_status = None
        last_sent_step = None
        last_sent_progress = None
        last_sent_hero = None
        sent_initialization = False
        redis_pubsub = None
        
        try:
            # Immediately send connection acknowledgment
            connection_message = {
                "type": "connected",
                "task_id": task_id,
                "message": "SSE connection established",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(connection_message)}\n\n"
            
            # Set up Redis pub/sub if available
            if task_manager._redis_manager and hasattr(task_manager._redis_manager, '_redis_client'):
                try:
                    redis_pubsub = task_manager._redis_manager._redis_client.pubsub()
                    channel = f"task_updates:{task_id}"
                    await redis_pubsub.subscribe(channel)
                    logger.info(f"📡 SSE subscribed to Redis channel: {channel}")
                except Exception as e:
                    logger.warning(f"Redis subscription failed, using database polling: {e}")
                    redis_pubsub = None
            
            # Get and send initial task state
            current_task = await task_manager.get_task(task_id)
            if not current_task:
                error_message = {
                    "type": "error", 
                    "task_id": task_id,
                    "message": "Task not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(error_message)}\n\n"
                return
            
            # Send initial state
            async for update in send_task_update(current_task, last_sent_status, last_sent_step, 
                                               last_sent_progress, last_sent_hero, sent_initialization, task_id):
                yield update
                
            # Choose update method based on Redis availability
            if redis_pubsub:
                logger.info(f"📡 Using Redis pub/sub for task {task_id}")
                async for update in listen_to_redis_updates(redis_pubsub, task_id, task_manager):
                    yield update
            else:
                logger.info(f"📊 Using database polling for task {task_id}")
                async for update in poll_database_updates(task_id, task_manager, last_sent_status, 
                                                        last_sent_step, last_sent_progress, last_sent_hero):
                    yield update
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for task {task_id}: {e}")
            error_message = {
                "type": "error",
                "task_id": task_id,
                "message": f"Stream error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_message)}\n\n"
        finally:
            # Clean up Redis subscription
            if redis_pubsub:
                try:
                    await redis_pubsub.unsubscribe(f"task_updates:{task_id}")
                    await redis_pubsub.close()
                except:
                    pass
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

async def send_task_update(task_data, last_sent_status, last_sent_step, last_sent_progress, 
                          last_sent_hero, sent_initialization, task_id):
    """Helper to format and send task updates via SSE"""
    from core.sse_message_types import (
        create_initializing_message, create_status_message, 
        create_completed_message, create_error_message
    )
    
    status = task_data.get('status', '').lower()
    step = task_data.get('current_step')
    progress = task_data.get('progress', 0)
    hero_url = task_data.get('hero_image_url')
    
    # Send initialization message once when task starts
    if not sent_initialization and status in ['started', 'in_progress']:
        init_message = create_initializing_message(
            task_id=task_id,
            phase="Blog Generation",
            message="Initializing AI blog generation workflow...",
            progress=0.0
        )
        yield f"data: {json.dumps(init_message.to_dict())}\n\n"
    
    # Create appropriate message type based on status
    if status == 'completed':
        final_content = task_data.get('content')
        generation_time = task_data.get('generation_time')
        message = create_completed_message(
            task_id=task_id,
            final_content=final_content,
            generation_time=generation_time
        )
    elif status == 'failed':
        error_details = task_data.get('error', 'Unknown error occurred')
        message = create_error_message(
            task_id=task_id,
            error_msg=error_details,
            recoverable=False
        )
    else:
        # Regular status update
        message = create_status_message(
            task_id=task_id,
            status=status,
            message=task_data.get('message', f"Status: {status}"),
            step=step,
            progress=progress
        )
    
    # Add hero image information if available
    payload = message.to_dict()
    if hero_url:
        payload['hero_image_url'] = hero_url
    
    yield f"data: {json.dumps(payload)}\n\n"

async def listen_to_redis_updates(redis_pubsub, task_id, task_manager):
    """Listen to Redis pub/sub messages for real-time task updates"""
    try:
        keepalive_counter = 0
        timeout_seconds = 300  # 5 minutes max
        start_time = datetime.utcnow()
        
        async for message in redis_pubsub.listen():
            # Check for timeout
            if (datetime.utcnow() - start_time).seconds > timeout_seconds:
                logger.info(f"Redis listening timeout for task {task_id}")
                break
                
            if message['type'] == 'message':
                try:
                    # Parse Redis message
                    redis_data = json.loads(message['data'].decode('utf-8'))
                    logger.info(f"📨 Redis update for {task_id}: {redis_data.get('status', 'unknown')}")
                    
                    # Get current task state from database
                    updated_task = await task_manager.get_task(task_id)
                    if updated_task:
                        async for update in send_task_update(
                            updated_task, None, None, None, None, True, task_id
                        ):
                            yield update
                        
                        # Exit if task is complete
                        if updated_task.get('status', '').lower() in ['completed', 'failed']:
                            break
                            
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid Redis message for {task_id}: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing Redis message for {task_id}: {e}")
            else:
                # Send periodic keepalives
                keepalive_counter += 1
                if keepalive_counter % 100 == 0:  # Every ~20-30 seconds
                    keepalive_message = {
                        "type": "keepalive",
                        "task_id": task_id,
                        "message": "Connection active (Redis mode)",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(keepalive_message)}\n\n"
                    
    except Exception as e:
        logger.error(f"❌ Redis listening error for {task_id}: {e}")

async def poll_database_updates(task_id, task_manager, last_sent_status, 
                               last_sent_step, last_sent_progress, last_sent_hero):
    """Fallback database polling when Redis is unavailable"""
    poll_count = 0
    max_polls = 1500  # ~5 minutes at 0.2s intervals
    
    while poll_count < max_polls:
        poll_count += 1
        
        try:
            current_task = await task_manager.get_task(task_id)
            if not current_task:
                break
            
            status = current_task.get('status', '').lower()
            step = current_task.get('current_step')
            progress = current_task.get('progress', 0)
            hero_url = current_task.get('hero_image_url')
            
            # Check for changes
            has_changes = (
                status != last_sent_status or
                step != last_sent_step or
                progress != last_sent_progress or
                hero_url != last_sent_hero
            )
            
            if has_changes:
                async for update in send_task_update(
                    current_task, last_sent_status, last_sent_step,
                    last_sent_progress, last_sent_hero, True, task_id
                ):
                    yield update
                    
                # Update tracking variables
                last_sent_status = status
                last_sent_step = step
                last_sent_progress = progress
                last_sent_hero = hero_url
            
            # Exit if complete
            if status in ['completed', 'failed']:
                break
            
            # Periodic keepalive
            if poll_count % 50 == 0:  # Every ~10 seconds
                keepalive_message = {
                    "type": "keepalive",
                    "task_id": task_id,
                    "message": "Connection active (polling mode)",
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(keepalive_message)}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Database polling error for {task_id}: {e}")
            
        # Wait before next poll
        await asyncio.sleep(0.2)
        
    # Timeout reached
    timeout_message = {
        "type": "timeout",
        "task_id": task_id,
        "message": "Stream timeout reached - refresh page to reconnect",
        "timestamp": datetime.utcnow().isoformat()
    }
    yield f"data: {json.dumps(timeout_message)}\n\n"
