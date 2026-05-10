const MAX_AUDIO_BYTES = 1_048_576;
const OPUS_BITRATE_BPS = 128_000;

export class AudioRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.stream = null;
    this.isRecording = false;
    this.totalBytes = 0;
    this.MAX_AUDIO_BYTES = MAX_AUDIO_BYTES;
    this.OPUS_BITRATE_BPS = OPUS_BITRATE_BPS;
    
    this.audioContext = null;
    this.sourceNode = null;
    this.processorNode = null;
    this.pcmChunkCallback = null;
    this.pcmBuffer = [];
    this.pcmChunkSize = 4000;


  }

  /**
   * Request microphone permission and initialize
   */
  async initialize() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 48000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 48000
      });

      return true;
    } catch (error) {
      console.error("❌ Microphone access denied:", error);
      return false;
    }
  }

  /**
   * Start recording audio (WebM/Opus for final + PCM for streaming)
   * 
   * @param {Function} onSizeUpdate - Callback for size updates
   * @param {Function} onLimitReached - Callback when limit reached
   * @param {Function} onPCMChunk - Callback for PCM chunks (for streaming)
   */
  async startRecording(onSizeUpdate, onLimitReached, onPCMChunk) {
    if (!this.stream) throw new Error("Microphone not initialized");

    this.audioChunks = [];
    this.totalBytes = 0;
    this.pcmBuffer = [];
    this.pcmChunkCallback = onPCMChunk;

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType,
      audioBitsPerSecond: 128_000,
    });

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data?.size > 0) {
        this.audioChunks.push(event.data);
        this.totalBytes += event.data.size;

        if (onSizeUpdate) {
          onSizeUpdate(this.totalBytes);
        }

        if (this.totalBytes >=this.MAX_AUDIO_BYTES) {
          console.warn("🚨 Audio size limit reached — stopping recorder");
          if (onLimitReached) onLimitReached();
          this.stopRecording();
        }
      }
    };

    this.mediaRecorder.start(250);

    await this._startPCMCapture();

    this.isRecording = true;
  }

  /**
   * ✅ NEW: Start PCM capture for streaming
   * @private
   */
  async _startPCMCapture() {
    try {
      this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);
      
      const bufferSize = 4096;
      this.processorNode = this.audioContext.createScriptProcessor(
        bufferSize,
        1,
        1
      );

      this.processorNode.onaudioprocess = (e) => {
        if (!this.isRecording) return;

        const inputData = e.inputBuffer.getChannelData(0);

        
        const pcmData = this._downsampleAndConvertToPCM(inputData, 48000, 16000);
        
        this.pcmBuffer.push(...pcmData);


        if (this.pcmBuffer.length >= this.pcmChunkSize) {
          const chunk = new Int16Array(this.pcmBuffer.splice(0, this.pcmChunkSize));
          
          const buffer = chunk.buffer;

          
          if (this.pcmChunkCallback) {
            this.pcmChunkCallback(buffer);
          }
        }
      };

      this.sourceNode.connect(this.processorNode);
      this.processorNode.connect(this.audioContext.destination);


    } catch (error) {
      console.error("❌ Failed to start PCM capture:", error);
    }
  }

  /**
   * ✅ NEW: Downsample and convert Float32 → Int16 PCM
   * @private
   */
  _downsampleAndConvertToPCM(buffer, fromSampleRate, toSampleRate) {
    if (fromSampleRate === toSampleRate) {
      return this._float32ToInt16(buffer);
    }

    const sampleRateRatio = fromSampleRate / toSampleRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);

    let offsetResult = 0;
    let offsetBuffer = 0;

    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
      
      let accum = 0;
      let count = 0;

      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }

      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }

    return this._float32ToInt16(result);
  }

  /**
   * ✅ NEW: Convert Float32Array → Int16Array PCM
   * @private
   */
  _float32ToInt16(buffer) {
    const int16 = new Int16Array(buffer.length);
    
    for (let i = 0; i < buffer.length; i++) {
      let s = Math.max(-1, Math.min(1, buffer[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    
    return int16;
  }

  /**
   * Stop recording and return WebM blob
   */
  async stopRecording() {
    return new Promise((resolve) => {
      if (!this.mediaRecorder || !this.isRecording) {
        resolve(null);
        return;
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, {
          type: this.mediaRecorder.mimeType || "audio/webm",
        });

        this.audioChunks = [];
        this.isRecording = false;

        this._stopPCMCapture();

        console.log(
          "⏹️ Recording stopped:",
          audioBlob.size,
          "bytes",
          audioBlob.type
        );

        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  /**
   * ✅ NEW: Stop PCM capture
   * @private
   */
  _stopPCMCapture() {
    try {
      if (this.processorNode) {
        this.processorNode.disconnect();
        this.processorNode.onaudioprocess = null;
        this.processorNode = null;
      }

      if (this.sourceNode) {
        this.sourceNode.disconnect();
        this.sourceNode = null;
      }

      if (this.pcmBuffer.length > 0 && this.pcmChunkCallback) {
        const chunk = new Int16Array(this.pcmBuffer);
        this.pcmChunkCallback(chunk.buffer);
        this.pcmBuffer = [];
      }

    } catch (error) {
      console.error("⚠️ Error stopping PCM capture:", error);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this._stopPCMCapture();

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }

    if (this.mediaRecorder) {
      this.mediaRecorder = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}


export class AudioPlayer {
  constructor() {
    this.audioContext = null;
    this.source = null;
  }

  async initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
  }

  async playBase64Audio(base64Audio) {
    if (!this.audioContext) {
      await this.initialize();
    }

    const binary = atob(base64Audio);
    const len = binary.length;
    const buffer = new Uint8Array(len);

    for (let i = 0; i < len; i++) {
      buffer[i] = binary.charCodeAt(i);
    }

    const audioBuffer = await this.audioContext.decodeAudioData(buffer.buffer);

    this.source = this.audioContext.createBufferSource();
    this.source.buffer = audioBuffer;
    this.source.connect(this.audioContext.destination);
    this.source.start(0);

    return new Promise((resolve) => {
      this.source.onended = resolve;
    });
  }

  stop() {
    try {
      this.source?.stop();
      this.source = null;
    } catch (e) {}
  }

  cleanup() {
    this.stop();
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}
