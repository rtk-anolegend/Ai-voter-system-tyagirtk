// ========================================
// MAIN APPLICATION SCRIPT
// Professional Voter Management System
// ========================================

let appState = {
    isInitialized: false,
    currentPage: 'dashboard',
    mobileMenuOpen: false,
    searchCache: {},
    suggestionsTimeout: null,
    lastQuery: ''
};

let eventListeners = new Map();

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    if (appState.isInitialized) return;
    
    try {
        initializeMobileMenu();
        initializeModals();
        initializeSearch();
        initializeProfileDropdown();
        initializeExportImport();
        addGlobalErrorHandling();
        
        appState.isInitialized = true;
        console.log('App initialized successfully');
    } catch (error) {
        console.error('Initialization error:', error);
    }
}

// ========================================
// MOBILE MENU
// ========================================

function initializeMobileMenu() {
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (!mobileToggle || !sidebar) return;
    
    // Remove old listeners
    if (eventListeners.has('mobileToggle')) {
        const oldListener = eventListeners.get('mobileToggle');
        mobileToggle.removeEventListener('click', oldListener);
    }
    
    // Add new listener
    const clickHandler = (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('open');
        appState.mobileMenuOpen = !appState.mobileMenuOpen;
    };
    
    mobileToggle.addEventListener('click', clickHandler);
    eventListeners.set('mobileToggle', clickHandler);
    
    // Close on outside click
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            if (!sidebar.contains(event.target) && !mobileToggle.contains(event.target)) {
                sidebar.classList.remove('open');
                appState.mobileMenuOpen = false;
            }
        }
    });
}

// ========================================
// MODALS
// ========================================

function initializeModals() {
    // Close buttons
    document.querySelectorAll('.modal .close').forEach(btn => {
        if (eventListeners.has(btn)) {
            btn.removeEventListener('click', eventListeners.get(btn));
        }
        
        const closeHandler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            const modal = btn.closest('.modal');
            if (modal) {
                closeModal(modal);
            }
        };
        
        btn.addEventListener('click', closeHandler);
        eventListeners.set(btn, closeHandler);
    });
    
    // Outside click to close
    document.querySelectorAll('.modal').forEach(modal => {
        if (eventListeners.has(modal)) {
            modal.removeEventListener('click', eventListeners.get(modal));
        }
        
        const outsideHandler = (e) => {
            if (e.target === modal) {
                closeModal(modal);
            }
        };
        
        modal.addEventListener('click', outsideHandler);
        eventListeners.set(modal, outsideHandler);
    });
    
    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                closeModal(modal);
            });
        }
    });
}

function closeModal(modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
    document.body.style.overflow = '';
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

// ========================================
// GLOBAL SEARCH
// ========================================

function initializeSearch() {
    // Sidebar search
    const sidebarSearch = document.querySelector('.sidebar-search input');
    if (sidebarSearch && !eventListeners.has('sidebarSearch')) {
        const sidebarSearchHandler = (e) => {
            const query = e.target.value.trim();
            if (query.length >= 2) {
                performLiveSearch(query, 'sidebar');
            }
        };
        sidebarSearch.addEventListener('input', sidebarSearchHandler);
        eventListeners.set('sidebarSearch', sidebarSearchHandler);
    }
    
    // Header search
    const headerSearch = document.querySelector('.search-wrapper input');
    if (headerSearch && !eventListeners.has('headerSearch')) {
        const headerSearchHandler = (e) => {
            const query = e.target.value.trim();
            if (query.length >= 2) {
                performLiveSearch(query, 'header');
            } else {
                hideSuggestions();
            }
        };
        headerSearch.addEventListener('input', debounce(headerSearchHandler, 200));
        eventListeners.set('headerSearch', headerSearchHandler);
        
        // Enter key
        headerSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = headerSearch.value.trim();
                if (query.length >= 2) {
                    window.location.href = `/search?q=${encodeURIComponent(query)}`;
                }
            }
        });
    }
}

function performLiveSearch(query, source = 'header') {
    if (!query || query.length < 2) {
        hideSuggestions();
        return;
    }
    
    // Check cache
    const cacheKey = `${source}_${query}`;
    if (appState.searchCache[cacheKey]) {
        displaySuggestions(appState.searchCache[cacheKey], source);
        return;
    }
    
    // Clear previous timeout
    if (appState.suggestionsTimeout) {
        clearTimeout(appState.suggestionsTimeout);
    }
    
    appState.suggestionsTimeout = setTimeout(() => {
        fetchSuggestions(query, source);
    }, 200);
}

async function fetchSuggestions(query, source = 'header') {
    try {
        const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}&limit=8`);
        if (!response.ok) throw new Error('Failed to fetch suggestions');
        
        const data = await response.json();
        const suggestions = data.suggestions || [];
        
        // Cache results
        const cacheKey = `${source}_${query}`;
        appState.searchCache[cacheKey] = suggestions;
        
        displaySuggestions(suggestions, source);
    } catch (error) {
        console.error('Suggestions error:', error);
    }
}

function displaySuggestions(suggestions, source = 'header') {
    const wrapper = document.querySelector('.search-wrapper');
    if (!wrapper) return;
    
    let suggestionsBox = wrapper.querySelector('.search-suggestions');
    if (!suggestionsBox) {
        suggestionsBox = document.createElement('div');
        suggestionsBox.className = 'search-suggestions';
        wrapper.appendChild(suggestionsBox);
    }
    
    if (suggestions.length === 0) {
        suggestionsBox.innerHTML = '<div class="search-suggestion-item">No results found</div>';
        suggestionsBox.classList.add('active');
        return;
    }
    
    suggestionsBox.innerHTML = suggestions.map((item, index) => `
        <div class="search-suggestion-item" onclick="goToVoter(${item.id})">
            <div class="suggestion-name">${escapeHtml(item.name)}</div>
            <div class="suggestion-meta">
                ${item.epic ? 'EPIC: ' + escapeHtml(item.epic) : ''}
                ${item.house_no ? ' | House: ' + escapeHtml(item.house_no) : ''}
            </div>
        </div>
    `).join('');
    
    suggestionsBox.classList.add('active');
}

function hideSuggestions() {
    const suggestionsBox = document.querySelector('.search-suggestions');
    if (suggestionsBox) {
        suggestionsBox.classList.remove('active');
    }
}

function goToVoter(voterId) {
    window.location.href = `/voter/${voterId}`;
}

// ========================================
// PROFILE DROPDOWN
// ========================================

function initializeProfileDropdown() {
    const profileDropdown = document.querySelector('.profile-dropdown');
    const dropdownMenu = document.querySelector('.dropdown-menu');
    
    if (!profileDropdown || !dropdownMenu) return;
    
    if (eventListeners.has('profileDropdown')) {
        profileDropdown.removeEventListener('click', eventListeners.get('profileDropdown'));
    }
    
    const toggleHandler = (e) => {
        e.stopPropagation();
        dropdownMenu.classList.toggle('active');
    };
    
    profileDropdown.addEventListener('click', toggleHandler);
    eventListeners.set('profileDropdown', toggleHandler);
    
    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!profileDropdown.contains(e.target) && !dropdownMenu.contains(e.target)) {
            dropdownMenu.classList.remove('active');
        }
    });
}

// ========================================
// EXPORT/IMPORT
// ========================================

function initializeExportImport() {
    const importForm = document.getElementById('importForm');
    if (importForm && !eventListeners.has('importForm')) {
        const submitHandler = async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('csvFile');
            
            if (!fileInput.files.length) {
                showNotification('Please select a file', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('csv_file', fileInput.files[0]);
            
            try {
                const response = await fetch('/import/csv', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    showNotification(`Imported ${data.imported} voters successfully`, 'success');
                    fileInput.value = '';
                    closeModal(importForm.closest('.modal'));
                } else {
                    showNotification(data.error || 'Import failed', 'error');
                }
            } catch (error) {
                console.error('Import error:', error);
                showNotification('Import error: ' + error.message, 'error');
            }
        };
        
        importForm.addEventListener('submit', submitHandler);
        eventListeners.set('importForm', submitHandler);
    }
}

function exportData(format) {
    window.location.href = `/export/${format}`;
}

// ========================================
// UTILITIES
// ========================================

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#00c853' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9999;
        animation: slideUp 0.3s;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideDown 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function addGlobalErrorHandling() {
    window.addEventListener('error', (event) => {
        console.error('Global error:', event.error);
        showNotification('An error occurred. Please refresh the page.', 'error');
    });
    
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled rejection:', event.reason);
        showNotification('An error occurred. Please try again.', 'error');
    });
}

// ========================================
// HELPER FUNCTIONS
// ========================================

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard', 'success');
    }).catch(err => {
        showNotification('Failed to copy', 'error');
    });
}
