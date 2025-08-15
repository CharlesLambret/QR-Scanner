/**
 * Application JavaScript principale pour QR Scanner
 * Fonctions utilitaires globales et configuration
 */

// Configuration globale
window.QRScanner = {
  version: '1.0.0',
  debug: true,
  
  // Utilitaires globaux
  utils: {
    formatUrl: function(url, maxLength = 50) {
      if (url.length > maxLength) {
        return url.substring(0, maxLength) + '...';
      }
      return url;
    },

    formatUtm: function(utm) {
      if (!utm || Object.keys(utm).length === 0) return 'Aucun';
      return Object.entries(utm)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ');
    },

    formatHttpStatus: function(status) {
      if (!status) return 'N/A';
      const statusClass = status === 200 ? 'text-green-600' : 'text-red-600';
      return `<span class="${statusClass}">${status}</span>`;
    },

    escapeHtml: function(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    log: function(message, type = 'info') {
      if (window.QRScanner.debug) {
        const prefix = {
          info: 'ℹ️',
          success: '✅',
          warning: '⚠️',
          error: '❌',
          debug: '🔍'
        }[type] || 'ℹ️';
        
        console.log(`${prefix} QR Scanner: ${message}`);
      }
    }
  },

  // Gestion des erreurs globales
  handleError: function(error, context = 'Unknown') {
    this.utils.log(`Erreur dans ${context}: ${error.message}`, 'error');
    console.error('Détails de l\'erreur:', error);
  }
};

// Gestionnaire d'erreurs global
window.addEventListener('error', function(event) {
  window.QRScanner.handleError(event.error, 'Global Error Handler');
});

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', function() {
  window.QRScanner.utils.log('Application QR Scanner initialisée', 'success');
  
  // Vérifier si nous sommes sur la page de résultats
  if (window.SCAN_CONFIG && window.SCAN_CONFIG.scanId) {
    window.QRScanner.utils.log(`Mode résultats activé pour scan: ${window.SCAN_CONFIG.scanId}`, 'info');
  }
});

console.log("📱 QR Scanner app.js chargé - Version", window.QRScanner.version);