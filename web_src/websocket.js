/**
 * web/src/websocket.js — Hardened WebSocket Manager
 * Provides resilient, heartbeat-backed real-time connection with exponential backoff.
 */

class BackendWSManager {
  constructor() {
    this.socket = null;
    this.listeners = new Set();
    this.reconnectAttempts = 0;
    this.heartbeatInterval = null;
    this.isConnecting = false;
  }

  getWsUrl() {
    if (typeof window !== "undefined" && window.__API_BASE__) {
      const u = new URL(window.__API_BASE__);
      return `${u.protocol === "https:" ? "wss:" : "ws:"}//${u.host}/ws`;
    }
    if (typeof window !== "undefined" && window.location) {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${window.location.host}/ws`;
    }
    return "ws://127.0.0.1:8000/ws";
  }

  connect() {
    if (this.isConnecting || (this.socket && this.socket.readyState === WebSocket.OPEN)) return;
    this.isConnecting = true;
    try {
      this.socket = new WebSocket(this.getWsUrl());
      this.socket.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };
      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.type === "PONG") return; // Handled heartbeat response
          this.notify(data);
        } catch (e) {
          console.warn("WebSocket parse error:", e);
        }
      };
      this.socket.onclose = () => {
        this.cleanup();
        this.scheduleReconnect();
      };
      this.socket.onerror = () => {
        this.cleanup();
        this.scheduleReconnect();
      };
    } catch {
      this.cleanup();
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    const ms = Math.min(1000 * Math.pow(2, this.reconnectAttempts++), 20000);
    setTimeout(() => this.connect(), ms);
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: "ping" }));
      }
    }, 15000);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  cleanup() {
    this.isConnecting = false;
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.onopen = this.socket.onmessage = this.socket.onclose = this.socket.onerror = null;
      this.socket = null;
    }
  }

  subscribe(cb) {
    this.listeners.add(cb);
    if (!this.socket) this.connect();
    return () => this.listeners.delete(cb);
  }

  notify(data) {
    this.listeners.forEach((fn) => fn(data));
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { BackendWSManager };
}
