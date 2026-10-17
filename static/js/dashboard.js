/**
 * Milma Kottayam Dairy - Live Camera & Color Detection Dashboard
 * Company: Goose Industrial Solutions
 */

document.addEventListener('DOMContentLoaded', () => {
    // Header & Clock
    const clockEl = document.getElementById('clockDisplay');
    const camStatusPill = document.getElementById('camStatusPill');
    const camStatusText = document.getElementById('camStatusText');

    // Source Toggles
    const btnSrcBaumer = document.getElementById('btnSrcBaumer');
    const btnSrcSim = document.getElementById('btnSrcSim');
    const cameraTitle = document.getElementById('cameraTitle');

    // Telemetry
    const telemetryFps = document.getElementById('telemetryFps');
    const telemetryExp = document.getElementById('telemetryExp');

    // Controls
    const exposureRange = document.getElementById('exposureRange');
    const exposureVal = document.getElementById('exposureVal');
    const btnSnapshot = document.getElementById('btnSnapshot');
    const btnFullscreen = document.getElementById('btnFullscreen');
    const liveVideoFeed = document.getElementById('liveVideoFeed');

    // Variant Card
    const variantCard = document.getElementById('variantCard');
    const variantIcon = document.getElementById('variantIcon');
    const variantName = document.getElementById('variantName');
    const variantDesc = document.getElementById('variantDesc');
    const confFill = document.getElementById('confFill');

    // Color Counters
    const countOrange = document.getElementById('countOrange');
    const covOrange = document.getElementById('covOrange');
    const countViolet = document.getElementById('countViolet');
    const covViolet = document.getElementById('covViolet');
    const countGreen = document.getElementById('countGreen');
    const covGreen = document.getElementById('covGreen');

    let isDraggingExposure = false;

    // Clock Updater
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Fetch Live Status
    async function fetchStatus() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();
            updateUI(data);
        } catch (err) {
            console.error('Error fetching camera telemetry:', err);
        }
    }

    function updateUI(data) {
        // 1. Connection & Source Status
        if (data.camera_source === 'baumer') {
            btnSrcBaumer.classList.add('active');
            btnSrcSim.classList.remove('active');

            if (data.camera_connected) {
                camStatusPill.className = 'status-pill';
                camStatusText.textContent = 'BAUMER GIGE ONLINE (169.254.123.85)';
                cameraTitle.textContent = 'Overhead Stream: Baumer VCXG.2-32C (3.2 MP Color)';
            } else {
                camStatusPill.className = 'status-pill offline';
                camStatusText.textContent = 'CONNECTING TO BAUMER...';
                cameraTitle.textContent = 'Searching for Camera on 169.254.123.85...';
            }
        } else {
            btnSrcSim.classList.add('active');
            btnSrcBaumer.classList.remove('active');
            camStatusPill.className = 'status-pill';
            camStatusText.textContent = 'SIMULATED CONVEYOR FEED';
            cameraTitle.textContent = 'Simulated Milma Conveyor Stream';
        }

        // 2. FPS & Exposure
        telemetryFps.textContent = `${data.fps.toFixed(1)} FPS`;
        telemetryExp.textContent = `Exp: ${data.exposure_ms.toFixed(1)} ms`;

        if (!isDraggingExposure && exposureRange) {
            exposureRange.value = data.exposure_ms;
            exposureVal.textContent = Math.round(data.exposure_ms);
        }

        // 3. Dominant Detected Variant Card
        const dom = data.dominant_variant || 'NONE';
        const conf = data.variant_confidence || 0.0;

        variantCard.className = 'variant-result-card';

        if (dom.includes('ORANGE')) {
            variantCard.classList.add('orange');
            variantIcon.textContent = '🟠';
            variantName.textContent = 'ORANGE (Rich Milk 500ml)';
            variantDesc.textContent = `High-Fat Milk Variant • Confidence: ${conf.toFixed(1)}%`;
            confFill.style.width = `${Math.min(100, Math.max(15, conf))}%`;
            confFill.style.background = 'var(--color-orange)';
        } else if (dom.includes('VIOLET')) {
            variantCard.classList.add('violet');
            variantIcon.textContent = '🟣';
            variantName.textContent = 'VIOLET (Toned Milk 500ml)';
            variantDesc.textContent = `Standard Toned Milk • Confidence: ${conf.toFixed(1)}%`;
            confFill.style.width = `${Math.min(100, Math.max(15, conf))}%`;
            confFill.style.background = 'var(--color-violet)';
        } else if (dom.includes('GREEN')) {
            variantCard.classList.add('green');
            variantIcon.textContent = '🟢';
            variantName.textContent = 'GREEN (Smart Milk 500ml)';
            variantDesc.textContent = `Double Toned Milk • Confidence: ${conf.toFixed(1)}%`;
            confFill.style.width = `${Math.min(100, Math.max(15, conf))}%`;
            confFill.style.background = 'var(--color-green)';
        } else {
            variantIcon.textContent = '⚪';
            variantName.textContent = 'NO MILK VARIANT DETECTED';
            variantDesc.textContent = 'Point camera at Milma milk pouches to detect variant';
            confFill.style.width = '0%';
        }

        // 4. Color Counters & Coverage
        const counts = data.color_counts || {};
        const coverage = data.color_coverage || {};

        countOrange.textContent = counts.orange || 0;
        covOrange.textContent = `${(coverage.orange || 0).toFixed(1)}% cov`;

        countViolet.textContent = counts.violet || 0;
        covViolet.textContent = `${(coverage.violet || 0).toFixed(1)}% cov`;

        countGreen.textContent = counts.green || 0;
        covGreen.textContent = `${(coverage.green || 0).toFixed(1)}% cov`;
    }

    // Controls: Source Toggle
    btnSrcBaumer.addEventListener('click', async () => {
        await fetch('/api/set_source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: 'baumer' })
        });
        fetchStatus();
    });

    btnSrcSim.addEventListener('click', async () => {
        await fetch('/api/set_source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: 'simulated' })
        });
        fetchStatus();
    });

    // Exposure Slider
    exposureRange.addEventListener('input', (e) => {
        isDraggingExposure = true;
        exposureVal.textContent = e.target.value;
    });

    exposureRange.addEventListener('change', async (e) => {
        isDraggingExposure = false;
        await fetch('/api/set_exposure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exposure_ms: parseFloat(e.target.value) })
        });
        fetchStatus();
    });

    // Snapshot Download
    btnSnapshot.addEventListener('click', () => {
        const a = document.createElement('a');
        a.href = `/video_feed?t=${Date.now()}`;
        a.download = `milma_camera_capture_${Date.now()}.jpg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    // Fullscreen Toggle
    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            liveVideoFeed.requestFullscreen().catch(err => {
                alert(`Error attempting to enable fullscreen: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    });

    // Initial fetch and 250ms polling loop
    fetchStatus();
    setInterval(fetchStatus, 250);
});
