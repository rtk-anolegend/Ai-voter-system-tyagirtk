// ======================================
// SEARCH PAGE SCRIPT
// STABLE FINAL VERSION
// ======================================

// --------------------------------------
// GLOBALS
// --------------------------------------

let currentSearchType = 'all';

let searchTimer = null;

let currentController = null;

// --------------------------------------
// INIT
// --------------------------------------

document.addEventListener('DOMContentLoaded', () => {

    initializeSearchPage();
});

// --------------------------------------
// INIT SEARCH PAGE
// --------------------------------------

function initializeSearchPage() {

    const searchInput =
        document.getElementById('mainSearch');

    const clearBtn =
        document.getElementById('clearSearch');

    const filterBtns =
        document.querySelectorAll('.filter-btn');

    if (!searchInput) return;

    // SEARCH INPUT
    searchInput.addEventListener('input', function () {

        const query =
            this.value.trim();

        // CLEAR BTN
        if (clearBtn) {

            clearBtn.style.display =
                query ? 'flex' : 'none';
        }

        // SMALL QUERY
        if (query.length < 2) {

            resetSearchResults();

            return;
        }

        // DEBOUNCE
        clearTimeout(searchTimer);

        searchTimer =
            setTimeout(() => {

                performSearch(query);

            }, 400);
    });

    // ENTER KEY
    searchInput.addEventListener('keydown', function (e) {

        if (e.key === 'Enter') {

            e.preventDefault();

            const query =
                this.value.trim();

            if (query.length >= 2) {

                performSearch(query);
            }
        }
    });

    // FILTERS
    filterBtns.forEach(btn => {

        btn.addEventListener('click', function () {

            filterBtns.forEach(b => {

                b.classList.remove('active');
            });

            this.classList.add('active');

            currentSearchType =
                this.dataset.type || 'all';

            const query =
                searchInput.value.trim();

            if (query.length >= 2) {

                performSearch(query);
            }
        });
    });

    // CLEAR BTN
    if (clearBtn) {

        clearBtn.addEventListener('click', () => {

            searchInput.value = '';

            clearBtn.style.display = 'none';

            resetSearchResults();

            searchInput.focus();
        });
    }

    
}

// --------------------------------------
// MAIN SEARCH
// --------------------------------------

async function performSearch(query) {

    const resultsGrid =
        document.getElementById('resultsGrid');

    const resultCount =
        document.getElementById('resultCount');

    if (!resultsGrid) return;

    showSearchLoading();

    try {

        // CANCEL OLD
        if (currentController) {

            currentController.abort();
        }

        currentController =
            new AbortController();

        const response =
            await fetch(

                `/api/search?q=${encodeURIComponent(query)}&type=${currentSearchType}`,

                {
                    signal:
                        currentController.signal
                }
            );

        if (!response.ok) {

            throw new Error('Search failed');
        }

        const data =
            await response.json();

        const results =
            data.results || [];

        const count =
            data.count || 0;

        // COUNT
        if (resultCount) {

            resultCount.textContent =
                `${count} found`;
        }

        // EMPTY
        if (results.length === 0) {

            resultsGrid.innerHTML = `

                <div class="empty-state-large">

                    <i class="fas fa-search"></i>

                    <h3>No voters found</h3>

                    <p>
                        Try another keyword
                    </p>

                </div>
            `;

            return;
        }

        // RESULTS
        resultsGrid.innerHTML =

            results.map(voter => `

                <div class="voter-card">

                    <div class="voter-card-inner"

                        onclick="
                            window.location.href='/voter/${voter.id}'
                        ">

                        <div class="voter-card-header">

                            <div class="voter-avatar-large">

                                <i class="fas fa-user-circle"></i>

                            </div>

                            <div class="voter-basic-info">

                                <h4>
                                    ${escapeSearchHtml(voter.name)}
                                </h4>

                                <p>

                                    EPIC:
                                    ${escapeSearchHtml(voter.epic || 'N/A')}

                                </p>

                            </div>

                        </div>

                        <div class="voter-card-details">

                            <div class="detail-item">

                                <i class="fas fa-home"></i>

                                <span>

                                    House:
                                    ${escapeSearchHtml(voter.house_no || 'N/A')}

                                </span>

                            </div>

                            <div class="detail-item">

                                <i class="fas fa-users"></i>

                                <span>

                                    ${escapeSearchHtml(voter.relation_name || 'N/A')}

                                </span>

                            </div>

                            <div class="detail-item">

                                <i class="fas fa-venus-mars"></i>

                                <span>

                                    ${escapeSearchHtml(voter.gender || 'N/A')}
                                    |
                                    Age ${escapeSearchHtml(voter.age || 'N/A')}

                                </span>

                            </div>

                            <div class="detail-item">

                                <i class="fas fa-phone"></i>

                                <span>

                                    ${escapeSearchHtml(voter.mobile || 'N/A')}

                                </span>

                            </div>

                        </div>

                    </div>

                </div>

            `).join('');

    } catch (error) {

        if (error.name === 'AbortError') {

            return;
        }

        console.error(error);

        resultsGrid.innerHTML = `

            <div class="empty-state-large">

                <i class="fas fa-exclamation-circle"></i>

                <h3>Search Error</h3>

                <p>

                    Unable to fetch results

                </p>

            </div>
        `;

    } finally {

        hideSearchLoading();
    }
}

// --------------------------------------
// RESET STATE
// --------------------------------------

function resetSearchResults() {

    const resultsGrid =
        document.getElementById('resultsGrid');

    const resultCount =
        document.getElementById('resultCount');

    if (resultCount) {

        resultCount.textContent = '0 found';
    }

    if (!resultsGrid) return;

    resultsGrid.innerHTML = `

        <div class="empty-state-large">

            <i class="fas fa-search"></i>

            <h3>Start Searching</h3>

            <p>

                Search by name,
                EPIC,
                or house number

            </p>

        </div>
    `;
}

// --------------------------------------
// LOADING
// --------------------------------------

function showSearchLoading() {

    document.body.classList.add('search-loading');
}

function hideSearchLoading() {

    document.body.classList.remove('search-loading');
}

// --------------------------------------
// ESCAPE HTML
// --------------------------------------

function escapeSearchHtml(text) {

    if (text === null || text === undefined) {

        return '';
    }

    const div =
        document.createElement('div');

    div.textContent =
        String(text);

    return div.innerHTML;
}

// --------------------------------------
// EXTRA CSS
// --------------------------------------

const style =
    document.createElement('style');

style.textContent = `

.search-loading #mainSearch {

    opacity: 0.7;
}

.search-loading {

    cursor: wait;
}

`;

document.head.appendChild(style);