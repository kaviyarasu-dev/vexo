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
        statusEl.textContent = data.status || "Idle";
        if (data.progress_pct !== undefined) {
            progressEl.value = data.progress_pct;
        }
        speedEl.textContent = data.speed !== undefined ? data.speed : "--";
        quotaEl.textContent = data.quota_used !== undefined ? data.quota_used : "--";
        currentSymbolEl.textContent = data.current_symbol || "None";
    }

    function disconnectSSE() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    }

    document.getElementById('btn-downloader')?.addEventListener('click', () => {
        connectSSE();
    });

    document.getElementById('close-drawer')?.addEventListener('click', disconnectSSE);
    document.getElementById('drawer-backdrop')?.addEventListener('click', disconnectSSE);

    document.getElementById('dl-pause')?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/v1/system/downloader/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'pause' })
            });
            const json = await res.json();
            if (json.success) {
                statusEl.textContent = "Paused";
            }
        } catch (e) {
            console.error("Downloader pause request failed", e);
        }
    });

    document.getElementById('dl-resume')?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/v1/system/downloader/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'resume' })
            });
            const json = await res.json();
            if (json.success) {
                statusEl.textContent = "Resuming...";
            }
        } catch (e) {
            console.error("Downloader resume request failed", e);
        }
    });
});
