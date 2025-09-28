#!/usr/bin/env python3
"""
SESSION AWARE ORCHESTRATION SYSTEM
Real-time monitoring and cross-session coordination for the Billionaire Consciousness Empire
"""

import asyncio
import json
import websockets
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class Session:
    session_id: str
    user_id: str
    status: str
    current_task: str
    progress: float
    last_activity: datetime
    resources_used: Dict[str, Any]

class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, Session] = {}
        self.session_lock = threading.Lock()
        
    def register_session(self, session_id: str, user_id: str) -> bool:
        """Register a new session"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = Session(
                    session_id=session_id,
                    user_id=user_id,
                    status='active',
                    current_task='initializing',
                    progress=0.0,
                    last_activity=datetime.now(),
                    resources_used={}
                )
                print(f"✅ Registered session: {session_id}")
                return True
            return False
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session information"""
        with self.session_lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.last_activity = datetime.now()
                return True
            return False
    
    def get_session_status(self, session_id: str) -> Optional[Session]:
        """Get session status"""
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Session]:
        """Get all active sessions"""
        with self.session_lock:
            return list(self.active_sessions.values())
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive sessions"""
        with self.session_lock:
            current_time = datetime.now()
            inactive_sessions = []
            
            for session_id, session in self.active_sessions.items():
                time_diff = (current_time - session.last_activity).total_seconds() / 60
                if time_diff > timeout_minutes:
                    inactive_sessions.append(session_id)
            
            for session_id in inactive_sessions:
                del self.active_sessions[session_id]
                print(f"🧹 Cleaned up inactive session: {session_id}")

class SessionWebSocketServer:
    def __init__(self, session_manager: SessionManager, port: int = 8765):
        self.session_manager = session_manager
        self.port = port
        self.clients = set()
        
    async def register_client(self, websocket, path):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        print(f"🔗 New client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"🔌 Client disconnected: {websocket.remote_address}")
    
    async def handle_message(self, websocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            command = data.get('command')
            
            if command == 'register_session':
                session_id = data.get('session_id')
                user_id = data.get('user_id')
                success = self.session_manager.register_session(session_id, user_id)
                await websocket.send(json.dumps({
                    'type': 'registration_response',
                    'success': success,
                    'session_id': session_id
                }))
                
            elif command == 'update_session':
                session_id = data.get('session_id')
                updates = data.get('updates', {})
                success = self.session_manager.update_session(session_id, **updates)
                await websocket.send(json.dumps({
                    'type': 'update_response',
                    'success': success,
                    'session_id': session_id
                }))
                
            elif command == 'get_sessions':
                sessions = self.session_manager.get_all_sessions()
                session_data = []
                for session in sessions:
                    session_data.append({
                        'session_id': session.session_id,
                        'user_id': session.user_id,
                        'status': session.status,
                        'current_task': session.current_task,
                        'progress': session.progress,
                        'last_activity': session.last_activity.isoformat(),
                        'resources_used': session.resources_used
                    })
                
                await websocket.send(json.dumps({
                    'type': 'sessions_data',
                    'sessions': session_data
                }))
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def broadcast_update(self, message: Dict[str, Any]):
        """Broadcast update to all connected clients"""
        if self.clients:
            message_str = json.dumps(message)
            disconnected_clients = set()
            
            for client in self.clients:
                try:
                    await client.send(message_str)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            self.clients -= disconnected_clients
    
    async def start_server(self):
        """Start the WebSocket server"""
        print(f"🚀 Starting Session WebSocket Server on port {self.port}")
        
        async def cleanup_sessions():
            """Periodic cleanup of inactive sessions"""
            while True:
                await asyncio.sleep(300)  # 5 minutes
                self.session_manager.cleanup_inactive_sessions()
                
                # Broadcast session cleanup
                await self.broadcast_update({
                    'type': 'sessions_cleaned',
                    'timestamp': datetime.now().isoformat()
                })
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(cleanup_sessions())
        
        # Start WebSocket server
        async with websockets.serve(self.register_client, "localhost", self.port):
            print(f"✅ Session WebSocket Server running on ws://localhost:{self.port}")
            await asyncio.Future()  # Run forever

class SessionDatabase:
    def __init__(self, db_path: str = "session_data.db"):
        self.db_path = db_path
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize session database"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    status TEXT,
                    current_task TEXT,
                    progress REAL,
                    created_at TIMESTAMP,
                    last_activity TIMESTAMP,
                    resources_used TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Session database initialized")
        except ImportError:
            print("⚠️ SQLite not available, using in-memory storage only")
    
    def save_session(self, session: Session):
        """Save session to database"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sessions 
                (session_id, user_id, status, current_task, progress, created_at, last_activity, resources_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.session_id,
                session.user_id,
                session.status,
                session.current_task,
                session.progress,
                datetime.now().isoformat(),
                session.last_activity.isoformat(),
                json.dumps(session.resources_used)
            ))
            
            conn.commit()
            conn.close()
        except ImportError:
            pass  # SQLite not available
    
    def load_sessions(self) -> List[Session]:
        """Load sessions from database"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM sessions')
            rows = cursor.fetchall()
            conn.close()
            
            sessions = []
            for row in rows:
                session = Session(
                    session_id=row[0],
                    user_id=row[1],
                    status=row[2],
                    current_task=row[3],
                    progress=row[4],
                    last_activity=datetime.fromisoformat(row[6]),
                    resources_used=json.loads(row[7]) if row[7] else {}
                )
                sessions.append(session)
            
            return sessions
        except ImportError:
            return []  # SQLite not available

class SessionOrchestrator:
    def __init__(self):
        self.session_manager = SessionManager()
        self.websocket_server = SessionWebSocketServer(self.session_manager)
        self.database = SessionDatabase()
        
    def start_orchestration(self, port: int = 8765):
        """Start the session-aware orchestration system"""
        print("🧠 Starting Session-Aware Orchestration System...")
        
        # Load existing sessions from database
        existing_sessions = self.database.load_sessions()
        for session in existing_sessions:
            self.session_manager.active_sessions[session.session_id] = session
            print(f"📂 Loaded existing session: {session.session_id}")
        
        # Start WebSocket server
        try:
            asyncio.run(self.websocket_server.start_server())
        except KeyboardInterrupt:
            print("\n🛑 Shutting down Session-Aware Orchestration System")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the orchestration system"""
        print("💾 Saving session data...")
        for session in self.session_manager.get_all_sessions():
            self.database.save_session(session)
        print("✅ Session data saved")

def run_interactive():
    """Run interactive session orchestration"""
    orchestrator = SessionOrchestrator()
    
    print("\n🧠 SESSION-AWARE ORCHESTRATION SYSTEM")
    print("=" * 50)
    print("Commands:")
    print("1. Start WebSocket Server")
    print("2. View Active Sessions")
    print("3. Test Session Registration")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            port = input("Enter port (default 8765): ").strip()
            port = int(port) if port else 8765
            
            orchestrator.websocket_server.port = port
            orchestrator.start_orchestration(port)
            
        elif choice == '2':
            sessions = orchestrator.session_manager.get_all_sessions()
            print(f"\n📊 Active Sessions: {len(sessions)}")
            for session in sessions:
                print(f"  - {session.session_id}: {session.status} ({session.current_task})")
                
        elif choice == '3':
            session_id = f"test_{int(time.time())}"
            user_id = "test_user"
            success = orchestrator.session_manager.register_session(session_id, user_id)
            print(f"✅ Test session registered: {success}")
            
        elif choice == '4':
            orchestrator.shutdown()
            break
            
        else:
            print("❌ Invalid choice")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        run_interactive()
    else:
        orchestrator = SessionOrchestrator()
        orchestrator.start_orchestration()

if __name__ == "__main__":
    import sys
    main()
