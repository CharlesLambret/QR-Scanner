/**
 * Service de gestion des WebSockets
 */
class SocketService {
  constructor(scanId) {
    this.scanId = scanId;
    this.socket = null;
    this.callbacks = {
      progress: [],
      complete: [],
      error: [],
      connect: [],
      disconnect: []
    };
    
    console.log("🔍 SocketService initialisé avec scanId:", this.scanId);
  }

  connect() {
    try {
      this.socket = io();
      console.log("🔌 Socket.IO instance créée");
      
      this.socket.on("connect", () => {
        console.log("🔌 Socket.IO connecté avec succès");
        this.socket.emit("client_ready", { scan_id: this.scanId });
        this._triggerCallbacks('connect');
      });

      this.socket.on("disconnect", () => {
        console.log("🔌 Socket.IO déconnecté");
        this._triggerCallbacks('disconnect');
      });

      this.socket.on("scan_progress", (data) => {
        console.log("📊 Event scan_progress reçu:", data);
        if (data.scan_id === this.scanId) {
          console.log("✅ scan_progress: mise à jour du message:", data.message);
          this._triggerCallbacks('progress', data);
        }
      });

      this.socket.on("scan_complete", (data) => {
        console.log("🎉 Event scan_complete reçu:", data);
        if (data.scan_id === this.scanId) {
          console.log("✅ scan_complete: traitement des résultats...");
          this._triggerCallbacks('complete', data);
        }
      });

      this.socket.on("scan_error", (data) => {
        console.log("❌ Event scan_error reçu:", data);
        if (data.scan_id === this.scanId) {
          this._triggerCallbacks('error', data);
        }
      });

    } catch (error) {
      console.error("❌ Erreur lors de l'initialisation du socket:", error);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  // Méthodes d'abonnement aux événements
  onProgress(callback) {
    this.callbacks.progress.push(callback);
  }

  onComplete(callback) {
    this.callbacks.complete.push(callback);
  }

  onError(callback) {
    this.callbacks.error.push(callback);
  }

  onConnect(callback) {
    this.callbacks.connect.push(callback);
  }

  onDisconnect(callback) {
    this.callbacks.disconnect.push(callback);
  }

  _triggerCallbacks(event, data = null) {
    this.callbacks[event].forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`❌ Erreur dans callback ${event}:`, error);
      }
    });
  }

  emit(eventName, data) {
    if (this.socket && this.socket.connected) {
      this.socket.emit(eventName, data);
    } else {
      console.warn("⚠️ Socket non connecté, impossible d'envoyer:", eventName);
    }
  }
}