document.addEventListener('DOMContentLoaded', () => {
    const searchTrigger = document.getElementById('search-trigger');
    const searchModal = document.getElementById('search-modal');
    const searchInput = document.getElementById('symbol-search-input');
    const searchResults = document.getElementById('search-results');
    const closeBtn = document.getElementById('close-search-modal');

    let currentResults = [];
    let selectedIndex = -1;
    let debounceTimer = null;
    let popularSymbols = [];

    async function loadPopularSymbols() {
        try {
            const res = await fetch('/api/v1/symbols/popular?limit=10');
            if (res.ok) {
                const json = await res.json();
                if (json.success && Array.isArray(json.data) && json.data.length > 0) {
                    popularSymbols = json.data;
                    return;
                }
            }
        } catch (e) {
            console.warn('[SymbolSearch] Could not load popular symbols from DB:', e);
        }
    }

    // Pre-load authentic popular symbols from DuckDB
    loadPopularSymbols();

    async function openSearch() {
        if (!searchModal) return;
        searchModal.classList.remove('hidden');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }
        if (!popularSymbols || popularSymbols.length === 0) {
            await loadPopularSymbols();
        }
        // Show authentic popular suggestions from DB on open
        currentResults = popularSymbols;
        selectedIndex = -1;
        renderResults(currentResults);
    }

    function closeSearch() {
        if (!searchModal) return;
        searchModal.classList.add('hidden');
        if (searchInput) searchInput.value = '';
        currentResults = [];
        selectedIndex = -1;
    }

    // Global keyboard shortcut: Ctrl+K or Cmd+K
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
            e.preventDefault();
            if (searchModal && !searchModal.classList.contains('hidden')) {
                closeSearch();
            } else {
                openSearch();
            }
        } else if (e.key === 'Escape' && searchModal && !searchModal.classList.contains('hidden')) {
            e.preventDefault();
            closeSearch();
        }
    });

    searchTrigger?.addEventListener('click', openSearch);
    document.getElementById('active-symbol-badge')?.addEventListener('click', openSearch);
    window.openSymbolSearch = openSearch;
    window.closeSymbolSearch = closeSearch;
    closeBtn?.addEventListener('click', closeSearch);

    // Click outside modal content to close
    searchModal?.addEventListener('click', (e) => {
        if (e.target === searchModal) {
            closeSearch();
        }
    });

    // Input typing with debounce
    searchInput?.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);

        if (!query) {
            currentResults = popularSymbols;
            selectedIndex = -1;
            renderResults(currentResults);
            return;
        }

        debounceTimer = setTimeout(() => {
            performSearch(query);
        }, 150);
    });

    // Keyboard Arrow navigation & Enter selection
    searchInput?.addEventListener('keydown', (e) => {
        if (!currentResults || currentResults.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = (selectedIndex + 1) % currentResults.length;
            updateSelectionVisuals();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = (selectedIndex - 1 + currentResults.length) % currentResults.length;
            updateSelectionVisuals();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            const pickIndex = selectedIndex >= 0 ? selectedIndex : 0;
            if (currentResults[pickIndex]) {
                selectSymbol(currentResults[pickIndex].symbol);
            }
        }
    });

    async function performSearch(query) {
        try {
            const res = await fetch(`/api/v1/symbols/search?query=${encodeURIComponent(query)}&limit=15`);
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.data) && data.data.length > 0) {
                    currentResults = data.data;
                } else {
                    currentResults = [];
                }
            } else {
                currentResults = [];
            }
        } catch (err) {
            console.warn("Search fetch failed:", err);
            currentResults = [];
        }
        selectedIndex = -1;
        renderResults(currentResults);
    }

    function renderResults(items) {
        if (!searchResults) return;

        if (!items || items.length === 0) {
            searchResults.innerHTML = `
                <li style="padding: 16px; color: #787B86; text-align: center; font-size: 13px;">
                    No matching stocks found. Try searching ticker like 'RELIANCE', 'TCS', or 'INFY'.
                </li>
            `;
            return;
        }

        searchResults.innerHTML = items.map((item, idx) => {
            const catBadge = item.category ? `<span class="search-item-badge">${item.category}</span>` : '';
            return `
                <li class="search-item ${idx === selectedIndex ? 'selected' : ''}" data-symbol="${item.symbol}" data-idx="${idx}">
                    <div style="display: flex; align-items: baseline;">
                        <span class="search-item-symbol">${item.symbol}</span>
                        <span class="search-item-name">${item.name || ''}</span>
                    </div>
                    ${catBadge}
                </li>
            `;
        }).join('');

        // Click listeners on items
        searchResults.querySelectorAll('.search-item').forEach(li => {
            li.addEventListener('click', (e) => {
                const sym = e.currentTarget.dataset.symbol;
                if (sym) {
                    selectSymbol(sym);
                }
            });
        });
    }

    function updateSelectionVisuals() {
        if (!searchResults) return;
        const allItems = searchResults.querySelectorAll('.search-item');
        allItems.forEach((li, idx) => {
            if (idx === selectedIndex) {
                li.classList.add('selected');
                li.scrollIntoView({ block: 'nearest' });
            } else {
                li.classList.remove('selected');
            }
        });
    }

    function selectSymbol(sym) {
        if (!sym) return;
        window.currentActiveSymbol = sym;

        // Update placeholder
        const placeholder = document.querySelector('#search-trigger .placeholder');
        if (placeholder) {
            placeholder.textContent = `${sym} (${window.currentSymbolTimeframe || '1D'})`;
        }

        closeSearch();

        // Load new symbol data
        if (typeof window.fetchChartData === 'function') {
            window.fetchChartData(sym, window.currentSymbolTimeframe || '1D');
        }
    }
});
