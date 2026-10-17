/**
 * Milma Kottayam Dairy - Operator HMI Dashboard Frontend Logic
 * Company: Goose Industrial Solutions
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const clockEl = document.getElementById('clockDisplay');
    const conveyorStatusPill = document.getElementById('conveyorStatusPill');
    const conveyorStatusText = document.getElementById('conveyorStatusText');

    // KPI Elements
    const kpiTotalPouches = document.getElementById('kpiTotalPouches');
    const kpiTotalCrates = document.getElementById('kpiTotalCrates');
    const kpiPassedCrates = document.getElementById('kpiPassedCrates');
    const kpiFailedCrates = document.getElementById('kpiFailedCrates');
    const kpiAccuracy = document.getElementById('kpiAccuracy');
    const kpiSpeed = document.getElementById('kpiSpeed');

    // Telemetry Elements
    const telemetryLatency = document.getElementById('telemetryLatency');
    const telemetryFps = document.getElementById('telemetryFps');

    // Verdict Elements
    const verdictBox = document.getElementById('verdictBox');
    const verdictTitle = document.getElementById('verdictTitle');
    const verdictSubtitle = document.getElementById('verdictSubtitle');
    const verdictIcon = document.getElementById('verdictIcon');
    const crateTimestamp = document.getElementById('crateTimestamp');
    const crateIdEl = document.getElementById('crateId');
    const crateCountEl = document.getElementById('crateCount');
    const crateDiffEl = document.getElementById('crateDiff');

    // Variant Card Elements
    const variantChip = document.getElementById('variantChip');
    const chipColorDot = document.getElementById('chipColorDot');
    const chipTitle = document.getElementById('chipTitle');
    const variantConf = document.getElementById('variantConf');

    // Progress Bars
    const countOrange = document.getElementById('countOrange');
    const countViolet = document.getElementById('countViolet');
    const countGreen = document.getElementById('countGreen');
    const barOrange = document.getElementById('barOrange');
    const barViolet = document.getElementById('barViolet');
    const barGreen = document.getElementById('barGreen');

    // Table Body
    const incidentTableBody = document.getElementById('incidentTableBody');

    // Controls
    const btnToggleConveyor = document.getElementById('btnToggleConveyor');
    const btnToggleText = document.getElementById('btnToggleText');
    const btnTriggerCrate = document.getElementById('btnTriggerCrate');
    const btnInjectUnderfill = document.getElementById('btnInjectUnderfill');
    const variantSelect = document.getElementById('variantSelect');
    const speedSlider = document.getElementById('speedSlider');
    const speedDisplay = document.getElementById('speedDisplay');
    const btnResetShift = document.getElementById('btnResetShift');

    // Camera Source & Exposure Elements
    const btnSrcSim = document.getElementById('btnSrcSim');
    const btnSrcBaumer = document.getElementById('btnSrcBaumer');
    const streamSourceTitle = document.getElementById('streamSourceTitle');
    const cameraExposureGroup = document.getElementById('cameraExposureGroup');
    const conveyorControlGroup = document.getElementById('conveyorControlGroup');
    const speedSliderGroup = document.getElementById('speedSliderGroup');
    const exposureSlider = document.getElementById('exposureSlider');
    const exposureDisplay = document.getElementById('exposureDisplay');
    const btnCaptureSnap = document.getElementById('btnCaptureSnap');

    // Modal
    const snapshotModal = document.getElementById('snapshotModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalSnapshotImg = document.getElementById('modalSnapshotImg');
    const modalMeta = document.getElementById('modalMeta');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const modalDismissBtn = document.getElementById('modalDismissBtn');

    // Real-Time Clock
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Data Polling
    async function fetchDashboardStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();
            renderDashboard(data);
        } catch (err) {
            console.error('Error fetching dashboard stats:', err);
        }
    }

    let isDraggingExposure = false;

    // Render Data onto UI
    function renderDashboard(data) {
        // 0. Camera Source State
        if (data.camera_source === 'baumer') {
            btnSrcBaumer.classList.add('active');
            btnSrcSim.classList.remove('active');
            const connStr = data.baumer_connected ? '🟢 ONLINE (169.254.123.85)' : '🟡 CONNECTING...';
            streamSourceTitle.textContent = `Physical Camera: Baumer VCXG.2-32C • ${connStr}`;
            cameraExposureGroup.style.display = 'flex';
            conveyorControlGroup.style.opacity = '0.35';
            conveyorControlGroup.style.pointerEvents = 'none';
            if (exposureSlider && !isDraggingExposure) {
                exposureSlider.value = data.baumer_exposure_ms;
                exposureDisplay.textContent = Math.round(data.baumer_exposure_ms);
            }
        } else {
            btnSrcSim.classList.add('active');
            btnSrcBaumer.classList.remove('active');
            streamSourceTitle.textContent = 'Overhead Camera Feed (Simulated Conveyor)';
            cameraExposureGroup.style.display = 'none';
            conveyorControlGroup.style.opacity = '1';
            conveyorControlGroup.style.pointerEvents = 'auto';
        }

        // 1. Conveyor State
        if (data.conveyor_running) {
            conveyorStatusPill.className = 'status-pill active';
            conveyorStatusText.textContent = `LINE RUNNING (${data.crates_per_minute} CPM)`;
            btnToggleText.textContent = 'Pause Line';
        } else {
            conveyorStatusPill.className = 'status-pill paused';
            conveyorStatusText.textContent = 'LINE PAUSED';
            btnToggleText.textContent = 'Resume Line';
        }

        // 2. KPI Cards
        const shift = data.shift_stats;
        kpiTotalPouches.textContent = shift.total_pouches.toLocaleString();
        kpiTotalCrates.textContent = shift.total_crates.toLocaleString();
        kpiPassedCrates.textContent = shift.passed_crates.toLocaleString();
        kpiFailedCrates.textContent = shift.failed_crates.toLocaleString();
        kpiAccuracy.textContent = `${shift.accuracy_pct}%`;
        kpiSpeed.innerHTML = `${data.crates_per_minute.toFixed(1)} <span class="unit">cpm</span>`;

        // Accuracy Color Tagging
        if (shift.accuracy_pct >= 99.0) {
            kpiAccuracy.className = 'kpi-value text-success';
        } else {
            kpiAccuracy.className = 'kpi-value text-danger';
        }

        // 3. Latest Crate Verdict
        const latest = data.latest_crate;
        if (latest) {
            crateIdEl.textContent = latest.crate_id;
            crateTimestamp.textContent = latest.timestamp;
            crateCountEl.textContent = `${latest.total_pouches} / ${latest.expected_count}`;
            const diff = latest.total_pouches - latest.expected_count;
            crateDiffEl.textContent = diff === 0 ? '0 (Exact)' : (diff > 0 ? `+${diff}` : `${diff}`);

            telemetryLatency.textContent = `Latency: ${latest.latency_ms} ms`;
            const fps = latest.latency_ms > 0 ? (1000 / latest.latency_ms).toFixed(1) : 30.0;
            telemetryFps.textContent = `${fps} FPS`;

            if (latest.is_passed) {
                verdictBox.className = 'verdict-box passed';
                verdictIcon.textContent = '✓';
                verdictTitle.textContent = 'PASSED';
                verdictSubtitle.textContent = `Full Crate (20 / 20 Pouches)`;
            } else {
                verdictBox.className = 'verdict-box alert';
                verdictIcon.textContent = '⚠';
                verdictTitle.textContent = latest.status.toUpperCase();
                verdictSubtitle.textContent = `Defect Detected (${latest.total_pouches} / ${latest.expected_count} Packets)`;
            }

            // Variant Chip
            updateVariantChip(latest.variant, latest.variant_confidence);
        }

        // 4. Variant Production Distribution
        const vt = shift.variant_totals;
        const totalPouches = Math.max(1, shift.total_pouches);

        countOrange.textContent = `${vt.orange.toLocaleString()} pkts`;
        countViolet.textContent = `${vt.violet.toLocaleString()} pkts`;
        countGreen.textContent = `${vt.green.toLocaleString()} pkts`;

        barOrange.style.width = `${(vt.orange / totalPouches * 100).toFixed(1)}%`;
        barViolet.style.width = `${(vt.violet / totalPouches * 100).toFixed(1)}%`;
        barGreen.style.width = `${(vt.green / totalPouches * 100).toFixed(1)}%`;

        // 5. Incident Log Table
        renderIncidentTable(data.recent_incidents);
    }

    function updateVariantChip(variantName, confidence) {
        variantConf.textContent = `Conf: ${confidence}%`;
        const vLower = variantName.toLowerCase();

        if (vLower.includes('violet') || vLower.includes('toned')) {
            variantChip.className = 'variant-chip violet';
            chipColorDot.style.background = 'var(--variant-violet)';
            chipTitle.textContent = 'Violet (Toned Milk - 500 ml)';
        } else if (vLower.includes('green') || vLower.includes('smart')) {
            variantChip.className = 'variant-chip green';
            chipColorDot.style.background = 'var(--variant-green)';
            chipTitle.textContent = 'Green (Smart Milk - 500 ml)';
        } else {
            variantChip.className = 'variant-chip orange';
            chipColorDot.style.background = 'var(--variant-orange)';
            chipTitle.textContent = 'Orange (Rich Milk - 500 ml)';
        }
    }

    function renderIncidentTable(incidents) {
        if (!incidents || incidents.length === 0) {
            incidentTableBody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="9">No incidents logged yet. All crates passing quality verification (20/20).</td>
                </tr>
            `;
            return;
        }

        incidentTableBody.innerHTML = incidents.map(inc => {
            const isUnder = inc.discrepancy < 0;
            const badgeClass = isUnder ? 'badge-underfill' : 'badge-overfill';
            const badgeText = isUnder ? `UNDERFILL (${inc.discrepancy})` : `OVERFILL (+${inc.discrepancy})`;

            return `
                <tr>
                    <td class="font-mono">${inc.timestamp}</td>
                    <td class="font-mono font-bold text-white">${inc.crate_id}</td>
                    <td>${inc.variant}</td>
                    <td class="font-mono font-bold ${isUnder ? 'text-danger' : 'text-warning'}">${inc.detected_count}</td>
                    <td class="font-mono">${inc.expected_count}</td>
                    <td class="font-mono font-bold ${isUnder ? 'text-danger' : 'text-warning'}">${inc.discrepancy}</td>
                    <td><span class="badge-incident ${badgeClass}">${badgeText}</span></td>
                    <td class="font-mono">${inc.latency_ms} ms</td>
                    <td>
                        <button class="btn-view-snapshot" onclick="openSnapshotModal('${inc.crate_id}', '${inc.status}', '${inc.detected_count}')">
                            🔍 Inspect
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Modal Inspector Handling
    window.openSnapshotModal = function(crateId, status, count) {
        modalTitle.textContent = `Audit Inspection: ${crateId}`;
        modalSnapshotImg.src = `/api/snapshot/${crateId}?t=${Date.now()}`;
        modalMeta.textContent = `${status} • ${count} / 20 Packets Recorded`;
        snapshotModal.classList.add('open');
    };

    function closeModal() {
        snapshotModal.classList.remove('open');
    }
    modalCloseBtn.addEventListener('click', closeModal);
    modalDismissBtn.addEventListener('click', closeModal);
    snapshotModal.addEventListener('click', (e) => {
        if (e.target === snapshotModal) closeModal();
    });

    // Control Handlers
    btnToggleConveyor.addEventListener('click', async () => {
        const res = await fetch('/api/toggle_conveyor', { method: 'POST' });
        const d = await res.json();
        fetchDashboardStats();
    });

    btnTriggerCrate.addEventListener('click', async () => {
        const curVar = variantSelect.value === 'auto' ? 'orange' : variantSelect.value;
        await fetch('/api/trigger_crate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ variant: curVar, count: 20 })
        });
        fetchDashboardStats();
    });

    btnInjectUnderfill.addEventListener('click', async () => {
        const curVar = variantSelect.value === 'auto' ? 'orange' : variantSelect.value;
        await fetch('/api/trigger_crate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ variant: curVar, count: 19 })
        });
        fetchDashboardStats();
    });

    variantSelect.addEventListener('change', async (e) => {
        await fetch('/api/set_variant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ variant: e.target.value })
        });
        fetchDashboardStats();
    });

    speedSlider.addEventListener('input', (e) => {
        speedDisplay.textContent = e.target.value;
    });

    speedSlider.addEventListener('change', async (e) => {
        await fetch('/api/set_speed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed: parseFloat(e.target.value) })
        });
        fetchDashboardStats();
    });

    btnResetShift.addEventListener('click', async () => {
        if (confirm('Are you sure you want to reset all shift counters and incident logs?')) {
            await fetch('/api/reset_shift', { method: 'POST' });
            fetchDashboardStats();
        }
    });

    // Camera Source Toggles
    btnSrcSim.addEventListener('click', async () => {
        await fetch('/api/set_camera_source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: 'simulated' })
        });
        fetchDashboardStats();
    });

    btnSrcBaumer.addEventListener('click', async () => {
        await fetch('/api/set_camera_source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: 'baumer' })
        });
        fetchDashboardStats();
    });

    // Exposure Control
    exposureSlider.addEventListener('input', (e) => {
        isDraggingExposure = true;
        exposureDisplay.textContent = e.target.value;
    });

    exposureSlider.addEventListener('change', async (e) => {
        isDraggingExposure = false;
        await fetch('/api/set_camera_exposure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exposure_ms: parseFloat(e.target.value) })
        });
        fetchDashboardStats();
    });

    btnCaptureSnap.addEventListener('click', () => {
        // Trigger download of current live frame
        const a = document.createElement('a');
        a.href = `/video_feed?t=${Date.now()}`;
        a.download = `milma_baumer_capture_${Date.now()}.jpg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    // Initial fetch & loop polling every 500ms
    fetchDashboardStats();
    setInterval(fetchDashboardStats, 500);
});
