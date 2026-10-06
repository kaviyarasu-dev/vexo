const chartContainer = document.getElementById('chart');
const tooltip = document.getElementById('tooltip');
const statusEl = document.getElementById('status');
const loader = document.getElementById('loader');
const loaderText = document.getElementById('loader-text');

// Initialize Chart
const chart = LightweightCharts.createChart(chartContainer, {
    width: chartContainer.clientWidth,
    height: chartContainer.clientHeight,
    layout: {
        background: { type: 'solid', color: '#121212' },
        textColor: '#888888',
    },
    grid: {
        vertLines: { color: 'rgba(44, 44, 44, 0.5)' },
        horzLines: { color: 'rgba(44, 44, 44, 0.5)' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    rightPriceScale: {
        borderColor: 'rgba(44, 44, 44, 0.8)',
    },
    timeScale: {
        borderColor: 'rgba(44, 44, 44, 0.8)',
        timeVisible: true,
        secondsVisible: false,
    },
});

// Add Series
const candlestickSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#00c853',
    downColor: '#ff3d00',
    borderDownColor: '#ff3d00',
    borderUpColor: '#00c853',
    wickDownColor: '#ff3d00',
    wickUpColor: '#00c853',
});

const volumeSeries = chart.addSeries(LightweightCharts.HistogramSeries, {
    color: '#26a69a',
    priceFormat: {
        type: 'volume',
    },
    priceScaleId: '', // set as an overlay by setting a blank priceScaleId
    scaleMargins: {
        top: 0.8, // highest point of the series will be at 80% of the chart
        bottom: 0,
    },
});

// Handle resize
new ResizeObserver(entries => {
    if (entries.length === 0 || entries[0].target !== chartContainer) { return; }
    const newRect = entries[0].contentRect;
    chart.applyOptions({ height: newRect.height, width: newRect.width });
}).observe(chartContainer);

// Tooltip logic
chart.subscribeCrosshairMove(param => {
    if (
        param.point === undefined ||
        !param.time ||
        param.point.x < 0 ||
        param.point.x > chartContainer.clientWidth ||
        param.point.y < 0 ||
        param.point.y > chartContainer.clientHeight
    ) {
        tooltip.style.display = 'none';
    } else {
        const data = param.seriesData.get(candlestickSeries);
        const volData = param.seriesData.get(volumeSeries);
        
        if (data) {
            const isUp = data.close >= data.open;
            const colorClass = isUp ? 'val-up' : 'val-down';
            
            let html = `
                <div style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">RELIANCE</div>
                <div>O <span class="${colorClass}">${data.open.toFixed(2)}</span></div>
                <div>H <span class="${colorClass}">${data.high.toFixed(2)}</span></div>
                <div>L <span class="${colorClass}">${data.low.toFixed(2)}</span></div>
                <div>C <span class="${colorClass}">${data.close.toFixed(2)}</span></div>
            `;
            
            if (volData) {
                html += `<div>V <span style="color: #bbb">${(volData.value / 1000).toFixed(2)}K</span></div>`;
            }

            tooltip.innerHTML = html;
            tooltip.style.display = 'block';

            // Position the tooltip to follow the mouse slightly
            const tooltipWidth = 120;
            let left = param.point.x + 15;
            if (left > chartContainer.clientWidth - tooltipWidth) {
                left = param.point.x - tooltipWidth - 15;
            }
            
            let top = param.point.y + 15;
            
            tooltip.style.transform = `translate(${left}px, ${top}px)`;
        } else {
            tooltip.style.display = 'none';
        }
    }
});

// Fetch and Parse CSV
function loadData() {
    loaderText.innerText = 'Downloading CSV (6.7MB)...';
    
    Papa.parse('RELIANCE_5m_data.csv', {
        download: true,
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete: function(results) {
            loaderText.innerText = 'Processing data...';
            
            // Allow UI to update before heavy processing
            setTimeout(() => {
                const data = results.data;
                const candleData = [];
                const volumeData = [];

                for (let i = 0; i < data.length; i++) {
                    const row = data[i];
                    
                    if (!row.datetime) continue;
                    
                    // Replace space with T to make it standard ISO format if needed
                    const dtStr = row.datetime.replace(' ', 'T');
                    const timestamp = Math.floor(new Date(dtStr).getTime() / 1000);
                    
                    if (isNaN(timestamp) || typeof row.open !== 'number' || typeof row.high !== 'number' || typeof row.low !== 'number' || typeof row.close !== 'number') {
                        continue; 
                    }

                    candleData.push({
                        time: timestamp,
                        open: row.open,
                        high: row.high,
                        low: row.low,
                        close: row.close
                    });

                    const isUp = row.close >= row.open;
                    volumeData.push({
                        time: timestamp,
                        value: row.volume || 0,
                        color: isUp ? 'rgba(0, 200, 83, 0.4)' : 'rgba(255, 61, 0, 0.4)'
                    });
                }

                // Sort by time (required by Lightweight Charts)
                candleData.sort((a, b) => a.time - b.time);
                volumeData.sort((a, b) => a.time - b.time);

                // Set Data
                candlestickSeries.setData(candleData);
                volumeSeries.setData(volumeData);
                
                // Fit Content
                chart.timeScale().fitContent();

                // Update UI
                loader.style.display = 'none';
                statusEl.innerHTML = `${candleData.length.toLocaleString()} candles loaded`;
                statusEl.className = 'status success';
                
            }, 50);
        },
        error: function(error) {
            loaderText.innerText = 'Error loading data!';
            console.error('Error parsing CSV:', error);
            statusEl.innerText = 'Failed to load CSV';
        }
    });
}

// Start loading
loadData();
