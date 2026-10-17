/**
 * Milma Kottayam Dairy - Live Camera, YOLO Object Detection & Color Classifier
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

    // Sliders & Controls
    const exposureRange = document.getElementById('exposureRange');
    const exposureVal = document.getElementById('exposureVal');
    const confRange = document.getElementById('confRange');
    const confVal = document.getElementById('confVal');
    const btnSnapshot = document.getElementById('btnSnapshot');
    const btnFullscreen = document.getElementById('btnFullscreen');
    const liveVideoFeed = document.getElementById('liveVideoFeed');

    // Detected Objects Deck
    const detectedChipsContainer = document.getElementById('detectedChipsContainer');
    const totalObjectsBadge = document.getElementById('totalObjectsBadge');

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

    // Clock
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Map object class names to emoji icons
    function getObjectIcon(name) {
        const lower = (name || '').toLowerCase();
        if (lower.includes('scissor')) return '✂️';
        if (lower.includes('bottle')) return '🧴';
        if (lower.includes('cup')) return '☕';
        if (lower.includes('mouse') || lower.includes('cap')) return '🖱️';
        if (lower.includes('phone')) return '📱';
        if (lower.includes('pouch') || lower.includes('milk')) return '🥛';
        if (lower.includes('knife') || lower.includes('blade')) return '🔪';
        if (lower.includes('book')) return '📖';
        if (lower.includes('box')) return '📦';
        return '🔍';
    }

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
                cameraTitle.textContent = 'Overhead Stream: Baumer VCXG.2-32C + YOLOv8 AI';
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
            cameraTitle.textContent = 'Simulated Milma Conveyor Stream + YOLOv8 AI';
        }

        // 2. FPS & Exposure
        telemetryFps.textContent = `${data.fps.toFixed(1)} FPS`;
        telemetryExp.textContent = `Exp: ${data.exposure_ms.toFixed(1)} ms`;

        if (!isDraggingExposure && exposureRange) {
            exposureRange.value = data.exposure_ms;
            exposureVal.textContent = Math.round(data.exposure_ms);
        }

        // 3. Detected Objects Deck
        const objects = data.detected_objects || [];
        totalObjectsBadge.textContent = `${objects.length} Object${objects.length === 1 ? '' : 's'}`;

        if (objects.length === 0) {
            detectedChipsContainer.innerHTML = '<span class="empty-state">No objects currently in camera frame. Place scissors, bottles, cups, or milk pouches in view...</span>';
        } else {
            detectedChipsContainer.innerHTML = objects.map(item => {
                const icon = getObjectIcon(item.object);
                const colorStr = item.color || 'NEUTRAL';
                let tagClass = 'tag-neutral';
                let chipMilmaClass = '';

                if (colorStr.includes('ORANGE')) {
                    tagClass = 'tag-orange';
                    chipMilmaClass = 'milma-chip milma-orange';
                } else if (colorStr.includes('VIOLET')) {
                    tagClass = 'tag-violet';
                    chipMilmaClass = 'milma-chip milma-violet';
                } else if (colorStr.includes('GREEN')) {
                    tagClass = 'tag-green';
                    chipMilmaClass = 'milma-chip milma-green';
                } else if (colorStr.includes('BLUE')) {
                    tagClass = 'tag-blue';
                } else if (colorStr.includes('BLACK')) {
                    tagClass = 'tag-black';
                }

                return `
                    <div class="object-chip ${chipMilmaClass}">
                        <span class="chip-icon">${icon}</span>
                        <span class="chip-obj-name">${item.object}</span>
                        <span class="chip-color-tag ${tagClass}">${colorStr}</span>
                        <span class="chip-conf">${item.confidence}%</span>
                    </div>
                `;
            }).join('');
        }

        // 4. Dominant Detected Variant Card
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

        // 5. Color Counters & Coverage
        const counts = data.color_counts || {};
        const coverage = data.color_coverage || {};

        countOrange.textContent = counts.orange || 0;
        covOrange.textContent = `${(coverage.orange || 0).toFixed(1)}% cov`;

        countViolet.textContent = counts.violet || 0;
        covViolet.textContent = `${(coverage.violet || 0).toFixed(1)}% cov`;

        countGreen.textContent = counts.green || 0;
        covGreen.textContent = `${(coverage.green || 0).toFixed(1)}% cov`;
    }

    // Source Toggle
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

    // Confidence Slider
    confRange.addEventListener('input', (e) => {
        confVal.textContent = e.target.value;
    });

    confRange.addEventListener('change', async (e) => {
        await fetch('/api/set_confidence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confidence: parseFloat(e.target.value) / 100.0 })
        });
        fetchStatus();
    });

    // Snapshot Download
    btnSnapshot.addEventListener('click', () => {
        const a = document.createElement('a');
        a.href = `/video_feed?t=${Date.now()}`;
        a.download = `milma_yolo_capture_${Date.now()}.jpg`;
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
