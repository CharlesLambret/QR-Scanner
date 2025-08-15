// Application JavaScript pour QR Scanner
console.log("QR Scanner app.js loaded");

// Fonction utilitaire pour formater les URLs
function formatUrl(url, maxLength = 50) {
    if (url.length > maxLength) {
        return url.substring(0, maxLength) + '...';
    }
    return url;
}

// Fonction pour formater les paramètres UTM
function formatUtm(utm) {
    if (!utm || Object.keys(utm).length === 0) return 'Aucun';
    return Object.entries(utm)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ');
}

// Fonction pour formater les statuts HTTP
function formatHttpStatus(status) {
    if (!status) return 'N/A';
    const statusClass = status === 200 ? 'text-green-600' : 'text-red-600';
    return `<span class="${statusClass}">${status}</span>`;
}

// Gestion des formulaires et interactions
document.addEventListener('DOMContentLoaded', function() {
    // Validation des formulaires
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const fileInput = this.querySelector('input[type="file"]');
            if (fileInput && !fileInput.files.length) {
                e.preventDefault();
                alert('Veuillez sélectionner un fichier PDF.');
                return false;
            }
        });
    });
    
    // Amélioration UX pour les inputs de fichier
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file && !file.name.toLowerCase().endsWith('.pdf')) {
                alert('Seuls les fichiers PDF sont acceptés.');
                this.value = '';
            }
        });
    });
});
