/**
 * TradingView-Grade "Indicators, metrics, and strategies" Modal Controller
 */

(function () {
    let catalogCache = null;
    let activeSection = 'builtin'; // 'builtin', 'personal', 'community'
    let activeCategory = 'technicals'; // 'technicals', 'fundamentals', 'my_scripts', 'favorites'
    let activeSubCategory = 'indicators'; // 'indicators', 'strategies', 'profiles', 'patterns', 'options'
    let searchQuery = '';
    let selectedStudyId = null;

    const FAVORITES_STORAGE_KEY = 'nse_quant_starred_studies';
    const MY_SCRIPTS_STORAGE_KEY = 'nse_quant_my_scripts';
    const HIDDEN_SCRIPTS_STORAGE_KEY = 'nse_quant_hidden_scripts';

    // Base engines catalog for creating new custom studies in any tab
    const BASE_ENGINES = {
        indicators: [
            { id: 'ema', name: 'EMA (Exponential Moving Average)', overlay: true, defaultPeriod: 20, defaultColor: '#FF6D00' },
            { id: 'sma', name: 'SMA (Simple Moving Average)', overlay: true, defaultPeriod: 20, defaultColor: '#2962FF' },
            { id: 'vwap', name: 'VWAP (Volume Weighted Average Price)', overlay: true, defaultPeriod: 0, defaultColor: '#F5AC00' },
            { id: 'bollinger_bands', name: 'Bollinger Bands', overlay: true, defaultPeriod: 20, defaultMult: 2.0, defaultColor: '#2962FF' },
            { id: 'supertrend', name: 'Supertrend', overlay: true, defaultPeriod: 10, defaultMult: 3.0, defaultColor: '#00E676' },
            { id: 'rsi', name: 'RSI (Relative Strength Index)', overlay: false, defaultPeriod: 14, defaultColor: '#7E57C2' },
            { id: 'macd', name: 'MACD (12, 26, 9)', overlay: false, defaultPeriod: 12, defaultColor: '#2962FF' },
            { id: 'stochastic', name: 'Stochastic Oscillator', overlay: false, defaultPeriod: 14, defaultColor: '#FF6D00' },
            { id: 'atr', name: 'ATR (Average True Range)', overlay: false, defaultPeriod: 14, defaultColor: '#FF5252' }
        ],
        strategies: [
            { id: 'strat_ema_cross', name: 'EMA Cross Strategy (Trend Follower)', overlay: true, defaultPeriod: 9, defaultMult: 21 },
            { id: 'strat_rsi_reversal', name: 'RSI Mean Reversion Strategy', overlay: false, defaultPeriod: 14, defaultMult: 70 },
            { id: 'strat_bb_breakout', name: 'Bollinger Bands Volatility Breakout', overlay: true, defaultPeriod: 20, defaultMult: 2.0 },
            { id: 'strat_supertrend', name: 'Supertrend Trend Follower Strategy', overlay: true, defaultPeriod: 10, defaultMult: 3.0 }
        ],
        profiles: [
            { id: 'visible_range_vp', name: 'Visible Range Volume Profile (VRVP)', overlay: true, defaultRows: 70, defaultVA: 70 },
            { id: 'session_vp', name: 'Session Volume Profile (SVP)', overlay: true, defaultRows: 50, defaultVA: 70 },
            { id: 'session_vp_hd', name: 'Session Volume Profile HD', overlay: true, defaultRows: 120, defaultVA: 70 },
            { id: 'fixed_range_vp', name: 'Fixed Range Volume Profile', overlay: true, defaultRows: 70, defaultVA: 70 },
            { id: 'tpo', name: 'Time Price Opportunity (TPO / Market Profile)', overlay: true, defaultBracket: 30, defaultVA: 70 },
            { id: 'session_tpo', name: 'Session TPO', overlay: true, defaultBracket: 30, defaultVA: 70 }
        ],
        patterns: [
            { id: 'bullish_engulfing', name: 'Bullish Engulfing Pattern', overlay: true },
            { id: 'bearish_engulfing', name: 'Bearish Engulfing Pattern', overlay: true },
            { id: 'morning_star', name: 'Morning Star Pattern', overlay: true },
            { id: 'evening_star', name: 'Evening Star Pattern', overlay: true },
            { id: 'hammer', name: 'Hammer Reversal', overlay: true },
            { id: 'doji', name: 'Doji Indecision Bar', overlay: true },
            { id: 'double_top', name: 'Double Top Reversal', overlay: true },
            { id: 'double_bottom', name: 'Double Bottom Reversal', overlay: true },
            { id: 'head_and_shoulders', name: 'Head and Shoulders Pattern', overlay: true }
        ],
        options: [
            { id: 'opt_max_pain', name: 'Max Pain Strike Benchmark', overlay: true },
            { id: 'opt_pcr', name: 'Put-Call Ratio (PCR) Oscillator', overlay: false },
            { id: 'opt_strike_oi_profile', name: 'Strike Open Interest Profile', overlay: true },
            { id: 'opt_iv_skew', name: 'Implied Volatility (IV) Skew', overlay: false }
        ]
    };

    function getStarredIds() {
        try {
            return JSON.parse(localStorage.getItem(FAVORITES_STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    function getHiddenIds() {
        try {
            return JSON.parse(localStorage.getItem(HIDDEN_SCRIPTS_STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    function toggleStar(studyId, e) {
        if (e) {
            e.stopPropagation();
            e.preventDefault();
        }
        let starred = getStarredIds();
        if (starred.includes(studyId)) {
            starred = starred.filter(id => id !== studyId);
        } else {
            starred.push(studyId);
        }
        localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(starred));
        renderList();
    }

    async function fetchCatalog() {
        if (catalogCache) return catalogCache;
        let baseList = [];
        try {
            const res = await fetch('/api/v1/studies/catalog');
            if (res.ok) {
                const json = await res.json();
                if (json.success && Array.isArray(json.data)) {
                    baseList = json.data;
                }
            }
        } catch (err) {
            console.warn("Could not fetch remote studies catalog, using cached fallback:", err);
        }

        // Merge custom user-saved setups from localStorage
        try {
            const raw = localStorage.getItem('tv_user_saved_scripts');
            if (raw) {
                const userScripts = JSON.parse(raw);
                if (Array.isArray(userScripts)) {
                    userScripts.forEach(s => { s.is_custom = true; });
                    baseList = [...userScripts, ...baseList];
                }
            }
        } catch (e) {
            console.warn("Could not parse user saved scripts from localStorage:", e);
        }

        catalogCache = baseList;
        return catalogCache;
    }

    function openStudyDialog() {
        const backdrop = document.getElementById('study-modal-backdrop');
        if (!backdrop) return;
        backdrop.classList.add('open');
        document.body.classList.add('modal-open');

        // Focus search input
        const searchInput = document.getElementById('study-search-input');
        if (searchInput) {
            setTimeout(() => searchInput.focus(), 50);
        }

        loadAndRender();
    }

    function closeStudyDialog() {
        const backdrop = document.getElementById('study-modal-backdrop');
        if (!backdrop) return;
        backdrop.classList.remove('open');
        document.body.classList.remove('modal-open');
        closeCreateStudyModal();
    }

    window.openStudyDialog = openStudyDialog;
    window.closeStudyDialog = closeStudyDialog;

    async function loadAndRender() {
        await fetchCatalog();
        renderSidebar();
        renderPills();
        renderList();
    }

    function renderSidebar() {
        document.querySelectorAll('.tv-study-nav-item').forEach(btn => {
            const sec = btn.dataset.section;
            const cat = btn.dataset.category;
            const isMatch = (sec === activeSection && cat === activeCategory);
            btn.classList.toggle('active', isMatch);
        });
    }

    function renderPills() {
        const pillsBar = document.getElementById('study-pills-bar');
        const pillsScroll = document.getElementById('study-pills-scroll');
        const createBtn = document.getElementById('study-create-new-btn');
        if (!pillsBar) return;

        const labelMap = {
            indicators: '+ Create New Indicator',
            strategies: '+ Create New Strategy',
            profiles: '+ Create New Profile',
            patterns: '+ Create New Pattern',
            options: '+ Create New Option Study',
            my_scripts: '+ Create New Script',
            favorites: '+ Create New Setup',
            fundamentals: '+ Create New Metric',
            community: '+ Create New Study'
        };

        if (activeCategory === 'technicals') {
            pillsBar.style.display = 'flex';
            if (pillsScroll) pillsScroll.style.display = 'flex';
            document.querySelectorAll('.tv-study-pill-btn').forEach(btn => {
                const sub = btn.dataset.sub;
                btn.classList.toggle('active', sub === activeSubCategory);
            });

            if (createBtn) {
                createBtn.style.display = 'inline-flex';
                createBtn.textContent = labelMap[activeSubCategory] || '+ Create New Study';
                createBtn.title = `Create a custom study in ${activeSubCategory}`;
            }
        } else {
            // In my_scripts, favorites, fundamentals, or community:
            // Display pillsBar with toolbar create action
            pillsBar.style.display = 'flex';
            if (pillsScroll) pillsScroll.style.display = 'none';
            if (createBtn) {
                createBtn.style.display = 'inline-flex';
                createBtn.textContent = labelMap[activeCategory] || '+ Create New Study';
                createBtn.title = `Create a custom study in ${activeCategory}`;
            }
        }
    }

    function filterStudies() {
        if (!catalogCache) return [];
        const starred = getStarredIds();
        const hiddenIds = getHiddenIds();
        const q = (searchQuery || '').trim().toLowerCase();

        return catalogCache.filter(study => {
            // Exclude deleted/hidden scripts
            if (hiddenIds.includes(study.id)) return false;

            // Text search matches override tab filtering if searching globally
            if (q.length > 0) {
                const nameMatch = study.name.toLowerCase().includes(q);
                const descMatch = study.description.toLowerCase().includes(q);
                const tagMatch = Array.isArray(study.tags) && study.tags.some(t => t.toLowerCase().includes(q));
                if (!nameMatch && !descMatch && !tagMatch) return false;
            }

            // Category & section filtering
            if (activeCategory === 'favorites') {
                return starred.includes(study.id);
            }

            if (activeCategory === 'my_scripts') {
                return study.section === 'personal' || study.is_custom === true || study.category === 'scripts';
            }

            if (activeSection === 'builtin') {
                if (activeCategory === 'fundamentals') {
                    return study.category === 'fundamentals';
                }
                if (activeCategory === 'technicals') {
                    if (q.length > 0) return study.category === 'technicals';
                    return (study.category === 'technicals' && study.sub_category === activeSubCategory) ||
                           (study.is_custom && study.sub_category === activeSubCategory);
                }
            }

            if (activeSection === 'community') {
                return study.section === 'community';
            }

            return true;
        });
    }

    function renderList() {
        const listEl = document.getElementById('study-items-list');
        const emptyEl = document.getElementById('study-empty-state');
        if (!listEl) return;

        const filtered = filterStudies();
        const starred = getStarredIds();

        listEl.innerHTML = '';

        if (filtered.length === 0) {
            listEl.style.display = 'none';
            if (emptyEl) emptyEl.style.display = 'flex';
            updateDetailBar(null);
            return;
        }

        listEl.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';

        // Auto select first item if none selected or selected not in list
        if (!selectedStudyId || !filtered.some(s => s.id === selectedStudyId)) {
            selectedStudyId = filtered[0].id;
        }

        filtered.forEach(study => {
            const isStarred = starred.includes(study.id);
            const isSelected = study.id === selectedStudyId;
            const isDeletable = study.is_custom || study.section === 'personal' || activeCategory === 'my_scripts';

            const li = document.createElement('li');
            li.className = `tv-study-row ${isSelected ? 'selected' : ''}`;
            li.dataset.studyId = study.id;

            const badgeHtml = study.is_custom
                ? `<span class="tv-study-badge custom-badge">Custom</span> <span class="tv-study-badge">${study.overlay ? 'Overlay' : 'Sub-Pane'}</span>`
                : `<span class="tv-study-badge">${study.overlay ? 'Overlay' : 'Sub-Pane'}</span>`;

            const deleteBtnHtml = isDeletable
                ? `<button class="tv-study-delete-btn" title="Delete script" data-delete-id="${escapeHtml(study.id)}">🗑️</button>`
                : '';

            li.innerHTML = `
                <div class="tv-study-row-left">
                    <button class="tv-study-star-btn ${isStarred ? 'starred' : ''}" title="${isStarred ? 'Remove from favorites' : 'Add to favorites'}">
                        ${isStarred ? '★' : '☆'}
                    </button>
                    <span class="tv-study-item-name">${escapeHtml(study.name)}</span>
                    ${badgeHtml}
                </div>
                <div class="tv-study-row-right">
                    <button class="tv-study-apply-btn" title="Add to active chart">+ Add</button>
                    ${deleteBtnHtml}
                </div>
            `;

            // Star click
            const starBtn = li.querySelector('.tv-study-star-btn');
            starBtn.addEventListener('click', (e) => toggleStar(study.id, e));

            // Apply button click
            const applyBtn = li.querySelector('.tv-study-apply-btn');
            applyBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                applyStudyToChart(study);
            });

            // Delete button click
            const deleteBtn = li.querySelector('.tv-study-delete-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    confirmAndDeleteStudy(study);
                });
            }

            // Row click selection
            li.addEventListener('click', () => {
                selectedStudyId = study.id;
                document.querySelectorAll('.tv-study-row').forEach(r => r.classList.remove('selected'));
                li.classList.add('selected');
                updateDetailBar(study);
            });

            listEl.appendChild(li);
        });

        const activeStudy = filtered.find(s => s.id === selectedStudyId) || filtered[0];
        updateDetailBar(activeStudy);
    }

    function confirmAndDeleteStudy(study) {
        if (!study) return;
        const msg = `Are you sure you want to delete "${study.name}"?\nThis script will be removed from your catalog.`;
        if (!window.confirm(msg)) {
            return;
        }

        // 1. Remove from localStorage saved scripts
        try {
            const raw = localStorage.getItem('tv_user_saved_scripts');
            if (raw) {
                const userSaved = JSON.parse(raw);
                const updated = userSaved.filter(s => s.id !== study.id);
                localStorage.setItem('tv_user_saved_scripts', JSON.stringify(updated));
            }
        } catch (e) {
            console.error("Error removing from localStorage:", e);
        }

        // 2. Track in hidden scripts so built-in personal items remain deleted
        try {
            const hidden = getHiddenIds();
            if (!hidden.includes(study.id)) {
                hidden.push(study.id);
                localStorage.setItem(HIDDEN_SCRIPTS_STORAGE_KEY, JSON.stringify(hidden));
            }
        } catch (e) {
            console.error("Error storing hidden script:", e);
        }

        // 3. Remove from remote custom backend API if applicable
        if (study.is_custom || study.id.startsWith('custom_')) {
            fetch(`/api/v1/studies/custom/${encodeURIComponent(study.id)}`, { method: 'DELETE' })
                .catch(err => console.warn("Could not delete from backend:", err));
        }

        // 4. Remove from memory catalogCache
        if (catalogCache) {
            catalogCache = catalogCache.filter(s => s.id !== study.id);
        }

        // 5. If selected, reset selection
        if (selectedStudyId === study.id) {
            selectedStudyId = null;
        }

        showStudyToast(`Removed "${study.name}"`);
        renderList();
    }

    window.confirmAndDeleteStudy = confirmAndDeleteStudy;

    function updateDetailBar(study) {
        const bar = document.getElementById('study-detail-bar');
        const descEl = document.getElementById('study-detail-desc');
        const applyBtn = document.getElementById('study-detail-apply-btn');
        if (!bar || !descEl || !applyBtn) return;

        // Ensure "Save Active Setup" button exists
        let saveBtn = document.getElementById('study-detail-save-btn');
        if (!saveBtn) {
            saveBtn = document.createElement('button');
            saveBtn.id = 'study-detail-save-btn';
            saveBtn.className = 'tv-study-secondary-btn';
            saveBtn.textContent = '💾 Save Active Setup';
            saveBtn.style.cssText = 'background:#2a2e39; color:#d1d4dc; border:1px solid #363a45; padding:8px 14px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; margin-right:10px; transition:all 0.15s ease;';
            saveBtn.onmouseenter = () => { saveBtn.style.background = '#363a45'; saveBtn.style.color = '#ffffff'; };
            saveBtn.onmouseleave = () => { saveBtn.style.background = '#2a2e39'; saveBtn.style.color = '#d1d4dc'; };
            saveBtn.onclick = () => saveCurrentActiveSetup();
            applyBtn.parentNode.insertBefore(saveBtn, applyBtn);
        }

        if (!study) {
            descEl.textContent = 'Select an indicator or strategy to view specifications and parameters.';
            applyBtn.disabled = true;
            return;
        }

        applyBtn.disabled = false;
        descEl.innerHTML = `<strong>${escapeHtml(study.name)}</strong>: ${escapeHtml(study.description)}`;
        applyBtn.onclick = () => applyStudyToChart(study);
    }

    function saveCurrentActiveSetup() {
        const name = prompt("Enter a name for your custom workspace setup:", "My Custom Indicator Setup");
        if (!name || !name.trim()) return;

        // Gather currently active studies
        const activeStudiesList = [];
        if (window.activeStudiesManager && window.activeStudiesManager.activeStudies) {
            window.activeStudiesManager.activeStudies.forEach(s => {
                activeStudiesList.push(s.studyId);
            });
        }
        if (window.volumeProfileOverlay && window.volumeProfileOverlay.activeMode) {
            activeStudiesList.push(window.volumeProfileOverlay.activeMode);
        }

        const newCustomStudy = {
            id: `custom_setup_${Date.now()}`,
            name: name.trim(),
            section: "personal",
            category: "scripts",
            sub_category: "my_scripts",
            description: `Custom saved setup containing: ${activeStudiesList.length > 0 ? activeStudiesList.join(', ').toUpperCase() : 'selected indicators'}.`,
            overlay: true,
            default_inputs: { studies: activeStudiesList.length > 0 ? activeStudiesList : ['ema', 'rsi'] },
            tags: ["personal", "custom", "saved", "my scripts"],
            is_custom: true
        };

        try {
            const raw = localStorage.getItem('tv_user_saved_scripts');
            const userSaved = raw ? JSON.parse(raw) : [];
            userSaved.unshift(newCustomStudy);
            localStorage.setItem('tv_user_saved_scripts', JSON.stringify(userSaved));
        } catch (e) {
            console.error("Failed to save to localStorage:", e);
        }

        if (catalogCache) {
            catalogCache.unshift(newCustomStudy);
        }

        showStudyToast(`Saved "${newCustomStudy.name}" to My scripts`);
        renderList();
    }

    // --- Create Custom Study Modal Logic ---

    function openCreateStudyModal(targetCategory = null) {
        const modal = document.getElementById('study-create-modal');
        if (!modal) {
            console.error("[StudyModal] #study-create-modal not found in DOM");
            return;
        }

        let category = targetCategory || activeSubCategory;
        if (!['indicators', 'strategies', 'profiles', 'patterns', 'options'].includes(category)) {
            category = 'indicators';
        }

        const categorySelect = document.getElementById('create-study-category');
        if (categorySelect) categorySelect.value = category;

        updateCreateModalFields(category);

        const nameInput = document.getElementById('create-study-name');
        if (nameInput) {
            nameInput.value = '';
            setTimeout(() => nameInput.focus(), 60);
        }

        const descInput = document.getElementById('create-study-desc');
        if (descInput) descInput.value = '';

        const autoApplyCb = document.getElementById('create-study-auto-apply');
        if (autoApplyCb) autoApplyCb.checked = true;

        modal.style.display = 'flex';
        modal.classList.add('open');
    }

    function closeCreateStudyModal() {
        const modal = document.getElementById('study-create-modal');
        if (!modal) return;
        modal.style.display = 'none';
        modal.classList.remove('open');
    }

    window.openCreateStudyModal = openCreateStudyModal;
    window.closeCreateStudyModal = closeCreateStudyModal;

    function updateCreateModalFields(category) {
        const titleEl = document.getElementById('create-modal-title');
        const badgeEl = document.getElementById('create-modal-badge');
        const baseSelect = document.getElementById('create-study-base');
        const periodRow = document.getElementById('create-param-period-row');
        const secondaryRow = document.getElementById('create-param-secondary-row');
        const styleRow = document.getElementById('create-param-style-row');

        const periodGroup = document.getElementById('create-param-period-group');
        const periodLabel = document.getElementById('create-param-period-label');
        const periodInput = document.getElementById('create-param-period');

        const multGroup = document.getElementById('create-param-mult-group');
        const multLabel = document.getElementById('create-param-mult-label');
        const multInput = document.getElementById('create-param-mult');

        const rowsGroup = document.getElementById('create-param-rows-group');
        const rowsLabel = document.getElementById('create-param-rows-label');
        const rowsInput = document.getElementById('create-param-rows');

        const sec2Group = document.getElementById('create-param-sec2-group');
        const sec2Label = document.getElementById('create-param-sec2-label');
        const sec2Input = document.getElementById('create-param-sec2');

        const colorGroup = document.getElementById('create-param-color-group');
        const colorLabel = document.getElementById('create-param-color-label');
        const colorPicker = document.getElementById('create-param-color');
        const colorHex = document.getElementById('create-param-color-hex');

        const overlayGroup = document.getElementById('create-param-overlay-group');
        const displayLabel = document.getElementById('create-display-mode-label');

        const nameInput = document.getElementById('create-study-name');

        const catTitles = {
            indicators: 'Create New Indicator',
            strategies: 'Create New Strategy',
            profiles: 'Create New Profile',
            patterns: 'Create New Pattern',
            options: 'Create New Options Study'
        };

        const catBadges = {
            indicators: 'Indicators',
            strategies: 'Strategies',
            profiles: 'Profiles',
            patterns: 'Patterns',
            options: 'Options'
        };

        if (titleEl) titleEl.textContent = catTitles[category] || 'Create New Study';
        if (badgeEl) badgeEl.textContent = catBadges[category] || category.toUpperCase();

        const namePlaceholders = {
            indicators: 'e.g. My Fast 9 EMA Scalp',
            strategies: 'e.g. EMA 9/21 Trend Strategy',
            profiles: 'e.g. Intraday Scalp VRVP',
            patterns: 'e.g. Bullish Engulfing Breakout',
            options: 'e.g. Nifty Expiry Max Pain'
        };
        if (nameInput) nameInput.placeholder = namePlaceholders[category] || 'Study name';

        // Populate base engine dropdown
        if (baseSelect) {
            baseSelect.innerHTML = '';
            const engines = BASE_ENGINES[category] || [];
            engines.forEach(eng => {
                const opt = document.createElement('option');
                opt.value = eng.id;
                opt.textContent = eng.name;
                baseSelect.appendChild(opt);
            });
        }

        // Configure input visibility and symmetrical layouts based on category
        if (category === 'indicators') {
            if (periodRow) periodRow.style.display = 'flex';
            if (periodGroup) {
                periodGroup.style.display = 'flex';
                if (periodLabel) periodLabel.textContent = 'Period / Length';
                if (periodInput) periodInput.value = '20';
            }
            if (multGroup) {
                multGroup.style.display = 'flex';
                if (multLabel) multLabel.textContent = 'Multiplier / StdDev';
                if (multInput) { multInput.value = '2.0'; multInput.step = '0.1'; }
            }

            if (secondaryRow) secondaryRow.style.display = 'none';

            if (styleRow) styleRow.style.display = 'flex';
            if (colorGroup) {
                colorGroup.style.display = 'flex';
                if (colorLabel) colorLabel.textContent = 'Theme Color';
                if (colorPicker) colorPicker.value = '#2962FF';
                if (colorHex) colorHex.textContent = '#2962FF';
            }
            if (overlayGroup) {
                overlayGroup.style.display = 'flex';
                if (displayLabel) displayLabel.textContent = 'Chart Display Mode';
                const overlayRadio = document.querySelector('input[name="create-display-mode"][value="overlay"]');
                if (overlayRadio) overlayRadio.checked = true;
            }
        } else if (category === 'strategies') {
            if (periodRow) periodRow.style.display = 'flex';
            if (periodGroup) {
                periodGroup.style.display = 'flex';
                if (periodLabel) periodLabel.textContent = 'Fast Period / Signal';
                if (periodInput) periodInput.value = '9';
            }
            if (multGroup) {
                multGroup.style.display = 'flex';
                if (multLabel) multLabel.textContent = 'Slow Period / Multiplier';
                if (multInput) { multInput.value = '21'; multInput.step = '1'; }
            }

            if (secondaryRow) secondaryRow.style.display = 'flex';
            if (rowsGroup) {
                rowsGroup.style.display = 'flex';
                if (rowsLabel) rowsLabel.textContent = 'Stop Loss % (e.g. 1.5)';
                if (rowsInput) rowsInput.value = '1.5';
            }
            if (sec2Group) {
                sec2Group.style.display = 'flex';
                if (sec2Label) sec2Label.textContent = 'Take Profit % (e.g. 3.0)';
                if (sec2Input) sec2Input.value = '3.0';
            }

            if (styleRow) styleRow.style.display = 'none';
        } else if (category === 'profiles') {
            if (periodRow) periodRow.style.display = 'flex';
            if (periodGroup) {
                periodGroup.style.display = 'flex';
                if (periodLabel) periodLabel.textContent = 'Value Area % (e.g. 70)';
                if (periodInput) periodInput.value = '70';
            }
            if (multGroup) {
                multGroup.style.display = 'flex';
                if (multLabel) multLabel.textContent = 'Price Rows Resolution';
                if (multInput) { multInput.value = '70'; multInput.step = '5'; }
            }

            if (secondaryRow) secondaryRow.style.display = 'none';

            if (styleRow) styleRow.style.display = 'flex';
            if (colorGroup) {
                colorGroup.style.display = 'flex';
                if (colorLabel) colorLabel.textContent = 'Histogram Theme Color';
                if (colorPicker) colorPicker.value = '#2962FF';
                if (colorHex) colorHex.textContent = '#2962FF';
            }
            if (overlayGroup) {
                overlayGroup.style.display = 'none';
            }
        } else if (category === 'patterns') {
            if (periodRow) periodRow.style.display = 'flex';
            if (periodGroup) {
                periodGroup.style.display = 'flex';
                if (periodLabel) periodLabel.textContent = 'Confirmation Bars';
                if (periodInput) periodInput.value = '3';
            }
            if (multGroup) {
                multGroup.style.display = 'none';
            }

            if (secondaryRow) secondaryRow.style.display = 'none';

            if (styleRow) styleRow.style.display = 'flex';
            if (colorGroup) {
                colorGroup.style.display = 'flex';
                if (colorLabel) colorLabel.textContent = 'Marker Badge Color';
                if (colorPicker) colorPicker.value = '#00E676';
                if (colorHex) colorHex.textContent = '#00E676';
            }
            if (overlayGroup) {
                overlayGroup.style.display = 'none';
            }
        } else if (category === 'options') {
            if (periodRow) periodRow.style.display = 'flex';
            if (periodGroup) {
                periodGroup.style.display = 'flex';
                if (periodLabel) periodLabel.textContent = 'Strike Depth Count (ATM +/-)';
                if (periodInput) periodInput.value = '10';
            }
            if (multGroup) {
                multGroup.style.display = 'none';
            }

            if (secondaryRow) secondaryRow.style.display = 'none';

            if (styleRow) styleRow.style.display = 'flex';
            if (colorGroup) {
                colorGroup.style.display = 'flex';
                if (colorLabel) colorLabel.textContent = 'Theme Color';
                if (colorPicker) colorPicker.value = '#FF6D00';
                if (colorHex) colorHex.textContent = '#FF6D00';
            }
            if (overlayGroup) {
                overlayGroup.style.display = 'flex';
                if (displayLabel) displayLabel.textContent = 'Chart Display Mode';
                const overlayRadio = document.querySelector('input[name="create-display-mode"][value="overlay"]');
                if (overlayRadio) overlayRadio.checked = true;
            }
        }

        // Trigger dynamic preset adjustments for active engine
        handleBaseEngineChange();
    }

    function handleBaseEngineChange() {
        const category = document.getElementById('create-study-category')?.value || 'indicators';
        const baseSelect = document.getElementById('create-study-base');
        if (!baseSelect) return;
        const selectedId = baseSelect.value;
        const engines = BASE_ENGINES[category] || [];
        const eng = engines.find(e => e.id === selectedId);
        if (!eng) return;

        const periodInput = document.getElementById('create-param-period');
        const multInput = document.getElementById('create-param-mult');
        const colorPicker = document.getElementById('create-param-color');
        const colorHex = document.getElementById('create-param-color-hex');
        const multGroup = document.getElementById('create-param-mult-group');
        const periodGroup = document.getElementById('create-param-period-group');

        if (eng.defaultPeriod !== undefined && periodInput) {
            periodInput.value = eng.defaultPeriod;
        }
        if (eng.defaultMult !== undefined && multInput) {
            multInput.value = eng.defaultMult;
        }
        if (eng.defaultRows !== undefined && multInput) {
            multInput.value = eng.defaultRows;
        }
        if (eng.defaultColor && colorPicker) {
            colorPicker.value = eng.defaultColor;
            if (colorHex) colorHex.textContent = eng.defaultColor.toUpperCase();
        }

        if (category === 'indicators') {
            if (['vwap'].includes(selectedId)) {
                if (periodGroup) periodGroup.style.display = 'none';
                if (multGroup) multGroup.style.display = 'none';
            } else if (['ema', 'sma', 'rsi', 'stochastic', 'atr'].includes(selectedId)) {
                if (periodGroup) periodGroup.style.display = 'flex';
                if (multGroup) multGroup.style.display = 'none';
            } else {
                if (periodGroup) periodGroup.style.display = 'flex';
                if (multGroup) multGroup.style.display = 'flex';
            }
        }

        if (eng.overlay !== undefined) {
            const targetMode = eng.overlay ? 'overlay' : 'subpane';
            const radio = document.querySelector(`input[name="create-display-mode"][value="${targetMode}"]`);
            if (radio) radio.checked = true;
        }
    }

    async function handleCreateStudySubmit(e) {
        e.preventDefault();
        const category = document.getElementById('create-study-category')?.value || 'indicators';
        const name = (document.getElementById('create-study-name')?.value || '').trim();
        const baseType = document.getElementById('create-study-base')?.value || 'ema';
        const period = parseInt(document.getElementById('create-param-period')?.value || '20', 10);
        const color = document.getElementById('create-param-color')?.value || '#2962FF';
        const mult = parseFloat(document.getElementById('create-param-mult')?.value || '2.0');
        const rows = parseInt(document.getElementById('create-param-rows')?.value || '70', 10);
        const desc = (document.getElementById('create-study-desc')?.value || '').trim();
        const autoApply = document.getElementById('create-study-auto-apply')?.checked !== false;

        let isOverlay = true;
        const checkedMode = document.querySelector('input[name="create-display-mode"]:checked');
        if (checkedMode && checkedMode.value === 'subpane') {
            isOverlay = false;
        } else if (category === 'indicators' && ['rsi', 'macd', 'stochastic', 'atr'].includes(baseType)) {
            isOverlay = false;
        } else if (category === 'options' && baseType === 'opt_pcr') {
            isOverlay = false;
        }

        if (!name) {
            alert("Please enter a name for your custom study.");
            return;
        }

        const studyId = `custom_${category}_${Date.now()}`;
        const inputs = {
            base_type: baseType,
            period: period,
            color: color,
            multiplier: mult,
            stdDev: mult,
            rows: rows,
            valueAreaPct: mult > 1 ? mult / 100 : 0.70
        };

        const newStudy = {
            id: studyId,
            name: name,
            section: "personal",
            category: "technicals",
            sub_category: category,
            description: desc || `Custom ${category.slice(0, -1)} built on ${baseType.toUpperCase()} engine.`,
            author: "Custom User Script",
            overlay: isOverlay,
            default_inputs: inputs,
            tags: ["custom", "personal", category, baseType],
            is_favorite: false,
            is_custom: true,
            base_type: baseType
        };

        // 1. Save to localStorage
        try {
            const raw = localStorage.getItem('tv_user_saved_scripts');
            const saved = raw ? JSON.parse(raw) : [];
            saved.unshift(newStudy);
            localStorage.setItem('tv_user_saved_scripts', JSON.stringify(saved));
        } catch (err) {
            console.error("Error saving custom study to localStorage:", err);
        }

        // 2. Sync to backend API
        try {
            fetch('/api/v1/studies/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newStudy)
            }).catch(e => console.warn("Could not post custom study to backend:", e));
        } catch (err) {
            console.warn("Could not post custom study to backend:", err);
        }

        // 3. Update memory catalog
        if (catalogCache) {
            catalogCache.unshift(newStudy);
        }

        // 4. Update UI
        closeCreateStudyModal();
        selectedStudyId = newStudy.id;
        renderList();

        // 5. Apply immediately if checked
        if (autoApply) {
            applyStudyToChart(newStudy);
        } else {
            showStudyToast(`Created "${newStudy.name}"!`);
        }
    }

    function applyStudyToChart(study) {
        if (!study) return;
        console.log(`[StudyManager] Applying study: ${study.name} (${study.id})`, study);

        // Handle custom study dispatch
        if (study.is_custom && study.base_type) {
            const bt = study.base_type;
            if (study.sub_category === 'patterns' || bt.startsWith('bullish_') || bt.startsWith('bearish_') || bt.startsWith('morning_') || bt.startsWith('evening_') || bt.startsWith('hammer') || bt.startsWith('doji') || bt.startsWith('double_') || bt.startsWith('head_')) {
                if (typeof window.applyChartPattern === 'function') {
                    window.applyChartPattern(bt);
                }
            } else if (study.sub_category === 'strategies' || bt.startsWith('strat_')) {
                if (typeof window.applyChartStrategy === 'function') {
                    window.applyChartStrategy(bt, study.default_inputs);
                }
            } else if (study.sub_category === 'profiles' || bt.includes('vp') || bt.includes('tpo')) {
                if (window.volumeProfileOverlay) {
                    window.volumeProfileOverlay.enable(bt, study.default_inputs);
                }
                if (window.activeStudiesManager) {
                    window.activeStudiesManager.addStudy(bt, study.default_inputs, study.name);
                }
            } else if (study.sub_category === 'options' || bt.startsWith('opt_')) {
                if (typeof window.applyChartOptionsStudy === 'function') {
                    window.applyChartOptionsStudy(bt);
                }
            } else {
                if (window.activeStudiesManager) {
                    window.activeStudiesManager.addStudy(bt, study.default_inputs, study.name);
                }
            }
            showStudyToast(`Applied "${study.name}" to chart`);
            closeStudyDialog();
            return;
        }

        // Handle built-in studies
        if (study.sub_category === 'patterns' || study.id.startsWith('patt_') || study.id.startsWith('pat_')) {
            const patternKey = study.id.replace(/^patt?_/, '');
            if (typeof window.applyChartPattern === 'function') {
                window.applyChartPattern(patternKey);
            }
        } else if (study.sub_category === 'strategies' || study.id.startsWith('strat_')) {
            if (typeof window.applyChartStrategy === 'function') {
                window.applyChartStrategy(study.id, study.default_inputs);
            }
        } else if (study.sub_category === 'options' || study.id.startsWith('opt_')) {
            if (typeof window.applyChartOptionsStudy === 'function') {
                window.applyChartOptionsStudy(study.id);
            }
        } else if (study.sub_category === 'profiles' || study.id.includes('vp') || study.id.includes('tpo')) {
            if (window.volumeProfileOverlay) {
                window.volumeProfileOverlay.enable(study.id, study.default_inputs);
            }
            if (window.activeStudiesManager) {
                window.activeStudiesManager.addStudy(study.id, study.default_inputs, study.name);
            }
        } else if (study.id === 'comm_intraday_momentum') {
            if (window.activeStudiesManager) {
                window.activeStudiesManager.addStudy('vwap', {});
                window.activeStudiesManager.addStudy('ema', { period: 20 });
                window.activeStudiesManager.addStudy('rsi', { period: 14 });
            }
            if (window.volumeProfileOverlay) {
                window.volumeProfileOverlay.enable('visible_range_vp');
            }
        } else if (study.id === 'comm_swing_breakout') {
            if (window.activeStudiesManager) {
                window.activeStudiesManager.addStudy('sma', { period: 50, color: '#2962FF' });
                window.activeStudiesManager.addStudy('sma', { period: 200, color: '#E040FB' });
                window.activeStudiesManager.addStudy('bollinger_bands', {});
            }
            if (typeof window.applyChartPattern === 'function') {
                window.applyChartPattern('bullish_engulfing');
            }
        } else if (study.id === 'comm_options_seller') {
            if (typeof window.applyChartOptionsStudy === 'function') {
                window.applyChartOptionsStudy('opt_max_pain');
                window.applyChartOptionsStudy('opt_strike_oi_profile');
                window.applyChartOptionsStudy('opt_pcr');
            }
        } else if (study.section === 'personal' || (study.default_inputs && Array.isArray(study.default_inputs.studies))) {
            const studiesToLoad = (study.default_inputs && study.default_inputs.studies) || [];
            if (studiesToLoad.length === 0) {
                if (window.activeStudiesManager) {
                    window.activeStudiesManager.addStudy('ema', { period: 20 });
                    window.activeStudiesManager.addStudy('rsi', { period: 14 });
                }
            } else {
                studiesToLoad.forEach(sid => {
                    if (sid === 'visible_range_vp' || sid === 'session_vp' || sid === 'tpo') {
                        if (window.volumeProfileOverlay) window.volumeProfileOverlay.enable(sid);
                    } else if (sid.startsWith('patt_') || sid.startsWith('pat_')) {
                        if (typeof window.applyChartPattern === 'function') window.applyChartPattern(sid.replace(/^patt?_/, ''));
                    } else if (window.activeStudiesManager) {
                        window.activeStudiesManager.addStudy(sid, {});
                    }
                });
            }
        } else {
            if (window.activeStudiesManager && typeof window.activeStudiesManager.addStudy === 'function') {
                window.activeStudiesManager.addStudy(study.id, study.default_inputs, study.name);
            } else {
                if (study.id === 'vwap') {
                    const btn = document.getElementById('btn-overlay-vwap');
                    if (btn && !btn.classList.contains('active')) btn.click();
                } else if (study.id === 'ema') {
                    const btn = document.getElementById('btn-overlay-ema');
                    if (btn && !btn.classList.contains('active')) btn.click();
                }
            }
        }

        // Visual toast confirmation
        showStudyToast(`Applied "${study.name}" to chart`);
        closeStudyDialog();
    }

    function showStudyToast(msg) {
        let toast = document.getElementById('study-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'study-toast';
            toast.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: #1E222D;
                color: #FFFFFF;
                border: 1px solid #2962FF;
                box-shadow: 0 4px 16px rgba(0,0,0,0.5);
                padding: 10px 18px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                z-index: 9999;
                transition: opacity 0.2s;
            `;
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.opacity = '1';
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => { toast.style.display = 'none'; }, 200);
        }, 2200);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // Initialize Event Listeners & Global Event Delegation
    function init() {
        const triggerBtn = document.getElementById('btn-open-studies');
        const closeBtn = document.getElementById('study-modal-close');
        const backdrop = document.getElementById('study-modal-backdrop');
        const searchInput = document.getElementById('study-search-input');
        const searchClear = document.getElementById('study-search-clear');
        const categorySelect = document.getElementById('create-study-category');
        const createForm = document.getElementById('create-study-form');
        const colorPicker = document.getElementById('create-param-color');
        const colorHex = document.getElementById('create-param-color-hex');

        if (triggerBtn) {
            triggerBtn.addEventListener('click', (e) => {
                e.preventDefault();
                openStudyDialog();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', closeStudyDialog);
        }

        // Close on backdrop click (outside click)
        if (backdrop) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    closeStudyDialog();
                }
            });
        }

        // Global Event Delegation for all study modal clicks
        document.addEventListener('click', (e) => {
            // Pill Navigation Clicks (Indicators, Strategies, Profiles, Patterns, Options)
            const pillBtn = e.target.closest('.tv-study-pill-btn');
            if (pillBtn) {
                e.preventDefault();
                activeSubCategory = pillBtn.dataset.sub || 'indicators';
                renderPills();
                renderList();
                return;
            }

            // Sidebar Navigation Clicks
            const navBtn = e.target.closest('.tv-study-nav-item');
            if (navBtn) {
                e.preventDefault();
                activeSection = navBtn.dataset.section || 'builtin';
                activeCategory = navBtn.dataset.category || 'technicals';
                renderSidebar();
                renderPills();
                renderList();
                return;
            }

            // Create button click in toolbar
            const createButton = e.target.closest('#study-create-new-btn');
            if (createButton) {
                e.preventDefault();
                e.stopPropagation();
                const targetCat = (activeCategory === 'my_scripts') ? 'indicators' : activeSubCategory;
                openCreateStudyModal(targetCat);
                return;
            }

            // Create modal close & cancel clicks
            if (e.target.closest('#create-modal-close') || e.target.closest('#create-modal-cancel')) {
                e.preventDefault();
                closeCreateStudyModal();
                return;
            }

            // Backdrop click on create modal
            if (e.target.id === 'study-create-modal') {
                closeCreateStudyModal();
                return;
            }
        });

        // Search Input with Debounce
        let searchTimer = null;
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimer);
                searchQuery = e.target.value;
                if (searchClear) {
                    searchClear.style.display = searchQuery ? 'block' : 'none';
                }
                searchTimer = setTimeout(() => {
                    renderList();
                }, 120);
            });
        }

        if (searchClear) {
            searchClear.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                searchQuery = '';
                searchClear.style.display = 'none';
                renderList();
                if (searchInput) searchInput.focus();
            });
        }

        if (categorySelect) {
            categorySelect.addEventListener('change', (e) => {
                updateCreateModalFields(e.target.value);
            });
        }

        const baseSelect = document.getElementById('create-study-base');
        if (baseSelect) {
            baseSelect.addEventListener('change', handleBaseEngineChange);
        }

        if (colorPicker && colorHex) {
            colorPicker.addEventListener('input', (e) => {
                colorHex.textContent = e.target.value.toUpperCase();
            });
        }

        if (createForm) {
            createForm.addEventListener('submit', handleCreateStudySubmit);
        }

        // Preload catalog
        fetchCatalog();
    }

    // Execute immediately if DOM is ready, or on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
