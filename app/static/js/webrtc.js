// WebRTC configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

class WebRTCHandler {
    constructor(socket, sessionId) {
        this.socket = socket;
        this.sessionId = sessionId;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.isScreenSharing = false;

        // Bind socket event handlers
        this.socket.on('webrtc_signal', this.handleSignal.bind(this));
        this.socket.on('screen_share_update', this.handleScreenShareUpdate.bind(this));
    }

    async initializeConnection() {
        this.peerConnection = new RTCPeerConnection(configuration);

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

        // Handle remote stream
        this.peerConnection.ontrack = (event) => {
            this.remoteStream = event.streams[0];
            const remoteVideo = document.getElementById('remoteVideo');
            if (remoteVideo) {
                remoteVideo.srcObject = this.remoteStream;
            }
        };
    }

    async startLocalStream(videoEnabled = true, audioEnabled = true) {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: videoEnabled,
                audio: audioEnabled
            });

            const localVideo = document.getElementById('localVideo');
            if (localVideo) {
                localVideo.srcObject = this.localStream;
            }

            // Add tracks to peer connection
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });

            return true;
        } catch (error) {
            console.error('Error accessing media devices:', error);
            return false;
        }
    }

    async startScreenShare() {
        try {
            const screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: true
            });

            // Replace video track
            const videoTrack = screenStream.getVideoTracks()[0];
            const senders = this.peerConnection.getSenders();
            const videoSender = senders.find(sender => sender.track?.kind === 'video');
            if (videoSender) {
                videoSender.replaceTrack(videoTrack);
            }

            // Update local video
            const localVideo = document.getElementById('localVideo');
            if (localVideo) {
                localVideo.srcObject = screenStream;
            }

            this.isScreenSharing = true;
            this.socket.emit('screen_share', {
                session_id: this.sessionId,
                action: 'start'
            });

            // Handle screen share stop
            videoTrack.onended = () => this.stopScreenShare();

            return true;
        } catch (error) {
            console.error('Error starting screen share:', error);
            return false;
        }
    }

    async stopScreenShare() {
        if (!this.isScreenSharing) return;

        try {
            // Revert to camera
            await this.startLocalStream();
            this.isScreenSharing = false;
            this.socket.emit('screen_share', {
                session_id: this.sessionId,
                action: 'stop'
            });
        } catch (error) {
            console.error('Error stopping screen share:', error);
        }
    }

    async createOffer() {
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

    async handleSignal(data) {
        const signal = data.signal;

        try {
            if (signal.type === 'offer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal.sdp));
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
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal.sdp));
            } else if (signal.type === 'candidate') {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
            }
        } catch (error) {
            console.error('Error handling signal:', error);
        }
    }

    handleScreenShareUpdate(data) {
        // Handle remote user's screen share status update
        const remoteVideo = document.getElementById('remoteVideo');
        if (remoteVideo) {
            remoteVideo.classList.toggle('screen-share', data.action === 'start');
        }
    }

    cleanup() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        this.socket.off('webrtc_signal');
        this.socket.off('screen_share_update');
    }
}

// Export the WebRTCHandler class
export default WebRTCHandler;