import WebRTCHandler from './webrtc.js';

class SessionHandler {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.socket = io();
        this.webrtc = null;
        this.messageContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('message-input');
        this.videoContainer = document.getElementById('video-container');
        
        this.initializeUI();
        this.initializeWebRTC();
        this.setupEventListeners();
    }

    initializeUI() {
        // Create video elements
        this.videoContainer.innerHTML = `
            <div class="video-grid">
                <div class="video-wrapper remote">
                    <video id="remoteVideo" autoplay playsinline></video>
                    <div class="participant-info">
                        <span id="remote-participant-name">Waiting for participant...</span>
                    </div>
                    <div class="connection-status">
                        <span class="status-indicator connecting"></span>
                        <span>Connecting...</span>
                    </div>
                </div>
                <div class="video-wrapper local">
                    <video id="localVideo" autoplay playsinline muted></video>
                    <div class="participant-info">
                        <span>You</span>
                    </div>
                </div>
            </div>
            <div class="video-controls-bar" style="opacity: 0;">
                <button id="toggleVideo" class="control-btn" title="Toggle Video">
                    <i class="fas fa-video"></i>
                </button>
                <button id="toggleAudio" class="control-btn" title="Toggle Audio">
                    <i class="fas fa-microphone"></i>
                </button>
                <button id="toggleScreen" class="control-btn" title="Share Screen">
                    <i class="fas fa-desktop"></i>
                </button>
                <button id="endCall" class="control-btn" style="background-color: var(--bs-danger);" title="End Call">
                    <i class="fas fa-phone-slash"></i>
                </button>
            </div>
        `;

        // Initialize tooltips if Bootstrap is available
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    async initializeWebRTC() {
        try {
            this.webrtc = new WebRTCHandler(this.socket, this.sessionId);
            await this.webrtc.initializeConnection();
            
            // Update connection status
            if (typeof window.updateConnectionStatus === 'function') {
                window.updateConnectionStatus('connecting');
            }
            
            await this.webrtc.startLocalStream();
            
            // Set the remote participant name
            const remoteParticipantName = document.getElementById('remote-participant-name');
            if (remoteParticipantName) {
                const isCurrentUserMentor = document.querySelector('[data-role="mentor"]') !== null;
                remoteParticipantName.textContent = isCurrentUserMentor ? 'Mentee' : 'Mentor';
            }
            
            await this.webrtc.createOffer();
        } catch (error) {
            console.error('Failed to initialize WebRTC:', error);
            this.addSystemMessage('Failed to initialize video call. Please check your camera and microphone permissions.');
            
            // Update connection status
            if (typeof window.updateConnectionStatus === 'function') {
                window.updateConnectionStatus('disconnected');
            }
        }
    }

    setupEventListeners() {
        // Socket event listeners
        this.socket.on('connect', () => {
            console.log('Socket connected');
            this.socket.emit('join_session', { 
                session_id: this.sessionId
            });
        });

        this.socket.on('user_joined', (data) => {
            console.log('User joined:', data);
            this.addSystemMessage(`${data.username} joined the session`);
            
            // Update connection status
            if (typeof window.updateConnectionStatus === 'function') {
                window.updateConnectionStatus('connected');
            }
            
            // Update connection status UI
            const connectionStatus = document.querySelector('.connection-status');
            if (connectionStatus) {
                connectionStatus.innerHTML = `
                    <span class="status-indicator"></span>
                    <span>Connected</span>
                `;
            }
        });

        this.socket.on('user_left', (data) => {
            this.addSystemMessage(`${data.username} left the session`);
            
            // Update connection status
            if (typeof window.updateConnectionStatus === 'function') {
                window.updateConnectionStatus('disconnected');
            }
            
            // Update connection status UI
            const connectionStatus = document.querySelector('.connection-status');
            if (connectionStatus) {
                connectionStatus.innerHTML = `
                    <span class="status-indicator disconnected"></span>
                    <span>Disconnected</span>
                `;
            }
        });

        this.socket.on('new_message', (data) => {
            this.addMessage(data.username, data.message, data.timestamp);
        });

        // UI event listeners
        document.getElementById('toggleVideo').addEventListener('click', () => this.toggleVideo());
        document.getElementById('toggleAudio').addEventListener('click', () => this.toggleAudio());
        document.getElementById('toggleScreen').addEventListener('click', () => this.toggleScreenShare());
        document.getElementById('endCall').addEventListener('click', () => this.endCall());

        // Message input
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
        
        // Connection state change
        this.socket.on('connect_error', () => {
            console.log('Socket connection error');
            
            // Update connection status
            if (typeof window.updateConnectionStatus === 'function') {
                window.updateConnectionStatus('disconnected');
            }
        });
        
        this.socket.on('reconnect', () => {
            console.log('Socket reconnected');
            this.socket.emit('join_session', { session_id: this.sessionId });
            
            // Update connection status
            if (typeof window.updateConnectionStatus === 'function') {
                window.updateConnectionStatus('connecting');
            }
        });
    }

    addSystemMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message system';
        messageElement.textContent = message;
        this.messageContainer.appendChild(messageElement);
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    addMessage(username, message, timestamp) {
        const isCurrentUser = username === '{{ current_user.username }}';
        const messageElement = document.createElement('div');
        messageElement.className = `message ${isCurrentUser ? 'sent' : 'received'}`;
        
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="username">${username}</span>
                <span class="timestamp">${timestamp}</span>
            </div>
            <div class="message-content">${message}</div>
        `;
        
        this.messageContainer.appendChild(messageElement);
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (message) {
            this.socket.emit('session_message', {
                session_id: this.sessionId,
                message: message
            });
            this.messageInput.value = '';
            
            // Reset textarea height
            this.messageInput.style.height = 'auto';
        }
    }

    async toggleVideo() {
        try {
            const videoTrack = this.webrtc.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = !videoTrack.enabled;
                const toggleBtn = document.getElementById('toggleVideo');
                
                if (!videoTrack.enabled) {
                    toggleBtn.innerHTML = '<i class="fas fa-video-slash"></i>';
                    toggleBtn.classList.add('active');
                } else {
                    toggleBtn.innerHTML = '<i class="fas fa-video"></i>';
                    toggleBtn.classList.remove('active');
                }
            }
        } catch (error) {
            console.error('Error toggling video:', error);
        }
    }

    async toggleAudio() {
        try {
            const audioTrack = this.webrtc.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                const toggleBtn = document.getElementById('toggleAudio');
                
                if (!audioTrack.enabled) {
                    toggleBtn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
                    toggleBtn.classList.add('active');
                } else {
                    toggleBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                    toggleBtn.classList.remove('active');
                }
            }
        } catch (error) {
            console.error('Error toggling audio:', error);
        }
    }

    async toggleScreenShare() {
        try {
            const toggleBtn = document.getElementById('toggleScreen');
            
            if (this.webrtc.isScreenSharing) {
                await this.webrtc.stopScreenShare();
                toggleBtn.innerHTML = '<i class="fas fa-desktop"></i>';
                toggleBtn.classList.remove('active');
            } else {
                const success = await this.webrtc.startScreenShare();
                if (success) {
                    toggleBtn.innerHTML = '<i class="fas fa-stop"></i>';
                    toggleBtn.classList.add('active');
                }
            }
        } catch (error) {
            console.error('Error toggling screen share:', error);
        }
    }
    
    endCall() {
        // Confirm before ending the call
        if (confirm('Are you sure you want to end this call?')) {
            // Redirect to the session detail page or dashboard
            window.location.href = `/sessions/session_detail/${this.sessionId}`;
        }
    }

    cleanup() {
        this.socket.emit('leave_session', { session_id: this.sessionId });
        if (this.webrtc) {
            this.webrtc.cleanup();
        }
        this.socket.disconnect();
    }
}

// Initialize session when the page loads
window.addEventListener('load', () => {
    const sessionId = document.getElementById('session-id').value;
    window.sessionHandler = new SessionHandler(sessionId);
});
