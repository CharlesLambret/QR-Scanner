/**
 * Composant de suivi de progression
 */
class ProgressTracker {
  constructor() {
    this.progressElement = document.getElementById("progress");
    this.statsElement = document.getElementById("stats");
    this.statsListElement = document.getElementById("stats-list");
    
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

  displayStats(stats) {
    if (!stats || !this.statsElement || !this.statsListElement) return;
    
    this.statsListElement.innerHTML = `
      <li>Pages totales : <strong>${stats.total_pages}</strong></li>
      <li>Pages avec QR codes : <strong>${stats.pages_with_qr}</strong></li>
      <li>URLs uniques trouvées : <strong>${stats.unique_urls}</strong></li>
      <li>Lignes de texte extraites : <strong>${stats.extracted_lines}</strong></li>
      ${stats.ai_extracted_items !== undefined ? `<li>Données IA extraites : <strong>${stats.ai_extracted_items}</strong></li>` : ''}
    `;
    
    this.statsElement.classList.remove("hidden");
    console.log("📊 Statistiques affichées:", stats);
  }

  showSuccessMessage() {
    const successDiv = document.createElement("div");
    successDiv.className = "bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mt-4";
    successDiv.innerHTML = "✅ Scan terminé avec succès !";
    document.querySelector("main").appendChild(successDiv);
    console.log("✅ Message de succès affiché");
  }
}