/**
 * Composant d'affichage des résultats par page
 */
class ResultsDisplay {
  constructor() {
    this.byPageSection = document.getElementById("by-page-section");
    this.byPageContent = document.getElementById("by-page-content");
    
    console.log("🔗 ResultsDisplay initialisé");
  }


  displayByPageSection(urlResults, aiExtraction) {
    console.log("📑 Création de la section par page...");
    
    // Organiser les données par page
    const pageData = this._organizeDataByPage(urlResults, aiExtraction);
    
    // Si aucune donnée, ne pas afficher la section
    if (Object.keys(pageData).length === 0) {
      return;
    }
    
    if (this.byPageContent) {
      this.byPageContent.innerHTML = "";
      
      // Créer les cartes pour chaque page
      Object.keys(pageData).sort((a, b) => parseInt(a) - parseInt(b)).forEach(pageNum => {
        const data = pageData[pageNum];
        const card = this._createPageCard(pageNum, data);
        this.byPageContent.appendChild(card);
      });
    }
    
    if (this.byPageSection) {
      this.byPageSection.classList.remove("hidden");
    }
    
    console.log("📑 Section par page affichée");
  }


  showSuccessMessage() {
    console.log("✅ Affichage du message de succès");
    
    const successMessage = document.createElement("div");
    successMessage.className = "bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4";
    successMessage.innerHTML = "✅ <strong>Scan terminé avec succès !</strong> Tous les QR codes ont été traités.";
    
    const statsElement = document.getElementById("stats");
    if (statsElement) {
      statsElement.after(successMessage);
    }
  }


  _organizeDataByPage(urlResults, aiExtraction) {
    const pageData = {};
    
    // Ajouter les QR codes
    if (urlResults) {
      urlResults.forEach(result => {
        if (!pageData[result.page]) {
          pageData[result.page] = { qrCodes: [], aiExtractions: [] };
        }
        pageData[result.page].qrCodes.push(result);
      });
    }
    
    // Ajouter les extractions IA
    if (aiExtraction && aiExtraction.success && aiExtraction.extracted_data) {
      console.log("📑 Traitement des extractions IA pour section par page...");
      aiExtraction.extracted_data.forEach(item => {
        let pageNumber = this._extractPageNumber(item);
        
        if (pageNumber !== 'unknown') {
          if (!pageData[pageNumber]) {
            pageData[pageNumber] = { qrCodes: [], aiExtractions: [] };
          }
          pageData[pageNumber].aiExtractions.push(item);
          console.log(`📑 ✅ Extraction ajoutée à la page ${pageNumber}`);
        } else {
          console.log(`📑 ❌ Extraction ignorée (pas de page): "${item.text}"`);
        }
      });
    }
    
    return pageData;
  }

  _extractPageNumber(item) {
    if (item.page) {
      return item.page;
    } else if (item.attributes && item.attributes.page) {
      return item.attributes.page;
    } else if (item.source_location && item.source_location.page) {
      return item.source_location.page;
    }
    return 'unknown';
  }

  _createPageCard(pageNum, data) {
    const card = document.createElement("div");
    card.className = "bg-white border-2 border-gray-200 rounded-lg p-4 min-w-80 flex-shrink-0";
    
    let cardContent = `
      <h4 class="text-lg font-bold mb-3 text-gray-800 border-b pb-2">
        📄 Page ${pageNum}
      </h4>
    `;
    
    // Ajouter les QR codes
    if (data.qrCodes.length > 0) {
      cardContent += this._createQRCodeSection(data.qrCodes);
    }
    
    // Ajouter les extractions IA
    if (data.aiExtractions.length > 0) {
      cardContent += this._createAIExtractionsSection(data.aiExtractions);
    }
    
    card.innerHTML = cardContent;
    return card;
  }

  _createQRCodeSection(qrCodes) {
    let section = `<div class="mb-4">
      <h5 class="font-semibold text-blue-800 mb-2 flex items-center gap-1">
        🔗 QR Code${qrCodes.length > 1 ? 's' : ''}
      </h5>`;
    
    qrCodes.forEach(qr => {
      const getValidationIcon = (valid) => {
        if (valid === true) return '✅';
        if (valid === false) return '❌';
        return '❓';
      };
      
      section += `
        <div class="bg-blue-50 border border-blue-200 rounded p-3 mb-2">
          <div class="mb-2">
            <a href="${qr.url}" target="_blank" class="text-blue-600 hover:underline font-medium break-all">
              ${qr.url}
            </a>
          </div>
          <div class="text-sm space-y-1">
            <div><strong>Status HTTP:</strong> 
              <span class="${qr.http_status === 200 ? 'text-green-600' : 'text-red-600'}">
                ${qr.http_status || 'N/A'}
              </span>
            </div>
            <div class="flex gap-4 text-xs">
              <span>Domaine: ${getValidationIcon(qr.domain_valid)}</span>
              <span>UTM: ${getValidationIcon(qr.utm_valid)}</span>
              <span>Texte: ${getValidationIcon(qr.text_search_valid)}</span>
            </div>
          </div>
        </div>
      `;
    });
    
    return section + `</div>`;
  }

  _createAIExtractionsSection(aiExtractions) {
    let section = `<div>
      <h5 class="font-semibold text-purple-800 mb-2 flex items-center gap-1">
        ✨ Extractions IA
      </h5>`;
    
    aiExtractions.forEach(extraction => {
      const typeClass = extraction.extraction_class || extraction.type || 'unknown';
      section += `
        <div class="bg-purple-50 border border-purple-200 rounded p-2 mb-2">
          <div class="flex items-center gap-2 mb-1">
            <span class="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded font-medium">
              ${typeClass}
            </span>
          </div>
          <div class="font-medium text-gray-800">
            ${this._escapeHtml(this._getDisplayText(extraction))}
          </div>
        </div>
      `;
    });
    
    return section + `</div>`;
  }

  _getDisplayText(extraction) {
    // For code extractions, prioritize the extracted_base if available
    if (extraction.extraction_class === 'code' && 
        extraction.attributes && 
        extraction.attributes.extracted_base) {
      return extraction.attributes.extracted_base;
    }
    
    // Fallback to the original text
    return extraction.text || extraction.extraction_text || '';
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}