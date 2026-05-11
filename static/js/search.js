// ========================================
// SEARCH PAGE SCRIPT
// Professional Search Engine
// ========================================

let searchState = {
    currentQuery: '',
    currentPage: 1,
    resultsPerPage: 20,
    totalResults: 0,
    isSearching: false,
    searchType: 'all',
    abortController: null
};

let searchEventListeners = new Map();

document.addEventListener('DOMContentLoaded', () => {
    initializeSearchPage();
});

function initializeSearchPage() {
    const mainSearch = document.getElementById('mainSearch');
    const clearBtn = document.getElementById('clearSearch');
    const filterBtns = document.querySelectorAll('.filter-btn');
    
    if (!mainSearch) return;
    
    // Remove old listeners
    if (searchEventListeners.has('mainSearch')) {
        mainSearch.removeEventListener('input', searchEventListeners.get('mainSearch'));
    }
    if (searchEventListeners.has('clearBtn') && clearBtn) {
        clearBtn.removeEventListener('click', searchEventListeners.get('clearBtn'));
    }
    
    // Search input listener
    const inputHandler = debounceSearch(function() {
        const query = mainSearch.value.trim();
        
        if (clearBtn) {
            clearBtn.style.display = query ? 'flex' : 'none';
        }
        
        if (query.length < 2) {
            resetSearchResults();
            return;
        }
        
        searchState.currentQuery = query;
        searchState.currentPage = 1;
        performSearch(query);
    }, 300);
    
    mainSearch.addEventListener('input', inputHandler);
    searchEventListeners.set('mainSearch', inputHandler);
    
    // Enter key
    mainSearch.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = mainSearch.value.trim();
            if (query.length >= 2) {
                performSearch(query);
            }
        }
    });
    
    // Clear button
    if (clearBtn) {
        const clearHandler = () => {
            mainSearch.value = '';
            clearBtn.style.display = 'none';
            resetSearchResults();
            mainSearch.focus();
        };
        clearBtn.addEventListener('click', clearHandler);
        searchEventListeners.set('clearBtn', clearHandler);
    }
    
    // Filter buttons
    filterBtns.forEach(btn => {
        if (searchEventListeners.has(btn)) {
            btn.removeEventListener('click', searchEventListeners.get(btn));
        }
        
        const filterHandler = () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            searchState.searchType = btn.dataset.type || 'all';
            searchState.currentPage = 1;
            
            const query = mainSearch.value.trim();
            if (query.length >= 2) {
                performSearch(query);
            }
        };
        
        btn.addEventListener('click', filterHandler);
        searchEventListeners.set(btn, filterHandler);
    });
    
    // Restore search if query exists
    const params = new URLSearchParams(window.location.search);
    const queryParam = params.get('q');
    if (queryParam) {
        mainSearch.value = queryParam;
        performSearch(queryParam);
    }
}

async function performSearch(query) {
    if (searchState.isSearching) return;
    if (!query || query.length < 2) {
        resetSearchResults();
        return;
    }
    
    const resultsGrid = document.getElementById('resultsGrid');
    const resultCount = document.getElementById('resultCount');
    
    if (!resultsGrid) return;
    
    searchState.isSearching = true;
    showSearchLoading();
    
    try {
        // Abort previous request
        if (searchState.abortController) {
            searchState.abortController.abort();
        }
        
        searchState.abortController = new AbortController();
        
        const params = new URLSearchParams({
            q: query,
            type: searchState.searchType,
            limit: searchState.resultsPerPage
        });
        
        const startTime = performance.now();
        
        const response = await fetch(`/api/search?${params.toString()}`, {
            signal: searchState.abortController.signal
        });
        
        const endTime = performance.now();
        const responseTime = ((endTime - startTime) / 1000).toFixed(2);
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        const results = data.results || [];
        const count = data.count || 0;
        
        searchState.totalResults = count;
        
        // Update result count
        if (resultCount) {
            resultCount.innerHTML = `
                <span>${count} result${count !== 1 ? 's' : ''} found</span>
                <span style="font-size: 12px; color: var(--text-secondary);">${responseTime}s</span>
            `;
        }
        
        if (results.length === 0) {
            resultsGrid.innerHTML = `
                <div style="grid-column: 1 / -1;">
                    <div class="empty-state">
                        <i class="fas fa-search"></i>
                        <h3>No Results Found</h3>
                        <p>Try different keywords or check your search terms</p>
                    </div>
                </div>
            `;
        } else {
            displaySearchResults(results);
        }
        
        // Update URL
        window.history.replaceState({}, '', `/search?q=${encodeURIComponent(query)}`);
        
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Search error:', error);
            resultsGrid.innerHTML = `
                <div style="grid-column: 1 / -1;">
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <h3>Search Error</h3>
                        <p>${error.message}</p>
                    </div>
                </div>
            `;
        }
    } finally {
        searchState.isSearching = false;
    }
}

function displaySearchResults(results) {
    const resultsGrid = document.getElementById('resultsGrid');
    if (!resultsGrid) return;
    
    resultsGrid.innerHTML = results.map(voter => `
        <div class="voter-card fade-in" onclick="window.location.href='/voter/${voter.id}'">
            <div class="voter-card-header">
                <div class="voter-card-avatar">${getInitials(voter.name)}</div>
                <div class="voter-card-name">${escapeHtml(voter.name || 'N/A')}</div>
                <div class="voter-card-epic">${voter.epic ? 'EPIC: ' + escapeHtml(voter.epic) : 'No EPIC'}</div>
            </div>
            <div class="voter-card-body">
                <div class="voter-card-info">
                    ${voter.house_no ? `
                        <div class="voter-card-info-item">
                            <span class="voter-card-info-label">House:</span>
                            <span>${escapeHtml(voter.house_no)}</span>
                        </div>
                    ` : ''}
                    ${voter.age ? `
                        <div class="voter-card-info-item">
                            <span class="voter-card-info-label">Age:</span>
                            <span>${voter.age} years</span>
                        </div>
                    ` : ''}
                    ${voter.mobile ? `
                        <div class="voter-card-info-item">
                            <span class="voter-card-info-label">Mobile:</span>
                            <span>${escapeHtml(voter.mobile)}</span>
                        </div>
                    ` : ''}
                    ${voter.village ? `
                        <div class="voter-card-info-item">
                            <span class="voter-card-info-label">Village:</span>
                            <span>${escapeHtml(voter.village)}</span>
                        </div>
                    ` : ''}
                    ${voter.gender ? `
                        <div class="voter-card-info-item">
                            <span class="voter-card-info-label">Gender:</span>
                            <span>${voter.gender}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
            <div class="voter-card-footer">
                <button class="btn btn-primary" onclick="event.stopPropagation(); window.location.href='/voter/${voter.id}'">
                    <i class="fas fa-eye"></i> View Profile
                </button>
                ${voter.doc_count > 0 ? `
                    <button class="btn btn-secondary" onclick="event.stopPropagation(); showDocs(${voter.id})">
                        <i class="fas fa-file"></i> ${voter.doc_count} Doc${voter.doc_count !== 1 ? 's' : ''}
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function showSearchLoading() {
    const resultsGrid = document.getElementById('resultsGrid');
    if (resultsGrid) {
        resultsGrid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <div class="loader" style="margin: 0 auto 20px;"></div>
                <p style="color: var(--text-secondary);">Searching...</p>
            </div>
        `;
    }
}

function resetSearchResults() {
    const resultsGrid = document.getElementById('resultsGrid');
    const resultCount = document.getElementById('resultCount');
    
    if (resultsGrid) {
        resultsGrid.innerHTML = `
            <div style="grid-column: 1 / -1;">
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h3>Start Searching</h3>
                    <p>Enter at least 2 characters to search for voters</p>
                </div>
            </div>
        `;
    }
    
    if (resultCount) {
        resultCount.textContent = '0 results';
    }
}

// ========================================
// UTILITIES
// ========================================

function debounceSearch(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function getInitials(name) {
    if (!name) return '?';
    return name
        .split(' ')
        .slice(0, 2)
        .map(word => word[0])
        .join('')
        .toUpperCase()
        .substring(0, 2);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showDocs(voterId) {
    // Implementation for showing documents
    console.log('Show documents for voter', voterId);
}
