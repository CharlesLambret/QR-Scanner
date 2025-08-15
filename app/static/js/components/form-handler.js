/**
 * Gestionnaire de formulaire pour la page d'accueil
 */
class FormHandler {
  constructor() {
    this.init();
    console.log("📝 FormHandler initialisé");
  }

  init() {
    document.addEventListener('DOMContentLoaded', () => {
      this.setupFormValidation();
      this.setupFileInputValidation();
    });
  }

  setupFormValidation() {
    const form = document.getElementById('scan-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      const fileInput = form.querySelector('input[type="file"]');
      
      if (fileInput && !fileInput.files.length) {
        e.preventDefault();
        this.showError('Veuillez sélectionner un fichier PDF.');
        return false;
      }

      // Validation additionnelle pour les champs spécialisés
      if (!this.validateAdvancedFields(form)) {
        e.preventDefault();
        return false;
      }

      // Afficher un indicateur de chargement
      this.showSubmittingState(form);
    });
  }

  setupFileInputValidation() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
      input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        
        if (file && !file.name.toLowerCase().endsWith('.pdf')) {
          this.showError('Seuls les fichiers PDF sont acceptés.');
          e.target.value = '';
          return;
        }

        if (file) {
          this.showFileInfo(file);
        }
      });
    });
  }

  validateAdvancedFields(form) {
    // Validation des domaines autorisés
    const domainsInput = form.querySelector('input[name="expected_domains"]');
    if (domainsInput && domainsInput.value) {
      const domains = domainsInput.value.split(',').map(d => d.trim());
      for (const domain of domains) {
        if (!this.isValidDomain(domain)) {
          this.showError(`Domaine invalide: ${domain}`);
          return false;
        }
      }
    }

    // Validation des paramètres UTM
    const utmInput = form.querySelector('input[name="expected_utm_params"]');
    if (utmInput && utmInput.value) {
      if (!this.isValidUTMFormat(utmInput.value)) {
        this.showError('Format des paramètres UTM invalide. Utilisez: clé=valeur;clé2=valeur2');
        return false;
      }
    }

    return true;
  }

  isValidDomain(domain) {
    // Regex simple pour valider un nom de domaine
    const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])*$/;
    return domainRegex.test(domain);
  }

  isValidUTMFormat(utmString) {
    // Vérifier le format clé=valeur;clé2=valeur2
    const params = utmString.split(';');
    for (const param of params) {
      if (!param.includes('=') || param.split('=').length !== 2) {
        return false;
      }
    }
    return true;
  }

  showFileInfo(file) {
    // Afficher des informations sur le fichier sélectionné
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    console.log(`📁 Fichier sélectionné: ${file.name} (${sizeInMB} MB)`);
    
    // Optionnel: afficher dans l'interface
    this.showInfo(`Fichier sélectionné: ${file.name} (${sizeInMB} MB)`);
  }

  showSubmittingState(form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = '⏳ Traitement en cours...';
      submitButton.className = submitButton.className.replace('bg-blue-600 hover:bg-blue-700', 'bg-gray-400 cursor-not-allowed');
    }
  }

  showError(message) {
    this.showNotification(message, 'error');
  }

  showInfo(message) {
    this.showNotification(message, 'info');
  }

  showNotification(message, type = 'info') {
    // Supprimer les notifications existantes
    const existingNotifications = document.querySelectorAll('.form-notification');
    existingNotifications.forEach(notification => notification.remove());

    const notification = document.createElement('div');
    notification.className = `form-notification px-4 py-3 rounded mb-4 ${
      type === 'error' 
        ? 'bg-red-100 border border-red-400 text-red-700'
        : 'bg-blue-100 border border-blue-400 text-blue-700'
    }`;
    notification.textContent = message;

    // Insérer au début du contenu principal
    const main = document.querySelector('main');
    if (main && main.firstChild) {
      main.insertBefore(notification, main.firstChild);
    }

    // Auto-suppression après 5 secondes pour les infos
    if (type === 'info') {
      setTimeout(() => {
        if (notification.parentNode) {
          notification.remove();
        }
      }, 5000);
    }
  }
}

// Initialisation automatique
new FormHandler();