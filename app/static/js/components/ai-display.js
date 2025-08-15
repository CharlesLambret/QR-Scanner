/**
 * Composant d'affichage des extractions IA
 */
class AIDisplay {
  constructor() {
    this.aiExtractionsDiv = document.getElementById("ai-extractions");
    this.aiQueryText = document.getElementById("ai-query-text");
    this.aiMetadata = document.getElementById("ai-metadata");
    this.aiTableHeader = document.getElementById("ai-table-header");
    this.aiTableBody = document.getElementById("ai-table-body");
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
      const keywords = aiExtraction.keywords || [];
      this.aiQueryText.textContent = `Keywords sélectionnés: ${keywords.join(', ')}` || 'Non spécifiées';
    }
    
    // Afficher les métadonnées si disponibles
    this._displayMetadata(aiExtraction);
    
    // Créer le tableau dynamique basé sur les keywords
    this._createDynamicTable(aiExtraction.keywords || [], aiExtraction.extracted_data);
    
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

  _createDynamicTable(keywords, extractedData) {
    if (!this.aiTableHeader || !this.aiTableBody) return;
    
    // Nettoyer le tableau
    this.aiTableHeader.innerHTML = "";
    this.aiTableBody.innerHTML = "";
    
    if (!keywords || keywords.length === 0) {
      this.aiTableBody.innerHTML = '<tr><td colspan="100%" class="text-center text-gray-500 p-4">Aucun keyword sélectionné</td></tr>';
      return;
    }
    
    // Créer l'en-tête avec une colonne "Page" + une colonne par keyword
    const headerRow = document.createElement("tr");
    
    // Colonne Page
    const pageHeader = document.createElement("th");
    pageHeader.className = "border-b border-purple-200 px-3 py-2 text-left text-purple-800 bg-purple-100";
    pageHeader.textContent = "Page";
    headerRow.appendChild(pageHeader);
    
    // Une colonne par keyword
    keywords.forEach(keyword => {
      const keywordHeader = document.createElement("th");
      keywordHeader.className = "border-b border-purple-200 px-3 py-2 text-left text-purple-800 bg-purple-100";
      keywordHeader.innerHTML = this._getKeywordIcon(keyword) + " " + this._getKeywordDisplayName(keyword);
      headerRow.appendChild(keywordHeader);
    });
    
    this.aiTableHeader.appendChild(headerRow);
    
    // Organiser les données par page
    const dataByPage = this._organizeDataByPage(extractedData);
    
    // Créer les lignes de données
    Object.keys(dataByPage).sort((a, b) => parseInt(a) - parseInt(b)).forEach((pageNum, index) => {
      const pageData = dataByPage[pageNum];
      const row = document.createElement("tr");
      row.className = index % 2 === 0 ? "bg-white hover:bg-purple-25" : "bg-purple-25 hover:bg-purple-50";
      
      // Colonne Page
      const pageCell = document.createElement("td");
      pageCell.className = "border-b border-purple-100 px-3 py-2 text-center";
      pageCell.innerHTML = `<span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium">Page ${pageNum}</span>`;
      row.appendChild(pageCell);
      
      // Une colonne par keyword
      keywords.forEach(keyword => {
        const keywordCell = document.createElement("td");
        keywordCell.className = "border-b border-purple-100 px-3 py-2";
        
        const valuesForKeyword = this._getValuesForKeyword(pageData, keyword);
        if (valuesForKeyword.length > 0) {
          keywordCell.innerHTML = valuesForKeyword.map(value => 
            `<div class="mb-1 last:mb-0"><span class="inline-block bg-purple-50 text-purple-800 px-2 py-1 rounded text-sm">${this._escapeHtml(value)}</span></div>`
          ).join('');
        } else {
          keywordCell.innerHTML = '<span class="text-gray-400 text-sm italic">-</span>';
        }
        
        row.appendChild(keywordCell);
      });
      
      this.aiTableBody.appendChild(row);
    });
    
    console.log(`🤖 Tableau dynamique créé avec ${keywords.length} keywords et ${Object.keys(dataByPage).length} pages`);
  }

  _organizeDataByPage(extractedData) {
    const dataByPage = {};
    extractedData.forEach((item) => {
      const pageNumber = this._extractPageNumber(item);
      if (!dataByPage[pageNumber]) {
        dataByPage[pageNumber] = [];
      }
      dataByPage[pageNumber].push(item);
    });
    return dataByPage;
  }

  _getValuesForKeyword(pageData, keyword) {
    const values = [];
    pageData.forEach(item => {
      const extractionClass = item.extraction_class || item.type || '';
      // Correspondances entre keywords et extraction classes
      if (this._keywordMatchesExtraction(keyword, extractionClass)) {
        const text = item.text || item.extraction_text || '';
        if (text && !values.includes(text)) {
          values.push(text);
        }
      }
    });
    return values;
  }

  _keywordMatchesExtraction(keyword, extractionClass) {
    const mappings = {
      'nom': ['nom', 'client_name', 'name'],
      'prénom': ['prénom', 'prenom', 'first_name'],
      'civilité': ['civilité', 'civilite', 'title', 'civility'],
      'code': ['code', 'mailing_code', 'reference', 'identifier'],
      'email': ['email', 'mail'],
      'téléphone': ['téléphone', 'telephone', 'phone'],
      'date': ['date'],
      'montant': ['montant', 'amount', 'prix', 'price'],
      'adresse': ['adresse', 'address']
    };
    
    const possibleClasses = mappings[keyword.toLowerCase()] || [keyword.toLowerCase()];
    return possibleClasses.some(cls => extractionClass.toLowerCase().includes(cls));
  }

  _getKeywordIcon(keyword) {
    const icons = {
      'nom': '👤',
      'prénom': '👤',
      'civilité': '👔',
      'code': '🏷️',
      'email': '📧',
      'téléphone': '📞',
      'date': '📅',
      'montant': '💰',
      'adresse': '🏠'
    };
    return icons[keyword.toLowerCase()] || '📋';
  }

  _getKeywordDisplayName(keyword) {
    const displayNames = {
      'nom': 'Nom',
      'prénom': 'Prénom',
      'civilité': 'Civilité',
      'code': 'Code',
      'email': 'Email',
      'téléphone': 'Téléphone',
      'date': 'Date',
      'montant': 'Montant',
      'adresse': 'Adresse'
    };
    return displayNames[keyword.toLowerCase()] || keyword;
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