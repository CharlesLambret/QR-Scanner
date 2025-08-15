/**
 * Composant de suivi de progression
 */
class ProgressTracker {
  constructor() {
    this.progressElement = document.getElementById("progress");
    
    console.log("📊 ProgressTracker initialisé");
  }

  updateProgress(message) {
    if (this.progressElement) {
      this.progressElement.textContent = message;
      console.log("📊 Progression mise à jour:", message);
    }
  }

  hideProgress() {
    if (this.progressElement) {
      this.progressElement.style.display = "none";
      console.log("📊 Progression masquée");
    }
  }

  showError(errorMessage) {
    if (this.progressElement) {
      this.progressElement.innerHTML = `
        <span class="text-red-600">❌ Erreur pendant le scan: ${errorMessage}</span>
      `;
      this.progressElement.className = "bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4";
      console.log("❌ Erreur affichée:", errorMessage);
    }
  }


  showSuccessMessage() {
    const successDiv = document.createElement("div");
    successDiv.className = "bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mt-4";
    successDiv.innerHTML = "✅ Scan terminé avec succès !";
    document.querySelector("main").appendChild(successDiv);
    console.log("✅ Message de succès affiché");
  }
}