import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timezone
import os
from flask import current_app

class FirebaseVideoService:
    def __init__(self):
        if not firebase_admin._apps:
            # Get the base directory path
            basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            # Path to service account file
            service_account_path = os.path.join(basedir, 'firebase-service-account.json')

            try:
                # Try to use the service account file
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': os.environ.get('FIREBASE_DATABASE_URL') or 'https://videocalling-8a1bb-default-rtdb.asia-southeast1.firebasedatabase.app'
                })
                print('Firebase initialized with service account file')
            except Exception as e:
                print(f'Error initializing Firebase: {str(e)}')
                raise
        self.db = db.reference()

    def create_call_room(self, session_id):
        """Create a new video call room or update existing one"""
        try:
            room_ref = self.db.child('video_calls').child(str(session_id))

            # Check if room already exists
            existing_room = room_ref.get()

            if existing_room:
                # Room exists, just update the active status
                room_ref.update({
                    'active': True,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
            else:
                # Create new room
                room_ref.set({
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'active': True,
                    'participants': {},
                    'signals': {}
                })

            return str(session_id)
        except Exception as e:
            print(f"Error creating/updating call room: {str(e)}")
            # Re-raise to let the caller handle it
            raise

    def join_call(self, session_id, user_id, user_data):
        """Add participant to video call"""
        try:
            room_ref = self.db.child('video_calls').child(str(session_id))

            # Make sure the room exists
            room_data = room_ref.get()
            if not room_data:
                # Create the room if it doesn't exist
                self.create_call_room(session_id)

            # Add participant
            room_ref.child('participants').child(str(user_id)).set({
                'joined_at': datetime.now(timezone.utc).isoformat(),
                'last_active': datetime.now(timezone.utc).isoformat(),
                'user_data': user_data
            })

            # Update room status
            room_ref.update({
                'active': True,
                'last_activity': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            print(f"Error joining call: {str(e)}")
            # Re-raise to let the caller handle it
            raise

    def leave_call(self, session_id, user_id):
        """Remove participant from video call"""
        try:
            room_ref = self.db.child('video_calls').child(str(session_id))

            # Check if room exists
            if room_ref.get():
                # Remove participant
                room_ref.child('participants').child(str(user_id)).delete()

                # Update room status
                room_ref.update({
                    'last_activity': datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            print(f"Error leaving call: {str(e)}")
            # Don't re-raise, as this is often called during cleanup

    def send_signal(self, session_id, user_id, signal_data):
        """Send WebRTC signal"""
        try:
            room_ref = self.db.child('video_calls').child(str(session_id))

            # Make sure the room exists
            room_data = room_ref.get()
            if not room_data:
                # Create the room if it doesn't exist
                self.create_call_room(session_id)

            # Send signal
            room_ref.child('signals').push({
                'user_id': str(user_id),
                'data': signal_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            # Update room status
            room_ref.update({
                'last_activity': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            print(f"Error sending signal: {str(e)}")
            # Re-raise to let the caller handle it
            raise

    def end_call(self, session_id):
        """End video call session"""
        try:
            room_ref = self.db.child('video_calls').child(str(session_id))

            # Check if room exists
            if room_ref.get():
                # Update room status
                room_ref.update({
                    'active': False,
                    'ended_at': datetime.now(timezone.utc).isoformat(),
                    'last_activity': datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            print(f"Error ending call: {str(e)}")
            # Don't re-raise, as this is often called during cleanup

    def handle_connection_error(self, session_id, user_id):
        """Handle connection errors and cleanup"""
        try:
            room_ref = self.db.child('video_calls').child(str(session_id))

            # Check if room exists
            if not room_ref.get():
                return

            # Remove user from participants
            room_ref.child('participants').child(str(user_id)).delete()

            # Check if room is empty
            participants = room_ref.child('participants').get()

            if not participants:
                # Close empty room
                room_ref.update({
                    'active': False,
                    'ended_at': datetime.now(timezone.utc).isoformat(),
                    'last_activity': datetime.now(timezone.utc).isoformat(),
                    'status': 'closed_due_to_error'
                })
            else:
                # Update room status
                room_ref.update({
                    'last_activity': datetime.now(timezone.utc).isoformat(),
                    'had_error': True
                })
        except Exception as e:
            # Log error but don't raise
            print(f"Error handling connection error: {str(e)}")
            try:
                if 'current_app' in globals() and hasattr(current_app, 'logger'):
                    current_app.logger.error(f"Error handling connection: {str(e)}")
            except:
                pass  # Fail silently if logger is not available
