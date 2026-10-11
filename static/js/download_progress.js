document.addEventListener('DOMContentLoaded', () => {
    const statusEl = document.getElementById('dl-status');
    const progressEl = document.getElementById('dl-progress');
    const speedEl = document.getElementById('dl-speed');
    const quotaEl = document.getElementById('dl-quota');
    const currentSymbolEl = document.getElementById('dl-current-symbol');

    let eventSource = null;

    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }
        
        eventSource = new EventSource('/api/v1/system/downloader/stream');
        
        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                updateTelemetry(data);
            } catch (e) {
                console.error("Failed to parse SSE data", e);
            }
        };

        eventSource.onerror = function(err) {
            console.error("SSE EventSource failed", err);
            statusEl.textContent = "Disconnected";
            eventSource.close();
            // Optional: Reconnect after delay
            // setTimeout(connectSSE, 5000);
        };
    }

    function updateTelemetry(data) {
        statusEl.textContent = data.status || "Running";
        if (data.progress_pct !== undefined) {
            progressEl.value = data.progress_pct;
        }
        speedEl.textContent = data.speed || "--";
        quotaEl.textContent = data.quota_used || "--";
        currentSymbolEl.textContent = data.current_symbol || "None";
    }

    document.getElementById('btn-downloader')?.addEventListener('click', () => {
        // Mock connection setup or use real one
        // connectSSE();
        mockSSE();
    });

    function mockSSE() {
        statusEl.textContent = "Downloading";
        progressEl.value = 45;
        speedEl.textContent = "178";
        quotaEl.textContent = "39,500";
        currentSymbolEl.textContent = "NSE:TCS-EQ (2018-2019)";
    }

    document.getElementById('dl-pause')?.addEventListener('click', async () => {
        try {
            await fetch('/api/v1/system/downloader/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'pause' })
            });
            statusEl.textContent = "Paused";
        } catch (e) {}
    });

    document.getElementById('dl-resume')?.addEventListener('click', async () => {
        try {
            await fetch('/api/v1/system/downloader/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'resume' })
            });
            statusEl.textContent = "Resuming...";
        } catch (e) {}
    });
});
