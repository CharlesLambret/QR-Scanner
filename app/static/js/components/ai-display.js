/**
 * Composant d'affichage des extractions IA
 */
class AIDisplay {
  constructor() {
    this.aiExtractionsDiv = document.getElementById("ai-extractions");
    this.aiQueryText = document.getElementById("ai-query-text");
    this.aiMetadata = document.getElementById("ai-metadata");
    this.aiTableBody = document.querySelector("#ai-results-table tbody");
    this.aiTotalExtractions = document.getElementById("ai-total-extractions");
    this.aiModelUsed = document.getElementById("ai-model-used");
    
    console.log("🤖 AIDisplay initialisé");
  }

  displayAIExtractions(aiExtraction) {
    console.log("🤖 Traitement des extractions IA...", aiExtraction);
    
    if (!aiExtraction || !aiExtraction.success) {
      if (aiExtraction && aiExtraction.error) {
        this._showAIError(aiExtraction.error);
      }
      return;
    }

    if (!aiExtraction.extracted_data || aiExtraction.extracted_data.length === 0) {
      this._showNoAIExtractions();
      return;
    }

    console.log("🤖 Affichage des extractions IA");
    
    // Afficher la requête
    if (this.aiQueryText) {
      this.aiQueryText.textContent = aiExtraction.query || 'Non spécifiée';
    }
    
    // Afficher les métadonnées si disponibles
    this._displayMetadata(aiExtraction);
    
    // Populer le tableau
    this._populateTable(aiExtraction.extracted_data);
    
    // Afficher la section
    if (this.aiExtractionsDiv) {
      this.aiExtractionsDiv.classList.remove("hidden");
    }
    
    console.log("🤖 Extractions IA affichées");
  }

  // Méthodes privées
  _displayMetadata(aiExtraction) {
    if (aiExtraction.total_extractions !== undefined && this.aiMetadata) {
      if (this.aiTotalExtractions) {
        this.aiTotalExtractions.textContent = aiExtraction.total_extractions;
      }
      if (this.aiModelUsed) {
        this.aiModelUsed.textContent = aiExtraction.model_used || 'gemini-2.5-flash';
      }
      this.aiMetadata.classList.remove("hidden");
    }
  }

  _populateTable(extractedData) {
    if (!this.aiTableBody) return;
    
    this.aiTableBody.innerHTML = "";
    
    extractedData.forEach((item, index) => {
      const tr = document.createElement("tr");
      tr.className = index % 2 === 0 ? "bg-white" : "bg-purple-25";
      
      // Badge pour le type/classe
      const typeClass = item.extraction_class || item.type || 'unknown';
      const typeBadge = `<span class="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded font-medium">${typeClass}</span>`;
      
      // Extraire le numéro de page
      let pageNumber = this._extractPageNumber(item);
      console.log(`🤖 Extraction ${item.id}: page=${pageNumber}, text="${item.text}"`);
      
      tr.innerHTML = `
        <td class="border-b border-purple-100 px-3 py-2 text-center font-medium">${item.id}</td>
        <td class="border-b border-purple-100 px-3 py-2">${typeBadge}</td>
        <td class="border-b border-purple-100 px-3 py-2">
          <span class="font-medium text-gray-800">${this._escapeHtml(item.text || item.extraction_text || '')}</span>
        </td>
        <td class="border-b border-purple-100 px-3 py-2 text-center">
          <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">${pageNumber}</span>
        </td>
      `;
      this.aiTableBody.appendChild(tr);
    });
  }

  _extractPageNumber(item) {
    if (item.page) {
      return item.page;
    } else if (item.attributes && item.attributes.page) {
      return item.attributes.page;
    } else if (item.source_location && item.source_location.page) {
      return item.source_location.page;
    }
    return 'N/A';
  }

  _showNoAIExtractions() {
    if (this.aiExtractionsDiv) {
      this.aiExtractionsDiv.innerHTML = `
        <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
          ⚠️ Aucune donnée correspondant à votre requête n'a été trouvée dans le PDF.
        </div>
      `;
      this.aiExtractionsDiv.classList.remove("hidden");
    }
  }

  _showAIError(error) {
    if (this.aiExtractionsDiv) {
      this.aiExtractionsDiv.innerHTML = `
        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          ❌ Erreur lors de l'extraction IA: ${this._escapeHtml(error)}
        </div>
      `;
      this.aiExtractionsDiv.classList.remove("hidden");
    }
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}