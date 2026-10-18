/**
 * OrderBlock SMC & Institutional Workstation Controller
 * Features:
 * - Market Breadth real-time progress bar (Advances / Declines)
 * - Top 3 Bullish & Bearish Picks with 2-sector cap
 * - Top 20 Bullish & Bearish Boards with rank deltas and Quick-View triggers
 * - Market X-Ray 200-stock HTML5 Canvas scatter visualizer with High-DPI support,
 *   contender halos, pulsing picks, event-risk markers, and hover inspection tooltips
 * - Sector Flow institutional participation heat-cells
 * - 4-Point Institutional Alignment badge (Board, Sector, Breadth, VWAP)
 * - Automatic 60-second polling and manual refresh
 */

(function () {
    class OrderBlockDashboard {
        constructor() {
            this.pollInterval = 60000; // 60s
            this.pollTimer = null;
            this.cachedBoards = null;
            this.cachedMarketPicture = null;
            this.points = [];
            this.sectors = [];
            this.mappedPoints = [];
            this.hoveredPoint = null;

            // DOM elements
            this.container = null;
            this.canvas = null;
            this.ctx = null;
            this.tooltipEl = null;

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }

        init() {
            this.container = document.getElementById('orderblock-view');
            this.canvas = document.getElementById('market-xray-canvas');
            if (this.canvas) {
                this.ctx = this.canvas.getContext('2d');
                this.setupCanvasInteractions();
            }

            // Setup Refresh Trigger
            const refreshBtn = document.getElementById('btn-orderblock-refresh');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    refreshBtn.classList.add('loading');
                    this.fetchData().finally(() => {
                        setTimeout(() => refreshBtn.classList.remove('loading'), 400);
                    });
                });
            }

            // Hook into Tab Switching
            document.querySelectorAll('.view-tab').forEach(tab => {
                tab.addEventListener('click', (e) => {
                    const view = e.currentTarget.dataset.view;
                    if (view === 'orderblock') {
                        setTimeout(() => {
                            this.resizeCanvas();
                            this.renderMarketXRay();
                        }, 50);
                    }
                });
            });

            // Window resize handler
            window.addEventListener('resize', () => {
                const view = document.getElementById('view-orderblock');
                if (view && !view.classList.contains('hidden')) {
                    this.resizeCanvas();
                    this.renderMarketXRay();
                }
            });

            // Start polling & initial load
            this.fetchData();
            this.startPolling();
        }

        startPolling() {
            if (this.pollTimer) clearInterval(this.pollTimer);
            this.pollTimer = setInterval(() => {
                // Poll if orderblock view is active or periodically in background
                this.fetchData();
            }, this.pollInterval);
        }

        stopPolling() {
            if (this.pollTimer) {
                clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        }

        async fetchData() {
            try {
                const [boardsRes, pictureRes] = await Promise.all([
                    fetch('/api/v1/orderblock/boards').catch(() => null),
                    fetch('/api/v1/orderblock/market-picture').catch(() => null)
                ]);

                if (boardsRes && boardsRes.ok) {
                    const boardsData = await boardsRes.json();
                    if (boardsData.success && boardsData.data) {
                        this.cachedBoards = boardsData.data;
                        this.updateBreadth(this.cachedBoards.market_breadth);
                        this.updatePicks(this.cachedBoards.bullish_picks, this.cachedBoards.bearish_picks);
                        this.updateBoards(this.cachedBoards.bullish_boards, this.cachedBoards.bearish_boards);
                    }
                }

                if (pictureRes && pictureRes.ok) {
                    const picData = await pictureRes.json();
                    if (picData.success && picData.data) {
                        this.cachedMarketPicture = picData.data;
                        this.points = picData.data.points || [];
                        this.sectors = picData.data.sectors || [];
                        this.renderMarketXRay();
                        this.renderSectorFlow(this.sectors, this.points);
                    }
                }

                // Update alignment badge for active chart symbol
                const activeSym = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
                this.updateChartAlignmentBadge(activeSym);
            } catch (err) {
                console.warn('[OrderBlockDashboard] Error fetching market context:', err);
            }
        }

        // =====================================================================
        // Market Breadth Bar
        // =====================================================================
        updateBreadth(breadth) {
            if (!breadth) return;
            const advances = Number(breadth.advances) || 0;
            const declines = Number(breadth.declines) || 0;
            const total = Math.max(1, advances + declines);
            const ratio = (advances / total) * 100.0;
            const declineRatio = 100.0 - ratio;

            const summaryEl = document.getElementById('breadth-summary-text');
            if (summaryEl) {
                summaryEl.textContent = `${advances} Advances (${ratio.toFixed(1)}%) · ${declines} Declines (${declineRatio.toFixed(1)}%)`;
            }

            const barAdv = document.getElementById('breadth-bar-advances');
            const barDec = document.getElementById('breadth-bar-declines');
            if (barAdv) barAdv.style.width = `${ratio}%`;
            if (barDec) barDec.style.width = `${declineRatio}%`;
        }

        // =====================================================================
        // Top 3 Picks Bar
        // =====================================================================
        updatePicks(bullishPicks, bearishPicks) {
            const bullContainer = document.getElementById('bullish-picks-container');
            const bearContainer = document.getElementById('bearish-picks-container');

            const renderPickChips = (container, list, side) => {
                if (!container) return;
                const qualified = (list || []).filter(p => p.status === 'PICKED');
                if (qualified.length === 0) {
                    container.innerHTML = '<span class="text-muted text-xs">No algorithmic picks currently qualified</span>';
                    return;
                }

                container.innerHTML = qualified.map(p => `
                    <div class="pick-chip ${side.toLowerCase()}" data-symbol="${p.symbol}" title="Score: ${Number(p.score).toFixed(2)} · Sector: ${p.sector}">
                        <span class="font-mono font-bold">${p.symbol.replace('NSE:', '').replace('-EQ', '')}</span>
                        <span class="badge-mini">${p.sector || 'Equities'}</span>
                        <span class="font-mono text-xs ${p.day_move_pct >= 0 ? 'text-green' : 'text-red'}">
                            ${p.day_move_pct >= 0 ? '+' : ''}${Number(p.day_move_pct).toFixed(2)}%
                        </span>
                        <span class="badge-pill bg-accent-subtle font-mono">${Number(p.score).toFixed(2)}</span>
                    </div>
                `).join('');

                container.querySelectorAll('.pick-chip').forEach(chip => {
                    chip.addEventListener('click', () => {
                        const sym = chip.dataset.symbol;
                        const pickItem = (list || []).find(p => p.symbol === sym);
                        if (typeof window.openOrderBlockSheet === 'function') {
                            window.openOrderBlockSheet(sym, pickItem || {});
                        }
                    });
                });
            };

            renderPickChips(bullContainer, bullishPicks, 'BULLISH');
            renderPickChips(bearContainer, bearishPicks, 'BEARISH');
        }

        // =====================================================================
        // Top 20 Boards Two-Column Tables
        // =====================================================================
        updateBoards(bullishBoards, bearishBoards) {
            const bullTbody = document.getElementById('tbody-bullish-board');
            const bearTbody = document.getElementById('tbody-bearish-board');

            const renderRows = (tbody, list, side) => {
                if (!tbody) return;
                if (!list || list.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No ${side.toLowerCase()} contenders</td></tr>`;
                    return;
                }

                tbody.innerHTML = list.map(item => {
                    const deltaHtml = item.rank_delta > 0
                        ? `<span class="text-green font-mono">▲+${item.rank_delta}</span>`
                        : (item.rank_delta < 0
                            ? `<span class="text-red font-mono">▼${item.rank_delta}</span>`
                            : `<span class="text-muted font-mono">-</span>`);
                    
                    const newBadge = item.is_new_top10 ? '<span class="badge-mini text-cyan ml-1" title="New Top 10 Entry">NEW</span>' : '';
                    const eventBadge = item.is_event_risk ? '<span class="badge-mini text-amber ml-1" title="High Event Risk / Earnings">⚠️</span>' : '';
                    const cleanSym = item.symbol.replace('NSE:', '').replace('-EQ', '');
                    const priceFormatted = item.current_price ? `₹${Number(item.current_price).toFixed(2)}` : '--';
                    const moveFormatted = `${item.day_move_pct >= 0 ? '+' : ''}${Number(item.day_move_pct).toFixed(2)}%`;
                    const moveClass = item.day_move_pct >= 0 ? 'text-green' : 'text-red';

                    // In-Tile 40-Bucket Volume Profile Micro-Bars & Live Price Marker
                    const summary = item.profile_summary || {};
                    const miniBuckets = Array.isArray(summary.mini_buckets) ? summary.mini_buckets : [];
                    const currentBucketIdx = summary.current_bucket_idx !== undefined ? summary.current_bucket_idx : 20;
                    const pocPrice = summary.poc_price ? `₹${Number(summary.poc_price).toFixed(2)}` : '--';

                    let profileBarsHtml = '';
                    if (miniBuckets.length === 40) {
                        profileBarsHtml = miniBuckets.map((widthPct, idx) => {
                            const isPoc = (widthPct >= 99.9 && widthPct > 0);
                            const sideClass = idx > currentBucketIdx ? 'resistance' : 'support';
                            const pocClass = isPoc ? 'poc is-poc' : '';
                            return `<div class="profile-bar ${sideClass} ${pocClass}" style="width: ${Number(widthPct).toFixed(1)}%;"></div>`;
                        }).join('');
                    } else {
                        profileBarsHtml = Array.from({ length: 40 }).map(() =>
                            '<div class="profile-bar" style="width: 0%;"></div>'
                        ).join('');
                    }

                    const markerPos = Math.min(100, Math.max(0, (currentBucketIdx / 40) * 100));
                    const priceMarkerHtml = `
                        <div class="profile-price-marker" style="bottom: ${markerPos.toFixed(1)}%;" title="Active LTP: ${priceFormatted}">
                            <span class="price-pill">${priceFormatted}</span>
                        </div>
                    `;

                    const profileWrapHtml = `
                        <div class="tile-profile-wrap" title="Volume Profile · POC: ${pocPrice}">
                            ${profileBarsHtml}
                            ${priceMarkerHtml}
                        </div>
                    `;

                    return `
                        <tr data-symbol="${item.symbol}">
                            <td class="font-mono font-bold">${item.rank}</td>
                            <td>${deltaHtml}${newBadge}</td>
                            <td class="font-mono font-semibold">
                                <div>${cleanSym}${eventBadge}</div>
                                ${profileWrapHtml}
                            </td>
                            <td class="text-muted text-xs">${item.sector || 'General'}</td>
                            <td class="font-mono">${priceFormatted}</td>
                            <td class="font-mono ${moveClass}">${moveFormatted}</td>
                            <td class="font-mono font-bold text-accent">${Number(item.score).toFixed(2)}</td>
                            <td>
                                <button class="btn-xs btn-secondary btn-board-quick" data-symbol="${item.symbol}" title="Quick View Sheet">View</button>
                                <button class="btn-xs btn-outline btn-board-chart" data-symbol="${item.symbol}" title="Open Chart">Chart</button>
                            </td>
                        </tr>
                    `;
                }).join('');

                // Bind Action Triggers
                tbody.querySelectorAll('.btn-board-quick').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const sym = btn.dataset.symbol;
                        const item = list.find(x => x.symbol === sym);
                        if (typeof window.openOrderBlockSheet === 'function') {
                            window.openOrderBlockSheet(sym, item || {});
                        }
                    });
                });

                tbody.querySelectorAll('.btn-board-chart').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const sym = btn.dataset.symbol;
                        if (typeof window.switchChartSymbol === 'function') {
                            window.switchChartSymbol(sym);
                        }
                        if (typeof window.switchAppView === 'function') {
                            window.switchAppView('chart');
                        }
                    });
                });
            };

            renderRows(bullTbody, bullishBoards, 'BULLISH');
            renderRows(bearTbody, bearishBoards, 'BEARISH');
        }

        // =====================================================================
        // Market X-Ray HTML5 Canvas Scatter Visualizer
        // =====================================================================
        setupCanvasInteractions() {
            if (!this.canvas) return;

            // Ensure parent wrapper is relative for tooltip positioning
            const wrap = this.canvas.parentElement;
            if (wrap) wrap.style.position = 'relative';

            // Create Tooltip DOM if not already present
            this.tooltipEl = document.getElementById('xray-tooltip');
            if (!this.tooltipEl && wrap) {
                this.tooltipEl = document.createElement('div');
                this.tooltipEl.id = 'xray-tooltip';
                this.tooltipEl.className = 'xray-canvas-tooltip hidden';
                wrap.appendChild(this.tooltipEl);
            }

            this.canvas.addEventListener('mousemove', (e) => this.handleCanvasMouseMove(e));
            this.canvas.addEventListener('mouseleave', () => this.handleCanvasMouseLeave());
            this.canvas.addEventListener('click', () => this.handleCanvasClick());
        }

        resizeCanvas() {
            if (!this.canvas) return;
            const wrap = this.canvas.parentElement;
            const cssWidth = wrap ? Math.max(540, wrap.clientWidth - 28) : 600;
            const cssHeight = 320;
            const dpr = window.devicePixelRatio || 1;

            this.canvas.width = Math.floor(cssWidth * dpr);
            this.canvas.height = Math.floor(cssHeight * dpr);
            this.canvas.style.width = `${cssWidth}px`;
            this.canvas.style.height = `${cssHeight}px`;

            if (this.ctx) {
                this.ctx.resetTransform();
                this.ctx.scale(dpr, dpr);
            }
        }

        mapCoordinates(dayMovePct, strengthScore, width, height, padding = 42) {
            const clampedMove = Math.max(-6.0, Math.min(6.0, Number(dayMovePct) || 0));
            const usableW = width - (2 * padding);
            const x = padding + ((clampedMove + 6.0) / 12.0) * usableW;

            const clampedStrength = Math.max(0.0, Math.min(5.0, Number(strengthScore) || 0));
            const usableH = height - (2 * padding);
            const y = (height - padding) - (clampedStrength / 5.0) * usableH;

            return { x, y };
        }

        renderMarketXRay() {
            if (!this.canvas || !this.ctx) return;
            const ctx = this.ctx;
            const width = parseFloat(this.canvas.style.width) || 600;
            const height = parseFloat(this.canvas.style.height) || 320;
            const padding = 42;

            // Clear Background
            ctx.fillStyle = '#090d16';
            ctx.fillRect(0, 0, width, height);

            // Quadrant Watermarks
            ctx.font = '600 11px Inter, sans-serif';
            ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
            ctx.fillText('BULL ACCELERATION (+)', width - padding - 140, padding + 18);

            ctx.fillStyle = 'rgba(239, 68, 68, 0.12)';
            ctx.fillText('BEAR ACCELERATION (-)', padding + 8, padding + 18);

            // Draw Y-Axis Gridlines & Labels
            const yStep = (height - (2 * padding)) / 5;
            for (let i = 0; i <= 5; i++) {
                const y = (height - padding) - (i * yStep);
                ctx.beginPath();
                ctx.strokeStyle = i === 2 ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.06)';
                ctx.lineWidth = i === 2 ? 1.5 : 1;
                ctx.moveTo(padding, y);
                ctx.lineTo(width - padding, y);
                ctx.stroke();

                ctx.font = '10px Inter, monospace';
                ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
                ctx.textAlign = 'right';
                ctx.fillText(i.toFixed(1), padding - 8, y + 3);
            }

            // Draw Center Zero Line (X = 0%)
            const zeroX = padding + (usableW => usableW * 0.5)(width - (2 * padding));
            ctx.beginPath();
            ctx.setLineDash([4, 4]);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.lineWidth = 1;
            ctx.moveTo(zeroX, padding);
            ctx.lineTo(zeroX, height - padding);
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw X-Axis Labels
            const xLabels = [
                { val: -6, text: '-6%' },
                { val: -3, text: '-3%' },
                { val: 0, text: '0%' },
                { val: 3, text: '+3%' },
                { val: 6, text: '+6%' }
            ];
            ctx.textAlign = 'center';
            xLabels.forEach(lbl => {
                const { x } = this.mapCoordinates(lbl.val, 0, width, height, padding);
                ctx.fillStyle = 'rgba(148, 163, 184, 0.7)';
                ctx.fillText(lbl.text, x, height - padding + 16);
            });

            // Map and Render Points
            this.mappedPoints = [];
            if (!this.points || this.points.length === 0) {
                ctx.fillStyle = 'rgba(148, 163, 184, 0.4)';
                ctx.font = '12px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('No market snapshot points loaded', width / 2, height / 2);
                return;
            }

            // Map coordinates for all 200 points
            this.points.forEach(p => {
                const coords = this.mapCoordinates(p.day_move_pct, p.strength_score, width, height, padding);
                this.mappedPoints.push({
                    ...p,
                    canvasX: coords.x,
                    canvasY: coords.y,
                    radius: p.is_pick ? 8 : (p.is_contender ? 6 : 3.5)
                });
            });

            // Pass 1: Normal Equities (Muted)
            this.mappedPoints.filter(p => !p.is_contender && !p.is_pick).forEach(p => {
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = p.day_move_pct >= 0 ? 'rgba(16, 185, 129, 0.45)' : 'rgba(239, 68, 68, 0.45)';
                ctx.fill();
            });

            // Pass 2: Contenders (40 Stocks with Glowing Halos)
            this.mappedPoints.filter(p => p.is_contender && !p.is_pick).forEach(p => {
                const isBull = (p.side === 'BULLISH' || p.day_move_pct >= 0);
                // Halo
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, 12, 0, Math.PI * 2);
                ctx.fillStyle = isBull ? 'rgba(6, 182, 212, 0.22)' : 'rgba(245, 158, 11, 0.22)';
                ctx.fill();

                // Core
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = isBull ? '#06b6d4' : '#f59e0b';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1;
                ctx.stroke();
            });

            // Pass 3: Top Picks (Pulsing Outer Rings & Symbol Labels)
            this.mappedPoints.filter(p => p.is_pick).forEach(p => {
                const isBull = (p.side === 'BULLISH' || p.day_move_pct >= 0);
                const pickColor = isBull ? '#10b981' : '#ef4444';

                // Outer pulsing ring
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, 14, 0, Math.PI * 2);
                ctx.strokeStyle = pickColor;
                ctx.lineWidth = 2;
                ctx.stroke();

                // Inner core
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = pickColor;
                ctx.fill();
                ctx.fillStyle = '#ffffff';
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, 3, 0, Math.PI * 2);
                ctx.fill();

                // Symbol text above pick
                const symText = p.symbol.replace('NSE:', '').replace('-EQ', '');
                ctx.font = 'bold 10px Inter, monospace';
                ctx.textAlign = 'center';
                ctx.fillStyle = '#ffffff';
                ctx.fillText(symText, p.canvasX, p.canvasY - 16);
            });

            // Pass 4: Event Risk Marker
            this.mappedPoints.filter(p => p.is_event_risk).forEach(p => {
                ctx.beginPath();
                ctx.arc(p.canvasX, p.canvasY, p.radius + 2, 0, Math.PI * 2);
                ctx.strokeStyle = '#f59e0b';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            });

            // Pass 5: Hovered Highlight
            if (this.hoveredPoint) {
                ctx.beginPath();
                ctx.arc(this.hoveredPoint.canvasX, this.hoveredPoint.canvasY, this.hoveredPoint.radius + 5, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }

        // =====================================================================
        // Canvas Mouse Events & Inspection Tooltip
        // =====================================================================
        handleCanvasMouseMove(e) {
            if (!this.canvas || this.mappedPoints.length === 0) return;
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            let closest = null;
            let minDist = 14;

            for (const p of this.mappedPoints) {
                const dist = Math.hypot(p.canvasX - mouseX, p.canvasY - mouseY);
                if (dist < minDist) {
                    minDist = dist;
                    closest = p;
                }
            }

            if (closest !== this.hoveredPoint) {
                this.hoveredPoint = closest;
                this.renderMarketXRay();
            }

            if (closest) {
                this.canvas.style.cursor = 'pointer';
                this.showTooltip(closest, e.clientX, e.clientY);
            } else {
                this.canvas.style.cursor = 'default';
                this.hideTooltip();
            }
        }

        handleCanvasMouseLeave() {
            if (this.hoveredPoint) {
                this.hoveredPoint = null;
                this.renderMarketXRay();
            }
            this.hideTooltip();
        }

        handleCanvasClick() {
            if (this.hoveredPoint) {
                if (typeof window.openOrderBlockSheet === 'function') {
                    window.openOrderBlockSheet(this.hoveredPoint.symbol, this.hoveredPoint);
                }
            }
        }

        showTooltip(p, clientX, clientY) {
            if (!this.tooltipEl) return;
            const cleanSym = p.symbol.replace('NSE:', '').replace('-EQ', '');
            const moveFormatted = `${p.day_move_pct >= 0 ? '+' : ''}${Number(p.day_move_pct).toFixed(2)}%`;
            const moveClass = p.day_move_pct >= 0 ? 'text-green' : 'text-red';
            const statusBadge = p.is_pick 
                ? '<span class="badge-mini text-cyan font-bold">⭐ PICK</span>' 
                : (p.is_contender ? '<span class="badge-mini text-accent">CONTENDER</span>' : '');
            
            const align = this.computeAlignment(p);

            this.tooltipEl.innerHTML = `
                <div class="font-mono font-bold text-sm mb-1">${cleanSym} ${statusBadge}</div>
                <div class="text-xs text-muted mb-1">${p.sector || 'Equities'} · ₹${p.current_price ? Number(p.current_price).toFixed(2) : '--'}</div>
                <div class="font-mono text-xs mb-1">Move: <span class="${moveClass} font-bold">${moveFormatted}</span> · Score: <span class="text-accent font-bold">${Number(p.strength_score).toFixed(2)}</span></div>
                <div class="mt-1">
                    <span class="badge-mini ${align.color === 'green' ? 'text-green' : (align.color === 'yellow' ? 'text-gold' : 'text-muted')} font-mono">
                        ${align.badge}
                    </span>
                </div>
            `;

            // Position tooltip relative to container
            const wrap = this.canvas.parentElement;
            if (wrap) {
                const wrapRect = wrap.getBoundingClientRect();
                let x = clientX - wrapRect.left + 15;
                let y = clientY - wrapRect.top - 20;

                if (x + 180 > wrapRect.width) x -= 190;
                if (y + 100 > wrapRect.height) y -= 60;

                this.tooltipEl.style.left = `${Math.max(5, x)}px`;
                this.tooltipEl.style.top = `${Math.max(5, y)}px`;
            }

            this.tooltipEl.classList.remove('hidden');
        }

        hideTooltip() {
            if (this.tooltipEl) this.tooltipEl.classList.add('hidden');
        }

        // =====================================================================
        // Sector Flow Heat-Bars
        // =====================================================================
        renderSectorFlow(sectors, points) {
            const container = document.getElementById('sector-flow-container');
            if (!container) return;

            if (!points || points.length === 0) {
                container.innerHTML = '<span class="text-muted text-xs">Loading sector flow...</span>';
                return;
            }

            // Aggregate metrics by sector
            const sectorMap = {};
            points.forEach(p => {
                const sec = p.sector || 'General';
                if (!sectorMap[sec]) {
                    sectorMap[sec] = {
                        sector: sec,
                        stocks: [],
                        greenCount: 0,
                        redCount: 0,
                        scores: []
                    };
                }
                const move = Number(p.day_move_pct) || 0;
                const score = Number(p.strength_score) || 0;
                if (move > 0) sectorMap[sec].greenCount++;
                else if (move < 0) sectorMap[sec].redCount++;
                sectorMap[sec].scores.push(p.side === 'BULLISH' ? score : -score);
                sectorMap[sec].stocks.push({
                    symbol: p.symbol,
                    move: move,
                    score: score
                });
            });

            const aggregated = Object.values(sectorMap).map(sec => {
                const total = sec.stocks.length;
                const avgScore = total ? (sec.scores.reduce((a, b) => a + b, 0) / total) : 0;
                return {
                    ...sec,
                    total,
                    avgScore: Math.round(avgScore * 100) / 100,
                    participationPct: Math.round((sec.greenCount / Math.max(1, total)) * 100)
                };
            });

            // Sort by net strength score descending
            aggregated.sort((a, b) => b.avgScore - a.avgScore);

            container.innerHTML = aggregated.map(sec => {
                const cellsHtml = sec.stocks.map(stk => `
                    <div class="stock-heat-cell ${stk.move >= 0 ? 'green' : 'red'}"
                         data-symbol="${stk.symbol}"
                         title="${stk.symbol.replace('NSE:', '').replace('-EQ', '')}: ${stk.move >= 0 ? '+' : ''}${stk.move.toFixed(2)}% (Score: ${stk.score.toFixed(2)})">
                    </div>
                `).join('');

                const avgMoveColor = sec.avgScore >= 0 ? 'text-green' : 'text-red';

                return `
                    <div class="sector-bar-row">
                        <div class="sector-info">
                            <span class="font-bold text-xs">${sec.sector}</span>
                            <span class="font-mono text-xs ${avgMoveColor} ml-2">${sec.avgScore >= 0 ? '+' : ''}${sec.avgScore.toFixed(2)}</span>
                            <span class="text-muted text-xs ml-1">(${sec.greenCount}G / ${sec.redCount}R)</span>
                        </div>
                        <div class="stock-heat-cells">
                            ${cellsHtml}
                        </div>
                    </div>
                `;
            }).join('');

            // Bind click on individual heat cells
            container.querySelectorAll('.stock-heat-cell').forEach(cell => {
                cell.addEventListener('click', (e) => {
                    const sym = cell.dataset.symbol;
                    const pt = points.find(p => p.symbol === sym);
                    if (typeof window.openOrderBlockSheet === 'function') {
                        window.openOrderBlockSheet(sym, pt || {});
                    }
                });
            });
        }

        // =====================================================================
        // 4-Point Institutional Alignment Logic & Interactive Popover
        // =====================================================================
        computeAlignment(point) {
            if (!point) {
                return {
                    score: 0,
                    badge: '≤2/4 Pass (0/4)',
                    color: 'dim',
                    action: 'PASS',
                    details: {
                        symbol: '--',
                        board: { pass: false, name: 'Board Presence', label: 'Outside Top 20', sub: 'Not in current institutional focus list', status: 'NOT IN TOP 20' },
                        sector: { pass: false, name: 'Sector Flow', label: 'Sector Divergence', sub: 'Stock move conflicts with sector flow', status: 'DIVERGENT' },
                        breadth: { pass: false, name: 'Market Breadth', label: 'Opposing Market Tide', sub: 'NSE breadth ratio conflicting', status: 'OPPOSING' },
                        vwap: { pass: false, name: 'VWAP Strength', label: 'Below Anchor Threshold', sub: 'Score < 1.50 threshold', status: 'BELOW ANCHOR' },
                        advice: 'PASS — No institutional edge. Avoid retail trap trades.',
                        adviceClass: 'advice-pass'
                    }
                };
            }

            // 1. Board presence (Contender or Pick)
            const isTop20 = Boolean(point.is_contender || point.is_pick);
            const boardSub = point.is_pick ? 'Top High-Conviction Pick' : (point.is_contender ? 'Top 20 Intraday Contender' : 'Not in Top 20 Contenders');
            const boardLabel = isTop20 ? 'Institutional Focus List' : 'Outside Main Focus';

            // 2. Sector Concordance (Stock move aligns with sector average)
            const sec = this.sectors.find(s => s.sector === point.sector);
            const secMove = sec ? sec.move_pct : 0;
            const sectorConcordant = (point.day_move_pct >= 0 && secMove >= 0) || (point.day_move_pct < 0 && secMove < 0);
            const secName = point.sector || 'Equities';
            const secMoveFormatted = `${secMove >= 0 ? '+' : ''}${secMove.toFixed(1)}%`;
            const stockMoveFormatted = `${point.day_move_pct >= 0 ? '+' : ''}${Number(point.day_move_pct || 0).toFixed(1)}%`;
            const sectorSub = `${secName} (${secMoveFormatted}) · Stock (${stockMoveFormatted})`;

            // 3. Breadth Concordance (>55% directional bias)
            let breadthConcordant = false;
            let ratio = 50.0;
            if (this.cachedBoards && this.cachedBoards.market_breadth) {
                ratio = this.cachedBoards.market_breadth.ratio;
                if (point.day_move_pct >= 0 && ratio > 55.0) breadthConcordant = true;
                if (point.day_move_pct < 0 && ratio < 45.0) breadthConcordant = true;
            } else {
                breadthConcordant = true;
            }
            const breadthSub = `NSE Advances: ${ratio.toFixed(1)}% (${ratio > 55.0 ? 'Bullish Tide' : (ratio < 45.0 ? 'Bearish Tide' : 'Mixed / Neutral')})`;

            // 4. VWAP Concordance (Price > VWAP or strong strength score >= 1.5)
            const strengthScore = Number(point.strength_score || 0);
            const vwapConcordant = strengthScore >= 1.5;
            const vwapSub = `Intraday Score: ${strengthScore.toFixed(2)} (Req: ≥ 1.50)`;

            const score = (isTop20 ? 1 : 0) + (sectorConcordant ? 1 : 0) + (breadthConcordant ? 1 : 0) + (vwapConcordant ? 1 : 0);

            let badge, color, action, advice, adviceClass;
            if (score === 4) {
                badge = '4/4 Full Edge';
                color = 'green';
                action = 'FULL_SIZE';
                advice = 'FULL SIZE — All 4 institutional pillars aligned with maximum edge.';
                adviceClass = 'advice-full';
            } else if (score === 3) {
                badge = '3/4 Half Size';
                color = 'yellow';
                action = 'HALF_SIZE';
                advice = 'HALF SIZE — 3 pillars aligned. Moderate edge; trade with controlled risk.';
                adviceClass = 'advice-half';
            } else {
                badge = `≤2/4 Pass (${score}/4)`;
                color = 'dim';
                action = 'PASS';
                advice = 'PASS — Conflicting sector or market forces. High retail trap risk.';
                adviceClass = 'advice-pass';
            }

            return {
                score,
                badge,
                color,
                action,
                details: {
                    symbol: point.symbol,
                    board: {
                        pass: isTop20,
                        name: 'Board Presence',
                        label: boardLabel,
                        sub: boardSub,
                        status: isTop20 ? 'ALIGNED' : 'NOT IN TOP 20'
                    },
                    sector: {
                        pass: sectorConcordant,
                        name: 'Sector Flow',
                        label: `${secName} Flow`,
                        sub: sectorSub,
                        status: sectorConcordant ? 'ALIGNED' : 'DIVERGENT'
                    },
                    breadth: {
                        pass: breadthConcordant,
                        name: 'Market Breadth',
                        label: 'NSE Market Breadth',
                        sub: breadthSub,
                        status: breadthConcordant ? 'ALIGNED' : 'OPPOSING'
                    },
                    vwap: {
                        pass: vwapConcordant,
                        name: 'VWAP Strength',
                        label: 'Institutional Anchor',
                        sub: vwapSub,
                        status: vwapConcordant ? 'ABOVE ANCHOR' : 'BELOW ANCHOR'
                    },
                    advice,
                    adviceClass
                }
            };
        }

        bindAlignmentPopoverAndDrawer() {
            const badge = document.getElementById('chart-alignment-badge');
            const popover = document.getElementById('chart-alignment-popover');
            if (!badge || !popover || this.popoverEventsBound) return;
            this.popoverEventsBound = true;

            let hideTimeout = null;

            const showPopover = () => {
                if (hideTimeout) clearTimeout(hideTimeout);
                this.renderAlignmentPopover();
                popover.classList.remove('hidden');
            };

            const scheduleHide = () => {
                hideTimeout = setTimeout(() => {
                    popover.classList.add('hidden');
                }, 150);
            };

            badge.addEventListener('mouseenter', showPopover);
            badge.addEventListener('mouseleave', scheduleHide);
            popover.addEventListener('mouseenter', () => {
                if (hideTimeout) clearTimeout(hideTimeout);
            });
            popover.addEventListener('mouseleave', scheduleHide);

            // Click on badge to open Quick-View Drawer
            badge.addEventListener('click', (e) => {
                e.stopPropagation();
                popover.classList.add('hidden');
                const sym = window.currentActiveSymbol || (this.currentActivePoint && this.currentActivePoint.symbol) || 'NSE:RELIANCE-EQ';
                let pt = this.points.find(p => p.symbol === sym) || this.currentActivePoint || {};
                if (typeof window.openOrderBlockSheet === 'function') {
                    window.openOrderBlockSheet(sym, pt);
                }
            });
        }

        renderAlignmentPopover() {
            const sym = window.currentActiveSymbol || (this.currentActivePoint && this.currentActivePoint.symbol) || 'NSE:RELIANCE-EQ';
            let pt = this.points.find(p => p.symbol === sym) || this.currentActivePoint || {};
            const align = this.computeAlignment(pt);
            const d = align.details || {};

            const titleElem = document.getElementById('popover-symbol-title');
            const scoreBadgeElem = document.getElementById('popover-score-badge');
            const listElem = document.getElementById('popover-checklist');
            const adviceElem = document.getElementById('popover-advice-banner');

            if (titleElem) titleElem.textContent = sym;
            if (scoreBadgeElem) {
                scoreBadgeElem.textContent = align.badge;
                scoreBadgeElem.className = `popover-score-badge font-mono ${align.color === 'green' ? 'edge-full' : (align.color === 'yellow' ? 'edge-half' : 'edge-pass')}`;
            }

            if (listElem) {
                const items = [d.board, d.sector, d.breadth, d.vwap].filter(Boolean);
                listElem.innerHTML = items.map(item => `
                    <div class="popover-check-row">
                        <span class="popover-check-icon">${item.pass ? '✅' : '❌'}</span>
                        <div class="popover-check-content">
                            <div class="popover-check-label-row">
                                <span class="popover-check-name">${item.name}</span>
                                <span class="popover-check-status ${item.pass ? 'status-pass' : 'status-fail'}">${item.status}</span>
                            </div>
                            <span class="popover-check-sub font-mono">${item.sub}</span>
                        </div>
                    </div>
                `).join('');
            }

            if (adviceElem) {
                adviceElem.className = `popover-advice-banner ${d.adviceClass || 'advice-pass'}`;
                adviceElem.textContent = d.advice || 'PASS — No institutional edge.';
            }
        }

        updateChartAlignmentBadge(symbol) {
            const badge = document.getElementById('chart-alignment-badge');
            if (!badge) return;

            let pt = this.points.find(p => p.symbol === symbol);
            if (!pt && this.points.length > 0) pt = this.points[0];
            this.currentActivePoint = pt;

            const align = this.computeAlignment(pt);
            badge.textContent = align.badge;
            badge.className = `alignment-badge-chip font-mono ${align.color === 'green' ? 'edge-full' : (align.color === 'yellow' ? 'edge-half' : 'edge-pass')}`;
            badge.title = `4-Point Institutional Alignment for ${symbol}: ${align.badge} · Click for SMC Drawer`;

            this.bindAlignmentPopoverAndDrawer();
        }
    }

    // Expose Global Singletons
    window.OrderBlockDashboard = OrderBlockDashboard;
    window.orderBlockDashboard = new OrderBlockDashboard();
})();
