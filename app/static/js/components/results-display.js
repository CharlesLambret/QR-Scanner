/**
 * Composant d'affichage des résultats QR et extractions de texte
 */
class ResultsDisplay {
  constructor() {
    this.qrResultsSection = document.getElementById("qr-results-section");
    this.resultsTableBody = document.querySelector("#results-table tbody");
    this.extractionsDiv = document.getElementById("extractions");
    this.extractionsContent = document.getElementById("extractions-content");
    this.byPageSection = document.getElementById("by-page-section");
    this.byPageContent = document.getElementById("by-page-content");
    
    console.log("🔗 ResultsDisplay initialisé");
  }

  displayQRResults(urlResults) {
    if (!urlResults || urlResults.length === 0) {
      this._showNoQRMessage();
      return;
    }

    console.log("🔗 Affichage du tableau des QR codes");
    
    if (this.qrResultsSection) {
      this.qrResultsSection.classList.remove("hidden");
    }
    
    if (this.resultsTableBody) {
      this.resultsTableBody.innerHTML = "";
      
      urlResults.forEach((result) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="border px-4 py-2">${result.page}</td>
          <td class="border px-4 py-2">
            <a href="${result.url}" target="_blank" class="text-blue-600 hover:underline" title="${result.url}">
              ${this._formatUrl(result.url)}
            </a>
          </td>
          <td class="border px-4 py-2">
            <span class="${result.http_status === 200 ? 'text-green-600' : 'text-red-600'}">
              ${result.http_status || 'N/A'}
            </span>
          </td>
          <td class="border px-4 py-2 text-sm">${this._getValidationStatus(result.domain_valid)}</td>
          <td class="border px-4 py-2 text-sm">${this._getValidationStatus(result.utm_valid)}</td>
          <td class="border px-4 py-2 text-sm">${this._getValidationStatus(result.text_search_valid)}</td>
        `;
        this.resultsTableBody.appendChild(tr);
      });
    }
  }

  displayTextExtractions(extractions) {
    if (!extractions || extractions.length === 0) return;
    
    console.log("📝 Affichage des extractions de texte");
    
    if (this.extractionsContent) {
      this.extractionsContent.innerHTML = extractions
        .map(ext => `<div class="mb-1"><strong>Page ${ext.page}:</strong> ${this._escapeHtml(ext.line)}</div>`)
        .join("");
    }
    
    if (this.extractionsDiv) {
      this.extractionsDiv.classList.remove("hidden");
    }
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

  displayStats(stats) {
    if (!stats) return;
    
    console.log("📊 Affichage des statistiques");
    
    const statsElement = document.getElementById("stats");
    const statsListElement = document.getElementById("stats-list");
    
    if (statsElement && statsListElement) {
      // Créer la liste des statistiques
      const statsList = [
        `Pages totales: ${stats.total_pages || 0}`,
        `Pages avec QR: ${stats.pages_with_qr || 0}`,
        `URLs trouvées: ${stats.total_qr_found || 0}`,
        `URLs uniques: ${stats.unique_urls || 0}`,
        `Extractions texte: ${stats.text_extractions || 0}`,
        `Extractions IA: ${stats.ai_extractions || 0}`,
        `Requêtes HTTP réussies: ${stats.http_success || 0}`,
        `Temps de réponse moyen: ${stats.avg_response_time || 0}ms`
      ];
      
      statsListElement.innerHTML = statsList
        .map(stat => `<li>${stat}</li>`)
        .join("");
      
      statsElement.classList.remove("hidden");
    }
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

  _formatUrl(url, maxLength = 50) {
    if (url.length > maxLength) {
      return url.substring(0, maxLength) + '...';
    }
    return url;
  }

  _getValidationStatus(validationResult) {
    if (validationResult === null || validationResult === undefined) {
      return '<span class="text-gray-500">Non testé</span>';
    } else if (validationResult === true) {
      return '<span class="text-green-600 font-semibold">✓ Valide</span>';
    } else {
      return '<span class="text-red-600 font-semibold">✗ Invalide</span>';
    }
  }

  _showNoQRMessage() {
    const noResultsDiv = document.createElement("div");
    noResultsDiv.className = "bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4";
    noResultsDiv.innerHTML = "⚠️ Aucun QR code avec URL détecté dans ce PDF.";
    
    const statsElement = document.getElementById("stats");
    if (statsElement) {
      statsElement.after(noResultsDiv);
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
            ${this._escapeHtml(extraction.text || extraction.extraction_text || '')}
          </div>
        </div>
      `;
    });
    
    return section + `</div>`;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}