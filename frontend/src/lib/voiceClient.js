/**
 * VoiceInterviewClient
 * Token-authenticated, stable WebSocket client for voice interviews
 * Production-ready with environment-aware URLs
 */

export class VoiceInterviewClient {
  constructor(interviewId, token) {
    this.interviewId = interviewId;
    this.token = token;

    this.ws = null;
    this.isConnected = false;
    this.manualClose = false;

    // heartbeat
    this.heartbeatInterval = null;

    // reconnect
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;

    this.listeners = {
      open: [],
      close: [],
      error: [],
      message: [],
      reconnect: [],
    };
  }

  /* -------------------------------------------------------------------------- */
  /*                               CONNECT                                      */
  /* -------------------------------------------------------------------------- */

  async connect() {
    return new Promise((resolve, reject) => {
      if (!this.token) {
        reject(new Error('Missing JWT token'));
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const host = apiUrl.replace(/^https?:\/\//, '');
      const wsUrl = `${protocol}//${host}/api/v1/ws/interview/${this.interviewId}/voice?token=${this.token}`;

      // console.log('🔌 Connecting to:', wsUrl);

      try {
        this.ws = new WebSocket(wsUrl);
        this.ws.binaryType = 'arraybuffer';
      } catch (err) {
        reject(err);
        return;
      }

      this.ws.onopen = () => {
        // console.log('✅ WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.manualClose = false;

        this.startHeartbeat();
        this.emit('open');
        resolve();
      };

      this.ws.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
        this.emit('error', err);
      };

      this.ws.onclose = (event) => {
        console.warn('🔌 WebSocket closed', event?.code, event?.reason);
        this.isConnected = false;
        this.stopHeartbeat();
        this.emit('close');

        if (!this.manualClose) {
          this.tryReconnect();
        }
      };

      this.ws.onmessage = (event) => {
        this.handleIncoming(event);
      };

      setTimeout(() => {
        if (!this.isConnected) {
          reject(new Error('WebSocket connection timeout'));
        }
      }, 10000);
    });
  }

  /* -------------------------------------------------------------------------- */
  /*                         INCOMING MESSAGE HANDLER                           */
  /* -------------------------------------------------------------------------- */

  handleIncoming(event) {
    try {
      if (event.data instanceof ArrayBuffer) {
        this.emit('message', { type: 'binary', data: event.data });
        return;
      }

      const json = JSON.parse(event.data);
      this.emit('message', json);
    } catch (err) {
      console.error('Error parsing incoming WS message:', err);
      this.emit('error', err);
    }
  }

  /* -------------------------------------------------------------------------- */
  /*                               HEARTBEAT                                    */
  /* -------------------------------------------------------------------------- */

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.safeSend({ type: 'ping' });
      }
    }, 15000);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /* -------------------------------------------------------------------------- */
  /*                          RECONNECT HANDLING                                */
  /* -------------------------------------------------------------------------- */

  tryReconnect() {
    if (this.maxReconnectAttempts === 0) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    if (this.manualClose) return;

    const delay = Math.min(5000, 1000 * 2 ** this.reconnectAttempts);
    this.reconnectAttempts++;

    // console.log(`🔄 Reconnecting in ${delay / 1000}s...`);
    this.emit('reconnect', this.reconnectAttempts);

    setTimeout(() => {
      this.connect().catch(() => this.tryReconnect());
    }, delay);
  }

  /* -------------------------------------------------------------------------- */
  /*                          SAFE JSON SENDING                                 */
  /* -------------------------------------------------------------------------- */

  safeSend(data) {
    if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ Cannot send JSON: WebSocket not connected/open');
      return;
    }

    try {
      this.ws.send(JSON.stringify(data));
    } catch (err) {
      console.error('❌ JSON send failed:', err);
      this.emit('error', err);
    }
  }

  /* -------------------------------------------------------------------------- */
  /*                        SAFE AUDIO (BINARY) SENDING                          */
  /* -------------------------------------------------------------------------- */

  async sendAudio(audioBlob) {
    if (!this.isConnected || !this.ws) {
      console.warn('⚠️ Cannot send audio: WebSocket not connected');
      throw new Error('WebSocket not connected');
    }

    if (this.ws.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ WebSocket not OPEN — cannot send audio');
      throw new Error('WebSocket not open');
    }

    try {
      const buffer = await audioBlob.arrayBuffer();
      this.ws.send(buffer);
      // console.log('📤 Sent audio:', audioBlob.size, 'bytes');
    } catch (err) {
      console.error('❌ Failed to send audio:', err);
      this.emit('error', err);
      throw err;
    }
  }

  /* -------------------------------------------------------------------------- */
  /*                          STREAMING METHODS (NEW)                           */
  /* -------------------------------------------------------------------------- */

  /**
   * Start streaming session (control message)
   */
  startStreaming() {
    if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ Cannot start streaming: WebSocket not connected');
      return false;
    }

    try {
      this.safeSend({ type: 'start_streaming' });
      // console.log('🎙️ Streaming started');
      return true;
    } catch (err) {
      console.error('❌ Failed to start streaming:', err);
      return false;
    }
  }

  /**
   * Send PCM chunk as raw binary
   * @param {ArrayBuffer} pcmBuffer
   */
  sendPCMChunk(pcmBuffer) {
    if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ Cannot send PCM chunk: WebSocket not connected');
      return false;
    }

    try {
      //  console.log(`📡 Sending ${pcmBuffer.byteLength} bytes via WebSocket`);
      this.ws.send(pcmBuffer);
      
      return true;
    } catch (err) {
      console.error('❌ Failed to send PCM chunk:', err);
      return false;
    }
  }

  /**
   * Stop streaming session (control message)
   */
  stopStreaming() {
    if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ Cannot stop streaming: WebSocket not connected');
      return false;
    }

    try {
      this.safeSend({ type: 'stop_streaming' });
      // console.log('🔇 Streaming stopped');
      return true;
    } catch (err) {
      console.error('❌ Failed to stop streaming:', err);
      return false;
    }
  }

  /* -------------------------------------------------------------------------- */
  /*                                 STOP                                       */
  /* -------------------------------------------------------------------------- */

  stop() {
    try {
      this.safeSend({ type: 'stop' });
    } catch (err) {
      console.warn('stop() safeSend failed', err);
    }
  }

  /* -------------------------------------------------------------------------- */
  /*                             DISCONNECT                                     */
  /* -------------------------------------------------------------------------- */

  disconnect() {
    this.manualClose = true;
    this.stopHeartbeat();

    if (this.ws) {
      try {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.close(1000, 'client_disconnect');
        } else {
          this.ws.onclose = null;
          this.ws.close();
        }
      } catch (_) {}
    }

    this.ws = null;
    this.isConnected = false;
    // console.log('🧹 WebSocket disconnected manually');
  }

  /* -------------------------------------------------------------------------- */
  /*                            EVENT EMITTER                                   */
  /* -------------------------------------------------------------------------- */

  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      for (const cb of this.listeners[event]) {
        try {
          cb(data);
        } catch (err) {
          console.error('Listener callback error', err);
        }
      }
    }
  }
}
