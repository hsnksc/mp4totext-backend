"""
WebSocket manager for real-time progress updates
"""

import logging
from typing import Dict, Set, Optional
import socketio
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    WebSocket manager using Socket.IO
    Manages real-time connections and broadcasts progress updates
    """
    
    def __init__(self):
        # Create Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',  # Configure for production
            logger=False,
            engineio_logger=False
        )
        
        # Track connections by user_id
        self.user_connections: Dict[int, Set[str]] = {}
        
        # Setup event handlers
        self.setup_handlers()
        
        logger.info("✅ WebSocket manager initialized")
    
    def setup_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection"""
            logger.info(f"🔌 WebSocket client connected: {sid}")
            
            # Get user_id from auth
            user_id = auth.get('user_id') if auth else None
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(sid)
                logger.info(f"👤 User {user_id} connected via {sid}")
            
            await self.sio.emit('connected', {'message': 'Connected to MP4toText'}, room=sid)
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            logger.info(f"🔌 WebSocket client disconnected: {sid}")
            
            # Remove from user connections
            for user_id, sids in self.user_connections.items():
                if sid in sids:
                    sids.remove(sid)
                    logger.info(f"👤 User {user_id} disconnected: {sid}")
                    break
        
        @self.sio.event
        async def subscribe(sid, data):
            """Subscribe to transcription updates"""
            transcription_id = data.get('transcription_id')
            if transcription_id:
                room = f"transcription_{transcription_id}"
                await self.sio.enter_room(sid, room)
                logger.info(f"📡 Client {sid} subscribed to transcription {transcription_id}")
                await self.sio.emit('subscribed', {'transcription_id': transcription_id}, room=sid)
        
        @self.sio.event
        async def unsubscribe(sid, data):
            """Unsubscribe from transcription updates"""
            transcription_id = data.get('transcription_id')
            if transcription_id:
                room = f"transcription_{transcription_id}"
                await self.sio.leave_room(sid, room)
                logger.info(f"📡 Client {sid} unsubscribed from transcription {transcription_id}")
    
    async def emit_progress(
        self,
        transcription_id: int,
        progress: int,
        status: str,
        message: Optional[str] = None
    ):
        """
        Emit progress update to all subscribers of a transcription
        
        Args:
            transcription_id: ID of transcription
            progress: Progress percentage (0-100)
            status: Status message
            message: Optional additional message
        """
        room = f"transcription_{transcription_id}"
        
        data = {
            'transcription_id': transcription_id,
            'progress': progress,
            'status': status,
            'message': message
        }
        
        await self.sio.emit('progress', data, room=room)
        logger.debug(f"📡 Progress update sent: {transcription_id} - {progress}%")
    
    async def emit_completed(
        self,
        transcription_id: int,
        result: Dict
    ):
        """
        Emit completion notification
        
        Args:
            transcription_id: ID of transcription
            result: Result data
        """
        room = f"transcription_{transcription_id}"
        
        data = {
            'transcription_id': transcription_id,
            'status': 'completed',
            'result': result
        }
        
        await self.sio.emit('completed', data, room=room)
        logger.info(f"✅ Completion notification sent: {transcription_id}")
    
    async def emit_error(
        self,
        transcription_id: int,
        error: str
    ):
        """
        Emit error notification
        
        Args:
            transcription_id: ID of transcription
            error: Error message
        """
        room = f"transcription_{transcription_id}"
        
        data = {
            'transcription_id': transcription_id,
            'status': 'failed',
            'error': error
        }
        
        await self.sio.emit('error', data, room=room)
        logger.error(f"❌ Error notification sent: {transcription_id}")
    
    async def emit_to_user(
        self,
        user_id: int,
        event: str,
        data: Dict
    ):
        """
        Emit event to all connections of a specific user
        
        Args:
            user_id: User ID
            event: Event name
            data: Event data
        """
        if user_id in self.user_connections:
            for sid in self.user_connections[user_id]:
                await self.sio.emit(event, data, room=sid)
            logger.debug(f"📡 Event '{event}' sent to user {user_id}")
    
    def get_asgi_app(self):
        """Get ASGI app for mounting"""
        return socketio.ASGIApp(self.sio)


# Singleton instance
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get WebSocket manager singleton"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def setup_websocket(app: FastAPI):
    """
    Setup WebSocket with FastAPI app
    
    Args:
        app: FastAPI application instance
    """
    ws_manager = get_ws_manager()
    
    # Mount Socket.IO app
    app.mount("/ws", ws_manager.get_asgi_app())
    
    logger.info("✅ WebSocket mounted at /ws")
