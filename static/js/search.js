// ================================
// SEARCH PAGE FUNCTIONALITY
// Fully Safe Frontend Version
// No collision with main.js
// Backend Safe
// Flask Safe
// ================================

// ------------------------------
// Global Variables
// ------------------------------
let currentSearchType = 'all';
let searchDebounceTimer = null;
let currentSearchController = null;

// ------------------------------
// Initialize Search Page
// ------------------------------
document.addEventListener('DOMContentLoaded', function () {

    initializeSearchPage();

});

// ------------------------------
// Safe Helper Functions
// ------------------------------
function searchEscapeHtml(text) {

    if (text === null || text === undefined) {
        return '';
    }

    const div = document.createElement('div');

    div.textContent = String(text);

    return div.innerHTML;
}

// ------------------------------
// Loading Functions
// ------------------------------
function searchShowLoading() {

    document.body.classList.add('search-loading');
}

function searchHideLoading() {

    document.body.classList.remove('search-loading');
}

// ------------------------------
// Notification Function
// ------------------------------
function searchShowNotification(message, type = 'info') {
    
    if (typeof showNotification === 'function') {
        
        showNotification(message, type);
        
    } else {
        
        console.log(`[${type}] ${message}`);
    }
}

// ------------------------------
// Search Page Initialization
// ------------------------------
function initializeSearchPage() {

    const mainSearch =
        document.getElementById('mainSearch');

    const clearBtn =
        document.getElementById('clearSearch');

    const filterBtns =
        document.querySelectorAll('.filter-btn');

    // --------------------------
    // Main Search Input
    // --------------------------
    if (mainSearch) {

        // Live Search
        mainSearch.addEventListener('input', function () {

            const query = this.value;

            // Show/Hide Clear Button
            if (clearBtn) {

                clearBtn.style.display =
                    query ? 'flex' : 'none';
            }

            // Debounce Search
            if (searchDebounceTimer) {

                clearTimeout(searchDebounceTimer);
            }

            searchDebounceTimer = setTimeout(() => {

                performSearch();

            }, 500);
        });

        // Enter Key Search
        mainSearch.addEventListener('keypress', function (e) {

            if (e.key === 'Enter') {

                if (searchDebounceTimer) {

                    clearTimeout(searchDebounceTimer);
                }

                performSearch();
            }
        });
    }

    // --------------------------
    // Filter Buttons
    // --------------------------
    filterBtns.forEach(btn => {

        btn.addEventListener('click', function () {

            filterBtns.forEach(b => {

                b.classList.remove('active');
            });

            this.classList.add('active');

            currentSearchType =
                this.dataset.type;

            performSearch();
        });
    });

    // --------------------------
    // Clear Search Button
    // --------------------------
    if (clearBtn) {

        clearBtn.addEventListener('click', function () {

            if (mainSearch) {

                mainSearch.value = '';

                this.style.display = 'none';

                performSearch();
            }
        });
    }
}

// ------------------------------
// Main Search Function
// ------------------------------
async function performSearch() {

    const searchInput =
        document.getElementById('mainSearch');

    const query = searchInput
        ? searchInput.value.trim()
        : '';

    // --------------------------
    // Empty Search State
    // --------------------------
    if (!query) {

        const resultsGrid =
            document.getElementById('resultsGrid');

        const resultCountSpan =
            document.getElementById('resultCount');

        if (resultCountSpan) {

            resultCountSpan.textContent = '0 found';
        }

        if (resultsGrid) {

            resultsGrid.innerHTML = `
                <div class="empty-state-large">

                    <i class="fas fa-search"></i>

                    <h3>Start searching</h3>

                    <p>
                        Enter a name,
                        EPIC number,
                        or house number
                        to find voters
                    </p>

                    <div class="example-searches">

                        <small>Try examples:</small>

                        <button class="example-btn"
                            onclick="searchExample('ram')">
                            ram
                        </button>

                        <button class="example-btn"
                            onclick="searchExample('house:7')">
                            house:7
                        </button>

                        <button class="example-btn"
                            onclick="searchExample('age:60')">
                            age:60
                        </button>

                    </div>

                </div>
            `;
        }

        return;
    }

    // --------------------------
    // Prevent Tiny Queries
    // --------------------------
    if (query.length === 1) {

        return;
    }

    // --------------------------
    // Show Loader
    // --------------------------
    searchShowLoading();

    try {

        // Cancel Previous Search
        if (currentSearchController) {

            currentSearchController.abort();
        }

        currentSearchController =
            new AbortController();

        const url =
            `/api/search?q=${encodeURIComponent(query)}&type=${currentSearchType}`;

        const response = await fetch(url, {

            signal:
                currentSearchController.signal
        });

        if (!response.ok) {

            throw new Error('Search request failed');
        }

        const data =
            await response.json();

        updateSearchResults(

            data.results || [],
            data.count || 0
        );

    } catch (error) {

        // Ignore Abort Errors
        if (error.name === 'AbortError') {

            return;
        }

        console.error('Search error:', error);

        searchShowNotification(

            'Search failed. Please try again.',
            'error'
        );

    } finally {

        searchHideLoading();
    }
}

// ------------------------------
// Update Search Results
// ------------------------------
function updateSearchResults(results, count) {

    const resultsGrid =
        document.getElementById('resultsGrid');

    const resultCountSpan =
        document.getElementById('resultCount');

    if (resultCountSpan) {

        resultCountSpan.textContent =
            `${count} found`;
    }

    if (!resultsGrid) return;

    // --------------------------
    // Empty Result State
    // --------------------------
    if (!results || results.length === 0) {

        resultsGrid.innerHTML = `
            <div class="empty-state-large">

                <i class="fas fa-search"></i>

                <h3>No results found</h3>

                <p>
                    Try different keywords
                    or check spelling
                </p>

                <div class="example-searches">

                    <small>Try:</small>

                    <button class="example-btn"
                        onclick="searchExample('राम')">
                        Hindi Name
                    </button>

                    <button class="example-btn"
                        onclick="searchExample('ZQU')">
                        EPIC
                    </button>

                    <button class="example-btn"
                        onclick="searchExample('house:7')">
                        House No
                    </button>

                </div>

            </div>
        `;

        return;
    }

    // --------------------------
    // Render Cards
    // --------------------------
    resultsGrid.innerHTML =
        (results || []).map(voter => `

        <div class="voter-card"
            onclick="window.location.href='/voter/${voter.id}'">

            <div class="voter-card-header">

                <div class="voter-avatar-large">

                    <i class="fas fa-user-circle"></i>

                </div>

                <div class="voter-basic-info">

                    <h4>
                        ${searchEscapeHtml(voter.name)}
                    </h4>

                    <p class="voter-location">

                        <i class="fas fa-map-marker-alt"></i>

                        ${searchEscapeHtml(voter.village || 'N/A')}

                    </p>

                </div>

                <div class="document-badge">

                    <i class="fas fa-file-alt"></i>

                    ${searchEscapeHtml(voter.doc_count || 0)} docs

                </div>

            </div>

            <div class="voter-card-details">

                <div class="detail-item">

                    <i class="fas fa-id-card"></i>

                    <span>
                        EPIC:
                        ${searchEscapeHtml(voter.epic || 'N/A')}
                    </span>

                </div>

                <div class="detail-item">

                    <i class="fas fa-home"></i>

                    <span>
                        House:
                        ${searchEscapeHtml(voter.house_no || 'N/A')}
                    </span>

                </div>

                <div class="detail-item">

                    <i class="fas fa-users"></i>

                    <span>
                        Relation:
                        ${searchEscapeHtml(voter.relation_name || 'N/A')}
                    </span>

                </div>

                <div class="detail-item">

                    <i class="fas fa-venus-mars"></i>

                    <span>
                        ${searchEscapeHtml(voter.gender || 'N/A')},
                        Age ${searchEscapeHtml(voter.age || 'N/A')}
                    </span>

                </div>

                <div class="detail-item">

                    <i class="fas fa-phone"></i>

                    <span>
                        ${searchEscapeHtml(voter.mobile || 'N/A')}
                    </span>

                </div>

            </div>

            <div class="voter-card-footer">

                <button class="btn-view"

                    onclick="
                        event.stopPropagation();
                        window.location.href='/voter/${voter.id}'
                    ">

                    View Full Profile

                    <i class="fas fa-arrow-right"></i>

                </button>

            </div>

        </div>

    `).join('');

    // --------------------------
    // Card Animation
    // --------------------------
    const cards =
        resultsGrid.querySelectorAll('.voter-card');

    cards.forEach((card, index) => {

        card.style.animation =
            `fadeInUp 0.3s ease ${index * 0.05}s both`;
    });
}

// ------------------------------
// Example Search Helper
// ------------------------------
function searchExample(query) {

    const searchInput =
        document.getElementById('mainSearch');

    if (searchInput) {

        searchInput.value = query;

        performSearch();
    }
}

// ------------------------------
// Dynamic Styles
// ------------------------------
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

.search-loading {
    cursor: wait;
}

.search-loading #mainSearch {
    opacity: 0.7;
}

.search-filters {
    overflow-x: auto;
    scrollbar-width: none;
}

.search-filters::-webkit-scrollbar {
    display: none;
}

`;

document.head.appendChild(style);