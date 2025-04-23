// WebRTC and Socket.IO handling for session room
class SessionRoom {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.socket = io();
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.screenStream = null;
        this.isAudioEnabled = true;
        this.isVideoEnabled = true;
        this.isScreenSharing = false;

        this.configuration = {
            iceServers: [{
                urls: 'stun:stun.l.google.com:19302'
            }]
        };

        this.initializeEventListeners();
        this.joinSession();
    }

    async initializeEventListeners() {
        // Socket.IO event listeners
        this.socket.on('user_joined', this.handleUserJoined.bind(this));
        this.socket.on('user_left', this.handleUserLeft.bind(this));
        this.socket.on('webrtc_signal', this.handleWebRTCSignal.bind(this));
        this.socket.on('screen_share_update', this.handleScreenShareUpdate.bind(this));

        // UI Controls
        document.getElementById('toggleVideo').addEventListener('click', this.toggleVideo.bind(this));
        document.getElementById('toggleAudio').addEventListener('click', this.toggleAudio.bind(this));
        document.getElementById('toggleScreen').addEventListener('click', this.toggleScreenShare.bind(this));

        // Initialize media stream
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });
            document.querySelector('#localVideo video').srcObject = this.localStream;
            await this.initializePeerConnection();
        } catch (error) {
            console.error('Error accessing media devices:', error);
            alert('Error accessing camera/microphone. Please check permissions.');
        }
    }

    async initializePeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.configuration);

        // Add local stream tracks to peer connection
        this.localStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.localStream);
        });

        // Handle incoming streams
        this.peerConnection.ontrack = (event) => {
            this.remoteStream = event.streams[0];
            document.querySelector('#remoteVideo video').srcObject = this.remoteStream;
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
    }

    joinSession() {
        this.socket.emit('join_session', { session_id: this.sessionId });
    }

    async handleUserJoined(data) {
        const timestamp = new Date(data.timestamp).toLocaleTimeString();
        this.addSystemMessage(`${data.username} joined the session`, timestamp);

        if (document.querySelector('[data-role="mentor"]')) {
            try {
                const offer = await this.peerConnection.createOffer();
                await this.peerConnection.setLocalDescription(offer);
                this.socket.emit('webrtc_signal', {
                    session_id: this.sessionId,
                    signal: {
                        type: 'offer',
                        sdp: offer
                    }
                });
            } catch (error) {
                console.error('Error creating offer:', error);
            }
        }
    }

    handleUserLeft(data) {
        const timestamp = new Date(data.timestamp).toLocaleTimeString();
        this.addSystemMessage(`${data.username} left the session`, timestamp);
    }

    async handleWebRTCSignal(data) {
        try {
            const signal = data.signal;
            if (signal.type === 'offer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal));
                const answer = await this.peerConnection.createAnswer();
                await this.peerConnection.setLocalDescription(answer);
                this.socket.emit('webrtc_signal', {
                    session_id: this.sessionId,
                    signal: {
                        type: 'answer',
                        sdp: answer
                    }
                });
            } else if (signal.type === 'answer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal));
            } else if (signal.type === 'candidate') {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
            }
        } catch (error) {
            console.error('Error handling WebRTC signal:', error);
        }
    }

    toggleVideo() {
        this.isVideoEnabled = !this.isVideoEnabled;
        this.localStream.getVideoTracks().forEach(track => {
            track.enabled = this.isVideoEnabled;
        });
        document.getElementById('toggleVideo').innerHTML = 
            `<i class="fas fa-video${this.isVideoEnabled ? '' : '-slash'}"></i>`;
    }

    toggleAudio() {
        this.isAudioEnabled = !this.isAudioEnabled;
        this.localStream.getAudioTracks().forEach(track => {
            track.enabled = this.isAudioEnabled;
        });
        document.getElementById('toggleAudio').innerHTML = 
            `<i class="fas fa-microphone${this.isAudioEnabled ? '' : '-slash'}"></i>`;
    }

    async toggleScreenShare() {
        try {
            if (!this.isScreenSharing) {
                this.screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
                const screenTrack = this.screenStream.getVideoTracks()[0];

                // Replace video track
                const videoSender = this.peerConnection.getSenders().find(sender => 
                    sender.track.kind === 'video'
                );
                await videoSender.replaceTrack(screenTrack);

                document.querySelector('#screenShare video').srcObject = this.screenStream;
                document.getElementById('screenShare').style.display = 'block';
                document.getElementById('toggleScreen').innerHTML = 
                    '<i class="fas fa-times"></i>';

                // Handle screen sharing stop
                screenTrack.onended = () => this.stopScreenSharing();
                this.isScreenSharing = true;

                this.socket.emit('screen_share', {
                    session_id: this.sessionId,
                    action: 'start'
                });
            } else {
                await this.stopScreenSharing();
            }
        } catch (error) {
            console.error('Error sharing screen:', error);
            alert('Error sharing screen. Please try again.');
        }
    }

    async stopScreenSharing() {
        if (this.screenStream) {
            this.screenStream.getTracks().forEach(track => track.stop());
            
            // Restore video track
            const videoTrack = this.localStream.getVideoTracks()[0];
            const videoSender = this.peerConnection.getSenders().find(sender => 
                sender.track.kind === 'video'
            );
            await videoSender.replaceTrack(videoTrack);

            document.getElementById('screenShare').style.display = 'none';
            document.getElementById('toggleScreen').innerHTML = 
                '<i class="fas fa-desktop"></i>';
            this.isScreenSharing = false;

            this.socket.emit('screen_share', {
                session_id: this.sessionId,
                action: 'stop'
            });
        }
    }

    handleScreenShareUpdate(data) {
        const timestamp = new Date().toLocaleTimeString();
        const action = data.action === 'start' ? 'started' : 'stopped';
        this.addSystemMessage(`${data.username} ${action} screen sharing`, timestamp);
    }

    addSystemMessage(message, timestamp) {
        const messagesDiv = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message system';
        messageDiv.innerHTML = `
            <div class="message-content">${message}</div>
            <div class="timestamp">${timestamp}</div>
        `;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

// Initialize session room when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const sessionId = document.querySelector('[data-session-id]').dataset.sessionId;
    window.sessionRoom = new SessionRoom(sessionId);
});