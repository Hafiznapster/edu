/**
 * WebRTC Handler for EduConnect
 * Manages video calls, screen sharing, and real-time communication
 */

class WebRTCHandler {
    constructor(sessionId, role) {
        this.sessionId = sessionId;
        this.role = role; // 'mentor' or 'mentee'
        this.socket = io();
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.isInitiator = role === 'mentor';
        this.isAudioEnabled = true;
        this.isVideoEnabled = true;
        this.isScreenSharing = false;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        // DOM Elements
        this.localVideo = document.querySelector('#localVideo video');
        this.remoteVideo = document.querySelector('#remoteVideo video');
        this.screenVideo = document.querySelector('#screenShare video');
        this.screenShareContainer = document.querySelector('#screenShare');
        this.toggleVideoBtn = document.querySelector('#toggleVideo');
        this.toggleAudioBtn = document.querySelector('#toggleAudio');
        this.toggleScreenBtn = document.querySelector('#toggleScreen');
        this.connectionStatus = document.querySelector('#connectionStatus');
        this.messagesContainer = document.querySelector('#messages');
        this.messageForm = document.querySelector('#messageForm');
        this.messageInput = document.querySelector('#messageInput');

        // WebRTC Configuration
        this.configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };

        this.init();
    }

    async init() {
        try {
            // Initialize event listeners
            this.initSocketListeners();
            this.initUIListeners();
            
            // Join the session room
            this.socket.emit('join_session', { session_id: this.sessionId });
            
            // Get local media stream
            await this.startLocalStream();
            
            // Initialize peer connection
            this.initPeerConnection();
            
            // Update UI
            this.updateConnectionStatus('Waiting for peer to join...');
            
            // If mentor, create offer when mentee joins
            if (this.role === 'mentor') {
                this.socket.on('user_joined', async (data) => {
                    if (!this.isConnected) {
                        await this.createOffer();
                    }
                });
            }
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to initialize video call. Please check your camera and microphone permissions.');
        }
    }

    initSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Socket connected');
            this.socket.emit('join_session', { 
                session_id: this.sessionId,
                role: this.role 
            });
        });

        this.socket.on('user_joined', async (data) => {
            console.log('User joined:', data);
            if (this.isInitiator) {
                await this.createOffer();
            }
        });

        this.socket.on('webrtc_signal', async (data) => {
            try {
                if (data.signal.type === 'offer') {
                    await this.handleOffer(data.signal);
                } else if (data.signal.type === 'answer') {
                    await this.handleAnswer(data.signal);
                } else if (data.signal.type === 'candidate') {
                    await this.handleCandidate(data.signal.candidate);
                }
            } catch (error) {
                console.error('Error handling signal:', error);
            }
        });

        // Handle screen sharing updates
        this.socket.on('screen_share_update', (data) => {
            if (data.action === 'start') {
                this.screenShareContainer.style.display = 'block';
                this.addSystemMessage(`${data.username} started sharing their screen`);
            } else if (data.action === 'stop') {
                this.screenShareContainer.style.display = 'none';
                this.addSystemMessage(`${data.username} stopped sharing their screen`);
            }
        });

        // Handle chat messages
        this.socket.on('new_message', (data) => {
            this.addChatMessage(data.username, data.message, data.timestamp, false);
        });

        // Handle user joined/left events
        this.socket.on('user_joined', (data) => {
            this.addSystemMessage(`${data.username} joined the session`);
        });

        this.socket.on('user_left', (data) => {
            this.addSystemMessage(`${data.username} left the session`);
            this.updateConnectionStatus('Peer disconnected');
            this.isConnected = false;
        });

        // Handle connection errors
        this.socket.on('connect_error', () => {
            this.updateConnectionStatus('Connection error. Trying to reconnect...');
        });

        this.socket.on('reconnect', () => {
            this.updateConnectionStatus('Reconnected to server');
            this.socket.emit('join_session', { session_id: this.sessionId });
        });
    }

    initUIListeners() {
        // Toggle video
        this.toggleVideoBtn.addEventListener('click', () => {
            this.toggleVideo();
        });

        // Toggle audio
        this.toggleAudioBtn.addEventListener('click', () => {
            this.toggleAudio();
        });

        // Toggle screen sharing
        this.toggleScreenBtn.addEventListener('click', () => {
            if (this.isScreenSharing) {
                this.stopScreenSharing();
            } else {
                this.startScreenSharing();
            }
        });

        // Send message
        this.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = this.messageInput.value.trim();
            if (message) {
                this.sendMessage(message);
                this.messageInput.value = '';
            }
        });
    }

    async startLocalStream() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });
            
            this.localVideo.srcObject = this.localStream;
            
            // Update UI to reflect initial state
            this.updateVideoButton();
            this.updateAudioButton();
            
            return true;
        } catch (error) {
            console.error('Error accessing media devices:', error);
            this.showError('Could not access camera or microphone. Please check permissions.');
            return false;
        }
    }

    initPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.configuration);

        // Add local tracks to peer connection
        this.localStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.localStream);
        });

        // Handle incoming tracks
        this.peerConnection.ontrack = (event) => {
            // Check if this is a screen sharing stream or a regular video stream
            if (event.streams[0].id.includes('screen')) {
                this.screenVideo.srcObject = event.streams[0];
                this.screenShareContainer.style.display = 'block';
            } else {
                this.remoteVideo.srcObject = event.streams[0];
                this.remoteStream = event.streams[0];
            }
        };

        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.emit('webrtc_signal', {
                    session_id: this.sessionId,
                    signal: {
                        type: 'candidate',
                        candidate: event.candidate
                    }
                });
            }
        };

        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            switch(this.peerConnection.connectionState) {
                case 'connected':
                    this.updateConnectionStatus('Connected');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    break;
                case 'disconnected':
                    this.updateConnectionStatus('Disconnected');
                    this.isConnected = false;
                    break;
                case 'failed':
                    this.updateConnectionStatus('Connection failed');
                    this.tryReconnect();
                    break;
                case 'closed':
                    this.updateConnectionStatus('Connection closed');
                    this.isConnected = false;
                    break;
            }
        };

        // Handle ICE connection state changes
        this.peerConnection.oniceconnectionstatechange = () => {
            if (this.peerConnection.iceConnectionState === 'failed') {
                this.tryReconnect();
            }
        };
    }

    async createOffer() {
        try {
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this.socket.emit('webrtc_signal', {
                session_id: this.sessionId,
                signal: {
                    type: 'offer',
                    sdp: this.peerConnection.localDescription
                }
            });
            
            this.updateConnectionStatus('Offer sent, waiting for answer...');
        } catch (error) {
            console.error('Error creating offer:', error);
            this.showError('Failed to create connection offer.');
        }
    }

    async handleOffer(offer) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
            
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            
            this.socket.emit('webrtc_signal', {
                session_id: this.sessionId,
                signal: {
                    type: 'answer',
                    sdp: this.peerConnection.localDescription
                }
            });
            
            this.updateConnectionStatus('Received offer, sent answer...');
        } catch (error) {
            console.error('Error handling offer:', error);
            this.showError('Failed to process connection offer.');
        }
    }

    async handleAnswer(answer) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
            this.updateConnectionStatus('Connection established');
        } catch (error) {
            console.error('Error handling answer:', error);
            this.showError('Failed to process connection answer.');
        }
    }

    async handleCandidate(candidate) {
        try {
            if (candidate && this.peerConnection.remoteDescription) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            }
        } catch (error) {
            console.error('Error adding ICE candidate:', error);
        }
    }

    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                this.isVideoEnabled = !videoTrack.enabled;
                videoTrack.enabled = this.isVideoEnabled;
                this.updateVideoButton();
            }
        }
    }

    toggleAudio() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                this.isAudioEnabled = !audioTrack.enabled;
                audioTrack.enabled = this.isAudioEnabled;
                this.updateAudioButton();
            }
        }
    }

    async startScreenSharing() {
        try {
            this.screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: true
            });
            
            // Mark this stream as a screen share
            this.screenStream.id = 'screen-' + this.screenStream.id;
            
            // Display local screen share
            this.screenVideo.srcObject = this.screenStream;
            this.screenShareContainer.style.display = 'block';
            
            // Add screen track to peer connection
            const screenTrack = this.screenStream.getVideoTracks()[0];
            const sender = this.peerConnection.getSenders().find(s => 
                s.track && s.track.kind === 'video'
            );
            
            if (sender) {
                sender.replaceTrack(screenTrack);
            } else {
                this.peerConnection.addTrack(screenTrack, this.screenStream);
            }
            
            // Update UI
            this.isScreenSharing = true;
            this.toggleScreenBtn.innerHTML = '<i class="fas fa-desktop"></i> Stop Sharing';
            this.toggleScreenBtn.classList.add('active');
            
            // Notify other participants
            this.socket.emit('screen_share', {
                session_id: this.sessionId,
                action: 'start'
            });
            
            // Handle the end of screen sharing
            screenTrack.onended = () => {
                this.stopScreenSharing();
            };
        } catch (error) {
            console.error('Error starting screen sharing:', error);
            this.showError('Failed to start screen sharing.');
        }
    }

    stopScreenSharing() {
        if (this.screenStream) {
            // Stop all tracks
            this.screenStream.getTracks().forEach(track => track.stop());
            
            // Hide screen share container
            this.screenShareContainer.style.display = 'none';
            
            // Replace screen track with camera track
            const videoTrack = this.localStream.getVideoTracks()[0];
            const sender = this.peerConnection.getSenders().find(s => 
                s.track && s.track.kind === 'video'
            );
            
            if (sender && videoTrack) {
                sender.replaceTrack(videoTrack);
            }
            
            // Update UI
            this.isScreenSharing = false;
            this.toggleScreenBtn.innerHTML = '<i class="fas fa-desktop"></i>';
            this.toggleScreenBtn.classList.remove('active');
            
            // Notify other participants
            this.socket.emit('screen_share', {
                session_id: this.sessionId,
                action: 'stop'
            });
        }
    }

    sendMessage(message) {
        // Send message to server
        this.socket.emit('session_message', {
            session_id: this.sessionId,
            message: message
        });
        
        // Add message to UI
        const timestamp = new Date().toLocaleTimeString();
        this.addChatMessage('You', message, timestamp, true);
    }

    addChatMessage(sender, message, timestamp, isSelf) {
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${isSelf ? 'sent' : 'received'}`;
        
        messageElement.innerHTML = `
            <div class="chat-message-content ${isSelf ? 'bg-primary text-white' : 'bg-light'}">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold">${sender}</span>
                    <small class="text-${isSelf ? 'light' : 'muted'}">${timestamp}</small>
                </div>
                <div>${message}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    addSystemMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'text-center my-2';
        messageElement.innerHTML = `<small class="text-muted">${message}</small>`;
        
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    updateVideoButton() {
        if (this.isVideoEnabled) {
            this.toggleVideoBtn.innerHTML = '<i class="fas fa-video"></i>';
            this.toggleVideoBtn.classList.remove('btn-danger');
            this.toggleVideoBtn.classList.add('btn-outline-primary');
        } else {
            this.toggleVideoBtn.innerHTML = '<i class="fas fa-video-slash"></i>';
            this.toggleVideoBtn.classList.remove('btn-outline-primary');
            this.toggleVideoBtn.classList.add('btn-danger');
        }
    }

    updateAudioButton() {
        if (this.isAudioEnabled) {
            this.toggleAudioBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            this.toggleAudioBtn.classList.remove('btn-danger');
            this.toggleAudioBtn.classList.add('btn-outline-primary');
        } else {
            this.toggleAudioBtn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            this.toggleAudioBtn.classList.remove('btn-outline-primary');
            this.toggleAudioBtn.classList.add('btn-danger');
        }
    }

    updateConnectionStatus(status) {
        if (this.connectionStatus) {
            this.connectionStatus.textContent = status;
            
            // Update status indicator color
            this.connectionStatus.className = 'connection-status';
            if (status.includes('Connected')) {
                this.connectionStatus.classList.add('text-success');
            } else if (status.includes('Waiting') || status.includes('Offer') || status.includes('answer')) {
                this.connectionStatus.classList.add('text-warning');
            } else {
                this.connectionStatus.classList.add('text-danger');
            }
        }
    }

    tryReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateConnectionStatus(`Connection failed. Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            // Close existing connection
            if (this.peerConnection) {
                this.peerConnection.close();
            }
            
            // Reinitialize after a delay
            setTimeout(() => {
                this.initPeerConnection();
                if (this.role === 'mentor') {
                    this.createOffer();
                }
            }, 2000);
        } else {
            this.updateConnectionStatus('Could not reconnect after multiple attempts. Please refresh the page.');
            this.showError('Connection failed after multiple attempts. Please refresh the page to try again.');
        }
    }

    showError(message) {
        // Use SweetAlert2 if available, otherwise use alert
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: message
            });
        } else {
            alert(message);
        }
    }

    cleanup() {
        // Stop all media tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.screenStream) {
            this.screenStream.getTracks().forEach(track => track.stop());
        }
        
        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        
        // Leave the session room
        this.socket.emit('leave_session', { session_id: this.sessionId });
    }
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const sessionContainer = document.querySelector('[data-session-id]');
    if (sessionContainer) {
        const sessionId = sessionContainer.dataset.sessionId;
        const role = sessionContainer.dataset.role;
        
        // Create WebRTC handler
        const webrtcHandler = new WebRTCHandler(sessionId, role);
        
        // Clean up when leaving the page
        window.addEventListener('beforeunload', () => {
            webrtcHandler.cleanup();
        });
    }
});
