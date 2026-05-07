// Search page specific functionality
let currentSearchType = 'all';
let searchDebounceTimer = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeSearchPage();
});

function initializeSearchPage() {
    const mainSearch = document.getElementById('mainSearch');
    const clearBtn = document.getElementById('clearSearch');
    const filterBtns = document.querySelectorAll('.filter-btn');
    
    if (mainSearch) {
        // Live search as user types
        mainSearch.addEventListener('input', function() {
            const query = this.value;
            
            if (clearBtn) {
                clearBtn.style.display = query ? 'block' : 'none';
            }
            
            if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                performSearch();
            }, 500);
        });
        
        // Handle enter key
        mainSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
                performSearch();
            }
        });
    }
    
    // Filter buttons
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentSearchType = this.dataset.type;
            performSearch();
        });
    });
    
    // Clear button
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            if (mainSearch) {
                mainSearch.value = '';
                this.style.display = 'none';
                performSearch();
            }
        });
    }
}

async function performSearch() {
    const searchInput = document.getElementById('mainSearch');
    const query = searchInput ? searchInput.value.trim() : '';
    
    if (!query) {
        // Show empty state
        const resultsGrid = document.getElementById('resultsGrid');
        if (resultsGrid) {
            resultsGrid.innerHTML = `
                <div class="empty-state-large">
                    <i class="fas fa-search"></i>
                    <h3>Start searching</h3>
                    <p>Enter a name, EPIC number, or house number to find voters</p>
                    <div class="example-searches">
                        <small>Try these examples:</small>
                        <button class="example-btn" onclick="searchExample('ram')">ram</button>
                        <button class="example-btn" onclick="searchExample('house:7')">house:7</button>
                        <button class="example-btn" onclick="searchExample('age:60')">age:60</button>
                    </div>
                </div>
            `;
        }
        return;
    }
    
    showLoading();
    
    try {
        const url = `/api/search?q=${encodeURIComponent(query)}&type=${currentSearchType}`;
        const response = await fetch(url);
        const data = await response.json();
        
        updateSearchResults(data.results, data.count);
    } catch (error) {
        console.error('Search error:', error);
        showNotification('Search failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

function updateSearchResults(results, count) {
    const resultsGrid = document.getElementById('resultsGrid');
    const resultCountSpan = document.getElementById('resultCount');
    
    if (resultCountSpan) {
        resultCountSpan.textContent = `${count} found`;
    }
    
    if (!resultsGrid) return;
    
    if (results.length === 0) {
        resultsGrid.innerHTML = `
            <div class="empty-state-large">
                <i class="fas fa-search"></i>
                <h3>No results found</h3>
                <p>Try different search terms or check your spelling</p>
                <div class="example-searches">
                    <small>Try searching by:</small>
                    <button class="example-btn" onclick="searchExample('राम')">Hindi name</button>
                    <button class="example-btn" onclick="searchExample('ZQU')">EPIC number</button>
                    <button class="example-btn" onclick="searchExample('house:7')">House number</button>
                </div>
            </div>
        `;
        return;
    }
    
    resultsGrid.innerHTML = results.map(voter => `
        <div class="voter-card" onclick="window.location.href='/voter/${voter.id}'">
            <div class="voter-card-header">
                <div class="voter-avatar-large">
                    <i class="fas fa-user-circle"></i>
                </div>
                <div class="voter-basic-info">
                    <h4>${escapeHtml(voter.name)}</h4>
                    <p class="voter-location">
                        <i class="fas fa-map-marker-alt"></i> ${escapeHtml(voter.village || 'N/A')}
                    </p>
                </div>
                <div class="document-badge">
                    <i class="fas fa-file-alt"></i> ${voter.doc_count || 0} docs
                </div>
            </div>
            
            <div class="voter-card-details">
                <div class="detail-item">
                    <i class="fas fa-id-card"></i>
                    <span>EPIC: ${escapeHtml(voter.epic || 'N/A')}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-home"></i>
                    <span>House: ${escapeHtml(voter.house_no || 'N/A')}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-users"></i>
                    <span>Relation: ${escapeHtml(voter.relation_name || 'N/A')}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-venus-mars"></i>
                    <span>${escapeHtml(voter.gender || 'N/A')}, Age ${voter.age || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-phone"></i>
                    <span>${escapeHtml(voter.mobile || 'N/A')}</span>
                </div>
            </div>
            
            <div class="voter-card-footer">
                <button class="btn-view" onclick="event.stopPropagation(); window.location.href='/voter/${voter.id}'">
                    View Full Profile <i class="fas fa-arrow-right"></i>
                </button>
            </div>
        </div>
    `).join('');
    
    // Add animation to new cards
    const cards = resultsGrid.querySelectorAll('.voter-card');
    cards.forEach((card, index) => {
        card.style.animation = `fadeInUp 0.3s ease ${index * 0.05}s both`;
    });
}

function searchExample(query) {
    const searchInput = document.getElementById('mainSearch');
    if (searchInput) {
        searchInput.value = query;
        performSearch();
    }
}

// Add fadeInUp animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);
