// ======================================
// GLOBAL VARIABLES
// ======================================

let currentVoterId = null;
let searchTimeout = null;

// ======================================
// INITIALIZE
// ======================================

document.addEventListener('DOMContentLoaded', function () {

    initializeMobileMenu();

    initializeModals();

    initializeExportImport();

    initializeGlobalSearch();

    initializeProfileDropdown();

    addLoadingAnimation();
});

// ======================================
// MOBILE MENU
// ======================================

function initializeMobileMenu() {

    const mobileToggle =
        document.getElementById('mobileMenuToggle');

    const sidebar =
        document.getElementById('sidebar');

    if (!mobileToggle || !sidebar) return;

    mobileToggle.addEventListener('click', function (e) {

        e.stopPropagation();

        sidebar.classList.toggle('open');

        document.body.classList.toggle('sidebar-open');
    });

    document.addEventListener('click', function (event) {

        if (window.innerWidth <= 768) {

            if (
                !sidebar.contains(event.target) &&
                !mobileToggle.contains(event.target)
            ) {

                sidebar.classList.remove('open');

                document.body.classList.remove('sidebar-open');
            }
        }
    });
}

// ======================================
// MODALS
// ======================================

function initializeModals() {

    const modals =
        document.querySelectorAll('.modal');

    const closeBtns =
        document.querySelectorAll('.close');

    closeBtns.forEach(btn => {

        btn.addEventListener('click', function () {

            const modal =
                this.closest('.modal');

            if (modal) {

                modal.style.display = 'none';
            }
        });
    });

    window.addEventListener('click', function (event) {

        modals.forEach(modal => {

            if (event.target === modal) {

                modal.style.display = 'none';
            }
        });
    });
}

// ======================================
// EXPORT IMPORT
// ======================================

function initializeExportImport() {

    const exportBtn =
        document.getElementById('exportBtn');

    const importBtn =
        document.getElementById('importBtn');

    if (exportBtn) {

        exportBtn.addEventListener('click', function (e) {

            e.preventDefault();

            showExportOptions();
        });
    }

    if (importBtn) {

        importBtn.addEventListener('click', function (e) {

            e.preventDefault();

            showImportDialog();
        });
    }
}

// ======================================
// PROFILE
// ======================================

function initializeProfileDropdown() {

    const dropdown =
        document.querySelector('.profile-dropdown');

    if (!dropdown) return;

    dropdown.addEventListener('click', function () {

        showNotification(
            'Admin Panel Active',
            'info'
        );
    });
}

// ======================================
// GLOBAL SEARCH
// ======================================

function initializeGlobalSearch() {

    const searchInputs = [

        document.getElementById('globalSearch'),
        document.getElementById('mobileSearch')

    ];

    const suggestionsDiv =
        document.getElementById('searchSuggestions');

    searchInputs.forEach(searchInput => {

        if (!searchInput) return;

        // INPUT SEARCH
        searchInput.addEventListener('input', function () {

            const query = this.value.trim();

            if (query.length >= 2) {

                if (searchTimeout) {

                    clearTimeout(searchTimeout);
                }

                searchTimeout = setTimeout(() => {

                    performLiveSearch(
                        query,
                        suggestionsDiv
                    );

                }, 300);

            } else {

                if (suggestionsDiv) {

                    suggestionsDiv.classList.remove('active');

                    suggestionsDiv.innerHTML = '';
                }
            }
        });

        // ENTER SEARCH
        searchInput.addEventListener('keypress', function (e) {

            if (e.key === 'Enter') {

                const query = this.value.trim();

                if (query) {

                    window.location.href =
                        `/search?q=${encodeURIComponent(query)}`;
                }
            }
        });
    });

    // CLOSE DROPDOWN
    document.addEventListener('click', function (e) {

        const wrapper =
            document.querySelector('.search-wrapper');

        if (
            suggestionsDiv &&
            wrapper &&
            !wrapper.contains(e.target)
        ) {

            suggestionsDiv.classList.remove('active');
        }
    });
}

// ======================================
// LIVE SEARCH
// ======================================

async function performLiveSearch(query, suggestionsDiv) {

    if (!suggestionsDiv) return;

    try {

        const response = await fetch(
            `/api/search?q=${encodeURIComponent(query)}`
        );

        if (!response.ok) {

            throw new Error('Request failed');
        }

        const data = await response.json();

        if (data.results && data.results.length > 0) {

            suggestionsDiv.innerHTML = `

                <div class="suggestions-list">

                    ${data.results.slice(0, 5).map(voter => `

                        <div class="suggestion-item"

                            onclick="
                                window.location.href='/voter/${voter.id}'
                            ">

                            <i class="fas fa-user"></i>

                            <div>

                                <strong>
                                    ${escapeHtml(voter.name)}
                                </strong>

                                <small>

                                    ${escapeHtml(voter.house_no || 'No house')}
                                    |
                                    EPIC:
                                    ${escapeHtml(voter.epic || 'N/A')}

                                </small>

                            </div>

                        </div>

                    `).join('')}

                </div>
            `;

            suggestionsDiv.classList.add('active');

        } else {

            suggestionsDiv.innerHTML = `

                <div class="suggestions-list">

                    <div class="no-results">

                        No results found

                    </div>

                </div>
            `;

            suggestionsDiv.classList.add('active');
        }

    } catch (error) {

        console.error('Search error:', error);
    }
}

// ======================================
// HELPERS
// ======================================

function showNotification(message, type = 'info') {

    const notification =
        document.createElement('div');

    notification.className =
        `notification notification-${type}`;

    notification.innerHTML = `

        <span>${message}</span>
    `;

    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #111827;
        color: white;
        padding: 12px 18px;
        border-radius: 10px;
        z-index: 10000;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {

        notification.remove();

    }, 2500);
}

function escapeHtml(text) {

    if (text === null || text === undefined) {

        return '';
    }

    const div =
        document.createElement('div');

    div.textContent =
        String(text);

    return div.innerHTML;
}

function addLoadingAnimation() {

    const style =
        document.createElement('style');

    style.textContent = `

        body.sidebar-open{
            overflow:hidden;
        }

        .loader{
            width:50px;
            height:50px;
            border:3px solid rgba(255,255,255,0.2);
            border-top-color:#14b8a6;
            border-radius:50%;
            animation:spin 1s linear infinite;
        }

        @keyframes spin{
            to{
                transform:rotate(360deg);
            }
        }

        .search-suggestions.active{
            display:block;
        }

        @media(max-width:768px){

            .sidebar{
                left:-100%;
                transition:0.3s ease;
            }

            .sidebar.open{
                left:0;
            }
        }
    `;

    document.head.appendChild(style);
}

function closeModal() {

    document
        .querySelectorAll('.modal')
        .forEach(modal => modal.remove());
}