// Global variables
let currentVoterId = null;
let searchTimeout = null;
// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    
    initializeMobileMenu();
    
    initializeModals();
    
    initializeExportImport();
    
    initializeGlobalSearch();
    
    initializeProfileDropdown();
    
    // Add loading animation
    addLoadingAnimation();
});
// Mobile menu functionality
function initializeMobileMenu() {
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(event) {
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(event.target) && !mobileToggle.contains(event.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });
    }
}

// Modal functionality
function initializeModals() {
    const modals = document.querySelectorAll('.modal');
    const closeBtns = document.querySelectorAll('.close');
    
    // Close modal when clicking on close button
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) modal.style.display = 'none';
        });
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Export/Import functionality
function initializeExportImport() {
    const exportBtn = document.getElementById('exportBtn');
    const importBtn = document.getElementById('importBtn');
    
    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showExportOptions();
        });
    }
    
    if (importBtn) {
        importBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showImportDialog();
        });
    }
}

function showExportOptions() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content small">
            <div class="modal-header">
                <h2>Export Data</h2>
                <span class="close">&times;</span>
            </div>
            <div class="modal-body">
                <div class="export-options">
                    <button onclick="exportData('csv')" class="btn-primary" style="width: 100%; margin-bottom: 10px;">
                        <i class="fas fa-file-csv"></i> Export as CSV
                    </button>
                    <button onclick="exportData('excel')" class="btn-primary" style="width: 100%; margin-bottom: 10px;">
                        <i class="fas fa-file-excel"></i> Export as Excel
                    </button>
                    <button onclick="backupDatabase()" class="btn-secondary" style="width: 100%;">
                        <i class="fas fa-database"></i> Backup Database
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const closeBtn = modal.querySelector('.close');
    closeBtn.onclick = () => modal.remove();
    
    modal.addEventListener('click', function(event) {
    
    if (event.target === modal) {
        
        modal.remove();
    }
});
}

function exportData(format) {
    if (format === 'csv') {
        window.location.href = '/export/csv';
    } else if (format === 'excel') {
        window.location.href = '/export/excel';
    }
    closeModal();
}

function showImportDialog() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content small">
            <div class="modal-header">
                <h2>Import Data</h2>
                <span class="close">&times;</span>
            </div>
            <div class="modal-body">
                <form id="importForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Select CSV File</label>
                        <input type="file" name="csv_file" accept=".csv" required>
                        <small>File should contain voter data with appropriate headers</small>
                    </div>
                    <button type="submit" class="btn-primary">Import</button>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const form = modal.querySelector('#importForm');
    form.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        
        showLoading();
        
        try {
            const response = await fetch('/import/csv', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
    throw new Error('Import request failed');
}

const result = await response.json();
            
            if (result.success) {
                showNotification(`Successfully imported ${result.imported} records`, 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showNotification('Import failed', 'error');
            }
        } catch (error) {
            showNotification('Error importing data', 'error');
        } finally {
            hideLoading();
            modal.remove();
        }
    };
    
    const closeBtn = modal.querySelector('.close');
    closeBtn.onclick = () => {
    modal.style.display = 'none';
    
    setTimeout(() => {
        modal.remove();
    }, 150);
};
}

function backupDatabase() {
    window.location.href = '/backup';
    showNotification('Backup initiated', 'success');
}
function initializeProfileDropdown() {

    const dropdown =
        document.querySelector('.profile-dropdown');

    if (!dropdown) return;

    dropdown.addEventListener('click', function() {

        showNotification(
            'Admin Panel Active',
            'info'
        );
    });
}
// Global search functionality
function initializeGlobalSearch() {
    const searchInput = document.getElementById('globalSearch');
    const suggestionsDiv = document.getElementById('searchSuggestions');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            if (query.length >= 2) {
                if (searchTimeout) clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    performLiveSearch(query, suggestionsDiv);
                }, 300);
            } else {
                if (suggestionsDiv) {
    suggestionsDiv.classList.remove('active');
}
            }
        });
        
        // Handle enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const query = this.value.trim();
                if (query) {
                    window.location.href = `/search?q=${encodeURIComponent(query)}`;
                }
            }
        });
    }
}

async function performLiveSearch(query, suggestionsDiv) {
        
        if (!suggestionsDiv) return;
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
    throw new Error('Request failed');
}

const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            suggestionsDiv.innerHTML = `
                <div class="suggestions-list">
                    ${data.results.slice(0, 5).map(voter => `
                        <div class="suggestion-item" onclick="window.location.href='/voter/${voter.id}'">
                            <i class="fas fa-user"></i>
                            <div>
                                <strong>${escapeHtml(voter.name)}</strong>
                                <small>
${escapeHtml(voter.house_no || 'No house')}
|
EPIC:
${escapeHtml(voter.epic || 'N/A')}
</small>
                            </div>
                        </div>
                    `).join('')}
                    ${data.count > 5 ? `<div class="suggestion-more">+ ${data.count - 5} more results. Press Enter to see all.</div>` : ''}
                </div>
            `;
            suggestionsDiv.classList.add('active');
        } else {
            suggestionsDiv.innerHTML = '<div class="suggestions-list"><div class="no-results">No results found</div></div>';
            suggestionsDiv.classList.add('active');
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

// Helper Functions
function showLoading() {
    let loader = document.getElementById('globalLoader');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'globalLoader';
        loader.innerHTML = '<div class="loader"></div>';
        loader.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
        `;
        document.body.appendChild(loader);
    }
    loader.style.display = 'flex';
}

function hideLoading() {
    const loader = document.getElementById('globalLoader');
    if (loader) {
        loader.style.display = 'none';
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'success' ? '#00c853' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10000;
        animation: slideInRight 0.3s ease;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    
    if (text === null || text === undefined) {
        return '';
    }
    
    const div = document.createElement('div');
    
    div.textContent = String(text);
    
    return div.innerHTML;
}

function addLoadingAnimation() {
    const style = document.createElement('style');
    style.textContent = `
      
        .loader {
            width: 50px;
            height: 50px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: var(--primary);
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .suggestions-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .suggestion-item {
            padding: 10px 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }
        
        .suggestion-item:hover {
            background: rgba(13, 143, 129, 0.1);
        }
        
        .suggestion-item i {
            color: var(--primary);
        }
        
        .suggestion-item strong {
            display: block;
            margin-bottom: 3px;
        }
        
        .suggestion-item small {
            font-size: 11px;
            color: var(--text-secondary);
        }
        
        .suggestion-more, .no-results {
            padding: 10px 15px;
            text-align: center;
            color: var(--text-secondary);
            font-size: 12px;
        }
        
        .export-options button {
            margin-bottom: 10px !important;
        }
    `;
    document.head.appendChild(style);
}

function closeModal() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => modal.remove());
}

