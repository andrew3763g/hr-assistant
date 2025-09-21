(function () {
  const globalConfig = window.CONFIG || {};
  const DEFAULT_TIMESLICE = normalisePositive(globalConfig.MEDIA_TIMESLICE_MS, 45000);
  const DEFAULT_MAX_CHUNKS = normalisePositive(globalConfig.MEDIA_MAX_CHUNKS, 80);
  const API_BASE = (globalConfig.MEDIA_UPLOAD_BASE || '/api/interviews').replace(/\/$/, '');
  const UPLOAD_ENDPOINT = `${API_BASE}/upload/chunk`;
  const FINALIZE_ENDPOINT = `${API_BASE}/upload/finalize`;

  const DEFAULT_RETRY_OPTIONS = {
    retries: 4,
    minTimeout: 500,
    factor: 2,
    maxTimeout: 5000,
  };

  function normalisePositive(value, fallback) {
    const numeric = Number(value);
    if (Number.isFinite(numeric) && numeric > 0) {
      return numeric;
    }
    return fallback;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function withRetry(task, options = {}) {
    const cfg = { ...DEFAULT_RETRY_OPTIONS, ...options };
    let attempt = 0;
    let delay = cfg.minTimeout;

    // eslint-disable-next-line no-constant-condition
    while (true) {
      try {
        return await task();
      } catch (error) {
        const retryable = error && (error.retryable === undefined || error.retryable === true);
        if (attempt >= cfg.retries || !retryable) {
          throw error;
        }
        await sleep(delay);
        attempt += 1;
        delay = Math.min(delay * cfg.factor, cfg.maxTimeout);
      }
    }
  }

  function defaultNotifyLimit(maxChunks) {
    const message = `Достигнут максимальный лимит записанных фрагментов (${maxChunks}). Запись остановлена.`;
    if (typeof window.toast === 'function') {
      window.toast(message, { type: 'warning' });
    } else if (typeof window.alert === 'function') {
      window.alert(message);
    } else {
      console.warn(message);
    }
  }

  function defaultHandleError(error) {
    console.error('Recorder error:', error);
  }

  class ChunkedRecorder {
    constructor(options = {}) {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Браузер не поддерживает запись mediaDevices.getUserMedia');
      }

      this.sessionId = options.sessionId;
      if (!this.sessionId) {
        throw new Error('sessionId is required for ChunkedRecorder');
      }

      this.kind = options.kind || 'audio';
      this.timeslice = normalisePositive(options.timeslice, DEFAULT_TIMESLICE);
      this.maxChunks = normalisePositive(options.maxChunks, DEFAULT_MAX_CHUNKS);
      this.mimeType = options.mimeType;
      this.constraints = options.constraints || { audio: true, video: false };
      this.onLimitReached = options.onLimitReached || ((info) => defaultNotifyLimit(info.maxChunks));
      this.onError = options.onError || defaultHandleError;
      this.onChunkUploaded = options.onChunkUploaded;
      this.retryOptions = { ...DEFAULT_RETRY_OPTIONS, ...options.retryOptions };

      this._mediaRecorder = null;
      this._stream = null;
      this._chunkIndex = 0;
      this._activeUploads = new Set();
      this._stopPromise = null;
      this._stopResolver = null;
      this._stopInitiated = false;
      this._finalized = false;
      this._limitReached = false;
    }

    async start() {
      if (this._mediaRecorder) {
        throw new Error('Recorder already started');
      }

      try {
        this._stream = await navigator.mediaDevices.getUserMedia(this.constraints);
      } catch (error) {
        this.onError(error);
        throw error;
      }

      const recorderOptions = {};
      if (this.mimeType) {
        recorderOptions.mimeType = this.mimeType;
      }

      this._mediaRecorder = new MediaRecorder(this._stream, recorderOptions);
      this._mediaRecorder.addEventListener('dataavailable', (event) => {
        void this._handleChunk(event);
      });
      this._mediaRecorder.addEventListener('error', (event) => {
        this.onError(event.error);
      });
      this._stopPromise = new Promise((resolve) => {
        this._stopResolver = resolve;
      });
      this._mediaRecorder.addEventListener('stop', () => {
        if (this._stopResolver) {
          this._stopResolver();
        }
      });

      this._mediaRecorder.start(this.timeslice);
    }

    async stop({ finalize = true } = {}) {
      if (!this._mediaRecorder) {
        if (finalize) {
          return this.finalize();
        }
        return undefined;
      }

      if (this._stopInitiated) {
        return this._stopPromise.then(() => (finalize ? this.finalize() : undefined));
      }

      this._stopInitiated = true;

      if (this._mediaRecorder.state !== 'inactive') {
        try {
          this._mediaRecorder.stop();
        } catch (error) {
          this.onError(error);
        }
      }
      if (this._stream) {
        this._stream.getTracks().forEach((track) => track.stop());
      }

      return this._stopPromise.then(async () => {
        await Promise.allSettled(Array.from(this._activeUploads));
        this._cleanup();
        if (finalize) {
          return this.finalize();
        }
        return undefined;
      });
    }

    async finalize() {
      if (this._finalized) {
        return this._finalized;
      }

      await Promise.allSettled(Array.from(this._activeUploads));

      const payload = { session_id: this.sessionId };

      const response = await withRetry(async () => {
        const res = await fetch(FINALIZE_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const error = new Error(`Finalize failed with status ${res.status}`);
          error.retryable = res.status >= 500 || res.status === 429;
          throw error;
        }

        return res.json();
      }, this.retryOptions).catch((error) => {
        this.onError(error);
        throw error;
      });

      this._finalized = response;
      return response;
    }

    async _handleChunk(event) {
      const blob = event.data;
      if (!blob || !blob.size) {
        return;
      }

      if (this._chunkIndex >= this.maxChunks) {
        if (!this._limitReached) {
          this._limitReached = true;
          try {
            await this.onLimitReached({ kind: this.kind, maxChunks: this.maxChunks });
          } catch (notifyError) {
            console.warn('onLimitReached handler error:', notifyError);
          }
          void this.stop();
        }
        return;
      }

      const currentIndex = this._chunkIndex;
      this._chunkIndex += 1;

      const uploadPromise = this._uploadChunk(blob, currentIndex)
        .then((result) => {
          if (typeof this.onChunkUploaded === 'function') {
            this.onChunkUploaded({ index: currentIndex, result });
          }
          return result;
        })
        .catch((error) => {
          this.onError(error);
          throw error;
        });

      this._activeUploads.add(uploadPromise);
      uploadPromise.finally(() => {
        this._activeUploads.delete(uploadPromise);
      });

      if (this._chunkIndex >= this.maxChunks && !this._limitReached) {
        this._limitReached = true;
        try {
          await this.onLimitReached({ kind: this.kind, maxChunks: this.maxChunks });
        } catch (notifyError) {
          console.warn('onLimitReached handler error:', notifyError);
        }
        void this.stop();
      }
    }

    async _uploadChunk(blob, index) {
      const formData = new FormData();
      formData.append('session_id', this.sessionId);
      formData.append('kind', this.kind);
      formData.append('index', index.toString());
      formData.append('chunk', blob, this._chunkFileName(index));

      return withRetry(async () => {
        const response = await fetch(UPLOAD_ENDPOINT, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const error = new Error(`Chunk upload failed with status ${response.status}`);
          error.retryable = response.status >= 500 || response.status === 429;
          throw error;
        }

        return response.json();
      }, this.retryOptions);
    }

    _chunkFileName(index) {
      const padded = index.toString().padStart(6, '0');
      return `${this.kind}_${padded}.webm`;
    }

    _cleanup() {
      this._mediaRecorder = null;
      this._stream = null;
      this._stopPromise = null;
      this._stopResolver = null;
    }
  }

  window.ChunkedRecorder = ChunkedRecorder;
})();
