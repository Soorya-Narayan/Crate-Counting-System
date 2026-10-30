/**
 * Goose Industrial Solutions - Vision AI Object & Color Classifier
 * Live Machine Vision Stream + YOLOv8 + Lens ISP Tuning
 */

document.addEventListener('DOMContentLoaded', () => {
    // Header & Telemetry Elements
    const clockEl = document.getElementById('clockDisplay');
    const camStatusPill = document.getElementById('camStatusPill');
    const camStatusText = document.getElementById('camStatusText');
    const cameraTitle = document.getElementById('cameraTitle');
    const telemetryFps = document.getElementById('telemetryFps');
    const telemetryExp = document.getElementById('telemetryExp');

    // Video Feed
    const liveVideoFeed = document.getElementById('liveVideoFeed');

    // Source Toggles
    const btnSrcWebcam = document.getElementById('btnSrcWebcam');
    const btnSrcBaumer = document.getElementById('btnSrcBaumer');
    const btnSrcSim = document.getElementById('btnSrcSim');

    // Lens & Sensor Tuning Sliders
    const exposureRange = document.getElementById('exposureRange');
    const exposureVal = document.getElementById('exposureVal');
    const brightnessRange = document.getElementById('brightnessRange');
    const brightnessVal = document.getElementById('brightnessVal');
    const contrastRange = document.getElementById('contrastRange');
    const contrastVal = document.getElementById('contrastVal');
    const saturationRange = document.getElementById('saturationRange');
    const saturationVal = document.getElementById('saturationVal');
    const awbToggle = document.getElementById('awbToggle');
    const confRange = document.getElementById('confRange');
    const confVal = document.getElementById('confVal');

    // Action & Toggle Buttons
    const btnTogglePouches = document.getElementById('btnTogglePouches');
    const btnToggleCrates = document.getElementById('btnToggleCrates');
    const btnQuickTogglePouches = document.getElementById('btnQuickTogglePouches');
    const btnQuickToggleCrates = document.getElementById('btnQuickToggleCrates');
    const btnToggleRoi = document.getElementById('btnToggleRoi');
    const btnResetTripwire = document.getElementById('btnResetTripwire');
    const btnResetLens = document.getElementById('btnResetLens');
    const btnSnapshot = document.getElementById('btnSnapshot');
    const btnFullscreen = document.getElementById('btnFullscreen');

    // Audit & Tracking Elements
    const crateAuditBadge = document.getElementById('crateAuditBadge');
    const cratePouchesCount = document.getElementById('cratePouchesCount');
    const tripwireCrossedCount = document.getElementById('tripwireCrossedCount');
    const cratesInViewCount = document.getElementById('cratesInViewCount');
    const cratesCrossedCount = document.getElementById('cratesCrossedCount');
    const activeTracksCount = document.getElementById('activeTracksCount');

    // Detections & Color Palettes
    const totalObjectsBadge = document.getElementById('totalObjectsBadge');
    const detectedChipsContainer = document.getElementById('detectedChipsContainer');
    const colorPaletteGrid = document.getElementById('colorPaletteGrid');

    let isInteracting = false;
    let autoWbState = true;

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
        if (lower.includes('cup') || lower.includes('mug')) return '☕';
        if (lower.includes('mouse')) return '🖱️';
        if (lower.includes('phone') || lower.includes('cell')) return '📱';
        if (lower.includes('knife') || lower.includes('fork') || lower.includes('spoon')) return '🍴';
        if (lower.includes('book')) return '📖';
        if (lower.includes('keyboard')) return '⌨️';
        if (lower.includes('laptop')) return '💻';
        if (lower.includes('backpack') || lower.includes('bag') || lower.includes('handbag')) return '🎒';
        if (lower.includes('chair')) return '🪑';
        if (lower.includes('apple') || lower.includes('banana') || lower.includes('orange')) return '🍎';
        if (lower.includes('clock') || lower.includes('watch')) return '⏱️';
        if (lower.includes('remote')) return '🎛️';
        return '🔍';
    }

    // Hex Color Palette for pill tags
    const COLOR_HEX_MAP = {
        'RED': '#ef4444',
        'ORANGE': '#f97316',
        'YELLOW': '#eab308',
        'GREEN': '#22c55e',
        'CYAN': '#06b6d4',
        'BLUE': '#3b82f6',
        'PURPLE': '#a855f7',
        'PINK': '#ec4899',
        'BROWN': '#854d0e',
        'BLACK': '#1e293b',
        'WHITE': '#f8fafc',
        'GRAY': '#94a3b8'
    };

    // Fetch Live Status & Update UI
    async function fetchStatus() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();
            updateUI(data);
        } catch (err) {
            console.error('Error fetching telemetry:', err);
        }
    }

    function updateUI(data) {
        // 1. Connection & Source Status
        if (data.camera_source === 'webcam') {
            if (btnSrcWebcam) btnSrcWebcam.classList.add('active');
            btnSrcBaumer.classList.remove('active');
            btnSrcSim.classList.remove('active');
            camStatusPill.className = 'status-pill';
            camStatusText.textContent = 'MAC CAMERA ONLINE (Built-in)';
            cameraTitle.textContent = 'Mac FaceTime HD Camera • Milma Pouch & Crate AI Stream';
        } else if (data.camera_source === 'baumer') {
            btnSrcBaumer.classList.add('active');
            if (btnSrcWebcam) btnSrcWebcam.classList.remove('active');
            btnSrcSim.classList.remove('active');

            if (data.camera_connected) {
                camStatusPill.className = 'status-pill';
                camStatusText.textContent = 'BAUMER GIGE ONLINE (169.254.123.85)';
                cameraTitle.textContent = 'Overhead Stream: Baumer VCXG.2-32C + YOLOv8 + Lens ISP';
            } else {
                camStatusPill.className = 'status-pill offline';
                camStatusText.textContent = 'CONNECTING TO BAUMER...';
                cameraTitle.textContent = 'Searching for Baumer Camera on 169.254.123.85...';
            }
        } else {
            btnSrcSim.classList.add('active');
            if (btnSrcWebcam) btnSrcWebcam.classList.remove('active');
            btnSrcBaumer.classList.remove('active');
            camStatusPill.className = 'status-pill';
            camStatusText.textContent = 'TEST FEED ACTIVE';
            cameraTitle.textContent = 'Plant Test Crate Stream (master_yolo_dataset)';
        }

        // 2. FPS, Exposure & Tripwire KPI Telemetry
        telemetryFps.textContent = `${(data.fps || 0.0).toFixed(1)} FPS`;
        telemetryExp.textContent = `Exp: ${(data.exposure_ms || 30.0).toFixed(1)} ms`;

        if (crateAuditBadge && data.last_audit_status) {
            crateAuditBadge.textContent = data.last_audit_status;
            crateAuditBadge.className = data.last_audit_class || 'badge-pass';
        }

        // Pouch detection and counts
        const isPouchActive = data.detect_pouches !== false;
        if (cratePouchesCount) {
            cratePouchesCount.textContent = isPouchActive ? `${data.current_crate_pouches || 0} / 20` : 'PAUSED';
            cratePouchesCount.style.opacity = isPouchActive ? '1' : '0.5';
        }
        if (tripwireCrossedCount && data.total_counted_pouches !== undefined) {
            tripwireCrossedCount.textContent = (data.total_counted_pouches).toLocaleString();
            tripwireCrossedCount.style.opacity = isPouchActive ? '1' : '0.5';
        }

        // Crate detection and counts
        const isCrateActive = data.detect_crates !== false;
        if (cratesInViewCount) {
            cratesInViewCount.textContent = isCrateActive ? (data.current_crates_count || 0) : 'PAUSED';
            cratesInViewCount.style.opacity = isCrateActive ? '1' : '0.5';
        }
        if (cratesCrossedCount && data.total_counted_crates !== undefined) {
            cratesCrossedCount.textContent = (data.total_counted_crates).toLocaleString();
            cratesCrossedCount.style.opacity = isCrateActive ? '1' : '0.5';
        }

        if (activeTracksCount && data.active_tracks_count !== undefined) {
            activeTracksCount.textContent = data.active_tracks_count;
        }

        // Sync Ribbon & Header Toggle Button States
        if (btnTogglePouches) {
            btnTogglePouches.classList.toggle('active', isPouchActive);
            btnTogglePouches.classList.toggle('inactive', !isPouchActive);
            const span = btnTogglePouches.querySelector('span');
            if (span) span.textContent = isPouchActive ? '🥛 Pouches: ON' : '🥛 Pouches: OFF';
        }
        if (btnQuickTogglePouches) {
            btnQuickTogglePouches.classList.toggle('active', isPouchActive);
            btnQuickTogglePouches.classList.toggle('inactive', !isPouchActive);
            btnQuickTogglePouches.textContent = isPouchActive ? '🥛 Pouches: ON' : '🥛 Pouches: OFF';
        }

        if (btnToggleCrates) {
            btnToggleCrates.classList.toggle('active', isCrateActive);
            btnToggleCrates.classList.toggle('inactive', !isCrateActive);
            const span = btnToggleCrates.querySelector('span');
            if (span) span.textContent = isCrateActive ? '📦 Crates: ON' : '📦 Crates: OFF';
        }
        if (btnQuickToggleCrates) {
            btnQuickToggleCrates.classList.toggle('active', isCrateActive);
            btnQuickToggleCrates.classList.toggle('inactive', !isCrateActive);
            btnQuickToggleCrates.textContent = isCrateActive ? '📦 Crates: ON' : '📦 Crates: OFF';
        }

        if (btnToggleRoi && data.roi_enabled !== undefined) {
            btnToggleRoi.classList.toggle('active', data.roi_enabled);
            const span = btnToggleRoi.querySelector('span');
            if (span) span.textContent = data.roi_enabled ? '🎯 Conveyor ROI [ON]' : '🎯 Conveyor ROI [OFF]';
        }

        // Sync slider values when not actively dragging
        if (!isInteracting) {
            if (exposureRange) {
                exposureRange.value = data.exposure_ms;
                exposureVal.textContent = Math.round(data.exposure_ms);
            }
            const lens = data.lens_settings || {};
            if (brightnessRange && lens.brightness !== undefined) {
                brightnessRange.value = lens.brightness;
                brightnessVal.textContent = (lens.brightness >= 0 ? '+' : '') + Math.round(lens.brightness);
            }
            if (contrastRange && lens.contrast !== undefined) {
                contrastRange.value = lens.contrast;
                contrastVal.textContent = lens.contrast.toFixed(2);
            }
            if (saturationRange && lens.saturation !== undefined) {
                saturationRange.value = lens.saturation;
                saturationVal.textContent = lens.saturation.toFixed(2);
            }
            if (lens.auto_wb !== undefined) {
                autoWbState = Boolean(lens.auto_wb);
                awbToggle.textContent = autoWbState ? 'ON' : 'OFF';
                awbToggle.classList.toggle('active', autoWbState);
            }
        }

        // 3. Detected Objects Deck
        const objects = data.detected_objects || [];
        totalObjectsBadge.textContent = `${objects.length} Object${objects.length === 1 ? '' : 's'}`;

        if (objects.length === 0) {
            detectedChipsContainer.innerHTML = '<span class="empty-state">No objects currently in camera frame. Place scissors, bottles, cups, phone, mouse, or items in view...</span>';
        } else {
            detectedChipsContainer.innerHTML = objects.map(item => {
                const icon = getObjectIcon(item.object);
                const colorStr = (item.color || 'UNKNOWN').toUpperCase();
                const hexColor = item.color_hex || COLOR_HEX_MAP[colorStr] || '#64748b';
                const isLight = ['WHITE', 'YELLOW', 'CYAN', 'PINK'].includes(colorStr);
                const textColor = isLight ? '#0f172a' : '#ffffff';

                return `
                    <div class="object-chip" style="border-left: 3px solid ${hexColor};">
                        <span class="chip-icon">${icon}</span>
                        <span class="chip-obj-name">${item.object}</span>
                        <span class="chip-color-tag" style="background: ${hexColor}; color: ${textColor};">
                            ${colorStr}
                        </span>
                        <span class="chip-conf">${item.confidence}%</span>
                    </div>
                `;
            }).join('');
        }

        // 4. Color Palette Breakdown
        const colorDist = data.color_distribution || {};
        const colorEntries = Object.entries(colorDist);

        if (colorEntries.length === 0) {
            colorPaletteGrid.innerHTML = '<span class="empty-palette">No colored objects detected yet...</span>';
        } else {
            colorPaletteGrid.innerHTML = colorEntries.map(([colName, count]) => {
                const hex = COLOR_HEX_MAP[colName] || '#64748b';
                return `
                    <div class="palette-chip">
                        <span class="palette-swatch" style="background: ${hex}; box-shadow: 0 0 8px ${hex}88;"></span>
                        <span class="palette-label">${colName}</span>
                        <span class="palette-count">${count}</span>
                    </div>
                `;
            }).join('');
        }
    }

    // =========================================================================
    // LENS & SENSOR CONTROLS (Live Tuning)
    // =========================================================================
    async function updateLensSettings(patch) {
        try {
            await fetch('/api/set_lens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(patch)
            });
        } catch (e) {
            console.error('Error updating lens settings:', e);
        }
    }

    // Exposure Slider
    exposureRange.addEventListener('input', (e) => {
        isInteracting = true;
        exposureVal.textContent = e.target.value;
    });

    exposureRange.addEventListener('change', async (e) => {
        isInteracting = false;
        await fetch('/api/set_exposure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exposure_ms: parseFloat(e.target.value) })
        });
        fetchStatus();
    });

    // Brightness Slider
    brightnessRange.addEventListener('input', (e) => {
        isInteracting = true;
        const val = parseInt(e.target.value);
        brightnessVal.textContent = (val >= 0 ? '+' : '') + val;
    });

    brightnessRange.addEventListener('change', async (e) => {
        isInteracting = false;
        await updateLensSettings({ brightness: parseFloat(e.target.value) });
        fetchStatus();
    });

    // Contrast Slider
    contrastRange.addEventListener('input', (e) => {
        isInteracting = true;
        contrastVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    contrastRange.addEventListener('change', async (e) => {
        isInteracting = false;
        await updateLensSettings({ contrast: parseFloat(e.target.value) });
        fetchStatus();
    });

    // Saturation Slider
    saturationRange.addEventListener('input', (e) => {
        isInteracting = true;
        saturationVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    saturationRange.addEventListener('change', async (e) => {
        isInteracting = false;
        await updateLensSettings({ saturation: parseFloat(e.target.value) });
        fetchStatus();
    });

    // Auto White Balance Toggle
    awbToggle.addEventListener('click', async () => {
        autoWbState = !autoWbState;
        awbToggle.textContent = autoWbState ? 'ON' : 'OFF';
        awbToggle.classList.toggle('active', autoWbState);
        await updateLensSettings({ auto_wb: autoWbState });
        fetchStatus();
    });

    // YOLO Confidence Threshold
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

    // Reset Lens Settings to Factory Defaults
    btnResetLens.addEventListener('click', async () => {
        exposureRange.value = 30;
        exposureVal.textContent = '30';
        brightnessRange.value = 5;
        brightnessVal.textContent = '+5';
        contrastRange.value = 1.18;
        contrastVal.textContent = '1.18';
        saturationRange.value = 1.35;
        saturationVal.textContent = '1.35';
        confRange.value = 38;
        confVal.textContent = '38';
        autoWbState = true;
        awbToggle.textContent = 'ON';
        awbToggle.classList.add('active');

        await fetch('/api/set_exposure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exposure_ms: 30.0 })
        });
        await updateLensSettings({
            brightness: 5,
            contrast: 1.18,
            saturation: 1.35,
            gamma: 0.85,
            auto_wb: true
        });
        await fetch('/api/set_confidence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confidence: 0.38 })
        });
        fetchStatus();
    });

    // Helper: Toggle Pouch or Crate Detection Engines
    async function toggleDetection(target) {
        try {
            const res = await fetch('/api/toggle_detection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });
            if (res.ok) {
                const data = await res.json();
                if (target === 'pouch' && btnTogglePouches) {
                    btnTogglePouches.classList.toggle('active', data.detect_pouches);
                    btnTogglePouches.classList.toggle('inactive', !data.detect_pouches);
                    const s = btnTogglePouches.querySelector('span');
                    if (s) s.textContent = data.detect_pouches ? '🥛 Pouches: ON' : '🥛 Pouches: OFF';
                }
                if (target === 'crate' && btnToggleCrates) {
                    btnToggleCrates.classList.toggle('active', data.detect_crates);
                    btnToggleCrates.classList.toggle('inactive', !data.detect_crates);
                    const s = btnToggleCrates.querySelector('span');
                    if (s) s.textContent = data.detect_crates ? '📦 Crates: ON' : '📦 Crates: OFF';
                }
            }
            fetchStatus();
        } catch (e) {
            console.error(`Error toggling ${target} detection:`, e);
        }
    }

    if (btnTogglePouches) {
        btnTogglePouches.addEventListener('click', () => toggleDetection('pouch'));
    }
    if (btnQuickTogglePouches) {
        btnQuickTogglePouches.addEventListener('click', () => toggleDetection('pouch'));
    }
    if (btnToggleCrates) {
        btnToggleCrates.addEventListener('click', () => toggleDetection('crate'));
    }
    if (btnQuickToggleCrates) {
        btnQuickToggleCrates.addEventListener('click', () => toggleDetection('crate'));
    }

    // Toggle Conveyor ROI
    if (btnToggleRoi) {
        btnToggleRoi.addEventListener('click', async () => {
            const res = await fetch('/api/toggle_roi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            if (res.ok) {
                const d = await res.json();
                btnToggleRoi.classList.toggle('active', d.roi_enabled);
                const span = btnToggleRoi.querySelector('span');
                if (span) span.textContent = d.roi_enabled ? '🎯 Conveyor ROI [ON]' : '🎯 Conveyor ROI [OFF]';
            }
            fetchStatus();
        });
    }

    // Reset Tripwire Pouch Count
    if (btnResetTripwire) {
        btnResetTripwire.addEventListener('click', async () => {
            await fetch('/api/reset_tripwire', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            fetchStatus();
        });
    }

    // Source Toggle
    if (btnSrcWebcam) {
        btnSrcWebcam.addEventListener('click', async () => {
            await fetch('/api/set_source', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: 'webcam' })
            });
            fetchStatus();
        });
    }

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

    // =========================================================================
    // RESILIENT VIDEO STREAMING
    // =========================================================================
    let framePollInterval = null;

    function startFramePollingFallback() {
        if (framePollInterval) return;
        console.warn("Activating fast frame fallback polling (/api/frame)...");
        framePollInterval = setInterval(() => {
            const nextImg = new Image();
            nextImg.onload = () => {
                liveVideoFeed.src = nextImg.src;
            };
            nextImg.src = `/api/frame?t=${Date.now()}`;
        }, 180);
    }

    liveVideoFeed.onerror = () => {
        console.warn("Video feed error detected. Attempting reload...");
        setTimeout(() => {
            liveVideoFeed.src = `/video_feed?t=${Date.now()}`;
        }, 1200);
    };

    // If stream has no dimensions after 2.5s, trigger frame polling fallback
    setTimeout(() => {
        if (!liveVideoFeed.naturalWidth || liveVideoFeed.naturalWidth === 0) {
            startFramePollingFallback();
        }
    }, 2500);

    // Snapshot Download
    btnSnapshot.addEventListener('click', () => {
        const a = document.createElement('a');
        a.href = `/api/frame?t=${Date.now()}`;
        a.download = `vision_ai_lens_capture_${Date.now()}.jpg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    // Fullscreen Toggle
    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            liveVideoFeed.requestFullscreen().catch(err => {
                alert(`Fullscreen error: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    });

    // Sequential Polling Loop
    let isFetching = false;
    async function pollTelemetryLoop() {
        if (!isFetching) {
            isFetching = true;
            try {
                await fetchStatus();
            } finally {
                isFetching = false;
            }
        }
        setTimeout(pollTelemetryLoop, 350);
    }

    pollTelemetryLoop();
});
