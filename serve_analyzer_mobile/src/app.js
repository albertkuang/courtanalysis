const videoElement = document.getElementById('inputVideo');
const canvasElement = document.getElementById('outputCanvas');
const canvasCtx = canvasElement?.getContext('2d');

const videoElementB = document.getElementById('inputVideoB');
const canvasElementB = document.getElementById('outputCanvasB');
const canvasCtxB = canvasElementB?.getContext('2d');

const uploadContainer = document.getElementById('uploadContainer');
const videoUpload = document.getElementById('videoUpload');
const videoUploadB = document.getElementById('videoUploadB');
const uploadAreaB = document.getElementById('uploadAreaB');
const uploadTextA = document.getElementById('uploadTextA');

const playerWrapper = document.getElementById('playerWrapper');
const videoGrid = document.getElementById('videoGrid');
const videoItemB = document.getElementById('videoItemB');
const resultsContainer = document.getElementById('resultsContainer');

const analyzeBtn = document.getElementById('analyzeBtn');
const retakeBtn = document.getElementById('retakeBtn');
const newServeBtn = document.getElementById('newServeBtn');
const comparisonToggle = document.getElementById('comparisonToggle');

const progressBar = document.getElementById('progressBar');
const loadingStatus = document.getElementById('loadingStatus');
const statusText = document.getElementById('statusText');
const progressContainer = document.querySelector('.progress-bar-container');

// Metrics
const shoulderEl = document.getElementById('shoulderAngle');
const shoulderFill = document.getElementById('shoulderFill');
const elbowEl = document.getElementById('elbowAngle');
const elbowFill = document.getElementById('elbowFill');
const kneeEl = document.getElementById('kneeAngle');
const kneeFill = document.getElementById('kneeFill');
const racketDropEl = document.getElementById('racketDrop');
const racketDropFill = document.getElementById('racketDropFill');
const pronationEl = document.getElementById('pronationSnap');
const pronationFill = document.getElementById('pronationFill');
const xFactorEl = document.getElementById('xFactorAngle');
const xFactorFill = document.getElementById('xFactorFill');
const levelSelect = document.getElementById('targetLevel');

let selectedLevel = 'pro';

const BENCHMARKS = {
    pro: {
        shoulder: { min: 90, max: 110 },
        elbow: { min: 70, max: 100 },
        knee: { min: 110, max: 140 },
        racketDrop: { min: 0, max: 105 },
        pronation: { threshold: 60 },
        xFactor: { min: 30, max: 50 }
    },
    junior: {
        shoulder: { min: 85, max: 115 },
        elbow: { min: 65, max: 110 },
        knee: { min: 100, max: 150 },
        racketDrop: { min: 0, max: 115 },
        pronation: { threshold: 45 },
        xFactor: { min: 20, max: 40 }
    }
};

levelSelect?.addEventListener('change', (e) => {
    selectedLevel = e.target.value;
});

let comparisonMode = false;
comparisonToggle?.addEventListener('change', (e) => {
    comparisonMode = e.target.checked;
    if (comparisonMode) {
        uploadAreaB.style.display = 'block';
        uploadTextA.innerText = 'Upload Serve A (Pro Baseline)';
    } else {
        uploadAreaB.style.display = 'none';
        uploadTextA.innerText = 'Ensure full body is visible from the side or rear-45 angle.';
    }
});

let poseA, poseB;
let isVideoSetupA = false;
let isVideoSetupB = false;
let isAnalyzing = false;
let poseResolveA = null;
let poseResolveB = null;

const PHASE_STATES = {
    PRE_SERVE: 'PRE_SERVE',
    LOADING: 'LOADING',
    DROPPING: 'DROPPING',
    STRIKING: 'STRIKING',
    FINISHED: 'FINISHED'
};

let trackingDataA = resetTrackingData();
let trackingDataB = resetTrackingData();

function resetTrackingData() {
    return {
        phaseState: PHASE_STATES.PRE_SERVE,
        stateStartTime: 0,
        maxShoulder: 0,
        minElbow: 180,
        minKnee: 180,
        minRacketDrop: 180,
        maxPronation: 0,
        maxXFactor: 0,
        impactTime: null,
        isServeStarted: false,
        velocityHistory: [],
        snapshots: {
            trophy: { img: null, time: null },
            kneeBend: { img: null, time: null },
            racketDrop: { img: null, time: null },
            impact: { img: null, time: null },
            finish: { img: null, time: null },
            xFactor: { img: null, time: null }
        },
        impactDetected: false,
        peakWristY: null,
        framesProcessed: 0,
        lastWristPos: null,
        lastTime: 0,
        reachedTrophy: false,
        frameBuffer: []
    };
}

let lastCapturedFrameA = null;
let lastCapturedFrameB = null;
let lastCapturedTimeA = 0;
let lastCapturedTimeB = 0;

function captureFrame(video, category, slot) {
    const data = slot === 'A' ? trackingDataA : trackingDataB;
    const frameCanvas = slot === 'A' ? lastCapturedFrameA : lastCapturedFrameB;
    const frameTime = slot === 'A' ? lastCapturedTimeA : lastCapturedTimeB;
    if (!frameCanvas) return;

    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = frameCanvas.width;
    offscreenCanvas.height = frameCanvas.height;
    const ctx = offscreenCanvas.getContext('2d');

    ctx.drawImage(frameCanvas, 0, 0);
    const mainCanvas = slot === 'A' ? canvasElement : canvasElementB;
    ctx.drawImage(mainCanvas, 0, 0, offscreenCanvas.width, offscreenCanvas.height);

    data.snapshots[category] = {
        img: offscreenCanvas.toDataURL('image/jpeg', 0.7),
        time: frameTime.toFixed(2)
    };
}

// Initialize MediaPipe Pose
async function initPose() {
    const opts = {
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    };

    poseA = new Pose({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}` });
    poseA.setOptions(opts);
    poseA.onResults((res) => onResults(res, 'A'));

    poseB = new Pose({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}` });
    poseB.setOptions(opts);
    poseB.onResults((res) => onResults(res, 'B'));

    try {
        await Promise.all([poseA.initialize(), poseB.initialize()]);
        if (statusText) statusText.innerText = 'AI Ready';
    } catch (err) {
        console.warn('MediaPipe init:', err);
    }
}
initPose();

function handleVideoUpload(file, videoEl, slotName) {
    if (file) {
        if (slotName === 'A') isVideoSetupA = true;
        if (slotName === 'B') isVideoSetupB = true;

        if (isVideoSetupA && (!comparisonMode || (comparisonMode && isVideoSetupB))) {
            uploadContainer.style.display = 'none';
            playerWrapper.style.display = 'flex';
            resultsContainer.style.display = 'none';

            if (comparisonMode) {
                videoGrid.classList.add('comparison-mode');
                videoItemB.style.display = 'block';
            } else {
                videoGrid.classList.remove('comparison-mode');
                videoItemB.style.display = 'none';
            }
        }

        const fileURL = URL.createObjectURL(file);
        videoEl.src = fileURL;
        videoEl.load();

        videoEl.onloadeddata = () => {
            if (slotName === 'A') {
                canvasElement.width = videoEl.videoWidth;
                canvasElement.height = videoEl.videoHeight;
            } else {
                canvasElementB.width = videoEl.videoWidth;
                canvasElementB.height = videoEl.videoHeight;
            }
            videoEl.play(); // Auto preview what was recorded
        };
    }
}

videoUpload?.addEventListener('change', (e) => handleVideoUpload(e.target.files[0], videoElement, 'A'));
videoUploadB?.addEventListener('change', (e) => handleVideoUpload(e.target.files[0], videoElementB, 'B'));

retakeBtn?.addEventListener('click', () => {
    uploadContainer.style.display = 'flex';
    playerWrapper.style.display = 'none';
    resultsContainer.style.display = 'none';
    if (comparisonMode) uploadAreaB.style.display = 'block';
});

newServeBtn?.addEventListener('click', () => {
    uploadContainer.style.display = 'flex';
    playerWrapper.style.display = 'none';
    resultsContainer.style.display = 'none';
    if (comparisonMode) uploadAreaB.style.display = 'block';
});

analyzeBtn?.addEventListener('click', () => {
    if (isVideoSetupA && !isAnalyzing) {
        processVideo();
    }
});

function calculateAngle3D(a, b, c) {
    if (!a || !b || !c) return null;
    const v1 = { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
    const v2 = { x: c.x - b.x, y: c.y - b.y, z: c.z - b.z };
    const dotProduct = v1.x * v2.x + v1.y * v2.y + v1.z * v2.z;
    const mag1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z);
    const mag2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y + v2.z * v2.z);
    const angleRad = Math.acos(Math.max(-1, Math.min(1, dotProduct / (mag1 * mag2))));
    return Math.round((angleRad * 180.0) / Math.PI);
}

function updateMetricUI(element, fillElement, angle, category) {
    if (angle === null) return;
    const config = BENCHMARKS[selectedLevel][category];
    const isPronation = category === 'pronation';

    if (isPronation) {
        if (element) element.innerText = `${angle.toFixed(1)}%`;
        const percent = Math.min(100, Math.max(0, angle));
        if (fillElement) {
            fillElement.style.width = `${percent}%`;
            fillElement.style.backgroundColor = angle >= config.threshold ? 'var(--success)' : 'var(--danger)';
        }
        return;
    }

    if (element) element.innerText = `${angle.toFixed(1)}°`;
    const percent = Math.min(100, Math.max(0, (angle / 180) * 100));
    if (fillElement) fillElement.style.width = `${percent}%`;

    const minIdeal = config.min;
    const maxIdeal = config.max;

    if (angle >= minIdeal && angle <= maxIdeal) {
        if (fillElement) fillElement.style.backgroundColor = 'var(--success)';
    } else {
        if (fillElement) fillElement.style.backgroundColor = 'var(--danger)';
    }
}

function onResults(results, slot) {
    const video = slot === 'A' ? videoElement : videoElementB;
    const canvas = slot === 'A' ? canvasElement : canvasElementB;
    const ctx = slot === 'A' ? canvasCtx : canvasCtxB;
    const data = slot === 'A' ? trackingDataA : trackingDataB;

    if (!video.videoWidth) return;

    // Dynamically match canvas size to video size if they drift
    if (slot === 'A' && canvasElement.width !== videoElement.videoWidth) {
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
    }
    if (slot === 'B' && comparisonMode && videoElementB.videoWidth > 0 && canvasElementB.width !== videoElementB.videoWidth) {
        canvasElementB.width = videoElementB.videoWidth;
        canvasElementB.height = videoElementB.videoHeight;
    }

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (results.poseLandmarks) {
        const color = slot === 'A' ? 'rgba(88, 166, 255, 0.6)' : 'rgba(255, 106, 51, 0.6)';
        const fillColor = slot === 'A' ? '#58a6ff' : '#ff6a33';
        drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS, { color, lineWidth: 4 });
        drawLandmarks(ctx, results.poseLandmarks, { color: '#0d1117', fillColor, lineWidth: 2, radius: 4 });

        const rawLandmarks = results.poseLandmarks;
        const shoulderAng = calculateAngle3D(rawLandmarks[24], rawLandmarks[12], rawLandmarks[14]);
        const elbowAng = calculateAngle3D(rawLandmarks[12], rawLandmarks[14], rawLandmarks[16]);
        const kneeAng = calculateAngle3D(rawLandmarks[24], rawLandmarks[26], rawLandmarks[28]);

        const hipVec = { x: rawLandmarks[24].x - rawLandmarks[23].x, z: rawLandmarks[24].z - rawLandmarks[23].z };
        const shldVec = { x: rawLandmarks[12].x - rawLandmarks[11].x, z: rawLandmarks[12].z - rawLandmarks[11].z };
        let xFactor = Math.abs(Math.atan2(shldVec.z, shldVec.x) - Math.atan2(hipVec.z, hipVec.x)) * (180 / Math.PI);
        if (xFactor > 180) xFactor = 360 - xFactor;
        if (xFactor > 90) xFactor = 180 - xFactor;

        // Peak Tracking
        if (shoulderAng > data.maxShoulder) data.maxShoulder = shoulderAng;
        if (elbowAng !== null && elbowAng < data.minElbow) data.minElbow = elbowAng;
        if (kneeAng !== null && kneeAng < data.minKnee) data.minKnee = kneeAng;
        if (xFactor > data.maxXFactor) data.maxXFactor = xFactor;

        // Track lowest racket drop if arm is bent
        if (elbowAng !== null && elbowAng < data.minRacketDrop && rawLandmarks[16].y < rawLandmarks[12].y + 0.2) {
            data.minRacketDrop = elbowAng;
        }

        // Live Velocity for Pronation
        const currentTime = video.currentTime;
        if (data.lastWristPos) {
            const dt = currentTime - data.lastTime;
            if (dt > 0.005) {
                const dx = rawLandmarks[16].x - data.lastWristPos.x;
                const dy = rawLandmarks[16].y - data.lastWristPos.y;
                const velocity = (Math.sqrt(dx * dx + dy * dy) / dt) * 100;
                if (velocity > data.maxPronation) data.maxPronation = Math.min(100, velocity);
            }
        }
        data.lastWristPos = { x: rawLandmarks[16].x, y: rawLandmarks[16].y };
        data.lastTime = currentTime;
        data.framesProcessed++;

        // --- Simplified Fast Snapshot Tracking Logic (Continuous capture max/min points) ---
        const isArmLoaded = elbowAng !== null && elbowAng < 165;
        const currentTossY = rawLandmarks[15].y;
        const isWristHigh = rawLandmarks[16].y < rawLandmarks[0].y;

        // 1. Trophy Capture (High toss, bent arm, shoulder rotation)
        if (!data.snapshots.trophy.img && isArmLoaded && currentTossY < 0.5 && shoulderAng > 80 && xFactor > 20) {
            captureFrame(video, 'trophy', slot);
        }
        // Always try to get a more loaded trophy
        else if (data.snapshots.trophy.img && isArmLoaded && currentTossY < 0.5 && kneeAng < data.minKnee + 10) {
            if (Math.random() > 0.8) captureFrame(video, 'trophy', slot); // sample deepest bend
        }

        // 2. Knee Bend
        if (kneeAng !== null && kneeAng <= data.minKnee + 2) {
            captureFrame(video, 'kneeBend', slot);
        }

        // 3. Racket Drop (Wrist below elbow, tight elbow angle)
        if (elbowAng !== null && elbowAng <= data.minRacketDrop + 5 && rawLandmarks[16].y > rawLandmarks[14].y) {
            captureFrame(video, 'racketDrop', slot);
        }

        // 4. X-Factor (Max coil before forward swing)
        if (xFactor >= data.maxXFactor - 2 && isArmLoaded) {
            captureFrame(video, 'xFactor', slot);
        }

        // 5. Impact (Arm extended high above head)
        if (!data.snapshots.impact.img && elbowAng > 140 && rawLandmarks[16].y < rawLandmarks[12].y - 0.2) {
            captureFrame(video, 'impact', slot);
            data.impactDetected = true;
        }

        // 6. Finish (After impact, hand drops below waist)
        if (data.impactDetected && !data.snapshots.finish.img && rawLandmarks[16].y > rawLandmarks[24].y) {
            captureFrame(video, 'finish', slot);
        }
    }
    ctx.restore();

    if (slot === 'A' && poseResolveA) { poseResolveA(); poseResolveA = null; }
    if (slot === 'B' && poseResolveB) { poseResolveB(); poseResolveB = null; }
}

async function processPoseFrame(video, slot) {
    return new Promise(resolve => {
        if (slot === 'A') poseResolveA = resolve;
        else poseResolveB = resolve;

        const poseInst = slot === 'A' ? poseA : poseB;
        poseInst.send({ image: video });

        setTimeout(() => {
            if (slot === 'A' && poseResolveA) { poseResolveA(); poseResolveA = null; }
            if (slot === 'B' && poseResolveB) { poseResolveB(); poseResolveB = null; }
        }, 3000);
    });
}

async function seekAndWait(videoEl, time) {
    videoEl.currentTime = time;
    await new Promise(resolve => {
        const onSeeked = () => {
            videoEl.removeEventListener('seeked', onSeeked);
            requestAnimationFrame(resolve);
        };
        videoEl.addEventListener('seeked', onSeeked);
        setTimeout(() => { videoEl.removeEventListener('seeked', onSeeked); requestAnimationFrame(resolve); }, 300);
    });
}

async function processVideo() {
    isAnalyzing = true;
    analyzeBtn.disabled = true;
    retakeBtn.disabled = true;

    loadingStatus.style.display = 'flex';
    statusText.innerText = 'Analyzing Biomechanics...';
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';

    videoElement.pause();
    trackingDataA = resetTrackingData();
    if (comparisonMode) {
        videoElementB.pause();
        trackingDataB = resetTrackingData();
    }

    const duration = videoElement.duration;
    let currentPos = 0;

    // Process at 15fps for speed on mobile
    const step = 1 / 15;

    // Await metadata to ensure we have intrinsic video dimensions
    while (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
        await new Promise(r => requestAnimationFrame(r));
    }
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;

    if (comparisonMode && isVideoSetupB) {
        while (videoElementB.videoWidth === 0 || videoElementB.videoHeight === 0) {
            await new Promise(r => requestAnimationFrame(r));
        }
        canvasElementB.width = videoElementB.videoWidth;
        canvasElementB.height = videoElementB.videoHeight;
    }

    while (currentPos < duration) {
        await seekAndWait(videoElement, currentPos);
        progressBar.style.width = `${((currentPos / duration) * 100)}%`;

        // Precapture A
        const preCapA = document.createElement('canvas');
        preCapA.width = videoElement.videoWidth / 2;
        preCapA.height = videoElement.videoHeight / 2;
        preCapA.getContext('2d').drawImage(videoElement, 0, 0, preCapA.width, preCapA.height);
        lastCapturedFrameA = preCapA;
        lastCapturedTimeA = currentPos;

        const fullCapA = document.createElement('canvas');
        fullCapA.width = videoElement.videoWidth;
        fullCapA.height = videoElement.videoHeight;
        fullCapA.getContext('2d').drawImage(videoElement, 0, 0);

        try {
            await processPoseFrame(fullCapA, 'A');

            if (comparisonMode && isVideoSetupB) {
                const ratioB = currentPos / duration;
                const posB = ratioB * videoElementB.duration;
                await seekAndWait(videoElementB, posB);

                const preCapB = document.createElement('canvas');
                preCapB.width = videoElementB.videoWidth / 2;
                preCapB.height = videoElementB.videoHeight / 2;
                preCapB.getContext('2d').drawImage(videoElementB, 0, 0, preCapB.width, preCapB.height);
                lastCapturedFrameB = preCapB;
                lastCapturedTimeB = posB;

                const fullCapB = document.createElement('canvas');
                fullCapB.width = videoElementB.videoWidth;
                fullCapB.height = videoElementB.videoHeight;
                fullCapB.getContext('2d').drawImage(videoElementB, 0, 0);

                await processPoseFrame(fullCapB, 'B');
            }
        } catch (e) { console.error('Pose frame error', e); }

        currentPos += step;
    }

    isAnalyzing = false;
    analyzeBtn.disabled = false;
    retakeBtn.disabled = false;
    loadingStatus.style.display = 'none';

    generateResults();
}

function generateVisualGallery(dataA, dataB, isComparison) {
    const container = document.getElementById('actionPlanContainer');
    let galleryHTML = `
        <div class="visual-gallery">
            <h3>${isComparison ? 'Side-by-Side Visuals' : 'Biomechanical Snapshots'}</h3>
            <div class="gallery-grid">
    `;

    const labels = {
        trophy: { title: 'Trophy Position', desc: 'Maximum coil.' },
        kneeBend: { title: 'Knee Bend', desc: 'Power loading.' },
        racketDrop: { title: 'Racket Drop', desc: 'Stretch-shortening cycle.' },
        xFactor: { title: 'X-Factor', desc: 'Hip-shoulder separation.' },
        impact: { title: 'Impact', desc: 'Full extension.' },
        finish: { title: 'Follow Through', desc: 'Deceleration.' }
    };

    Object.keys(labels).forEach(key => {
        const snapA = dataA.snapshots[key];
        const snapB = isComparison ? (dataB ? dataB.snapshots[key] : null) : null;

        const imgA = (snapA && snapA.img) ? snapA.img : '';
        const imgB = (snapB && snapB.img) ? snapB.img : '';
        const timeA = (snapA && snapA.time && snapA.time !== 'null') ? snapA.time : '--';
        const timeB = (snapB && snapB.time && snapB.time !== 'null') ? snapB.time : '--';

        galleryHTML += `
            <div class="gallery-item" style="${(isComparison && (!imgA || !imgB)) ? 'opacity: 0.8;' : ''}">
                <h4>${labels[key].title}</h4>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">${labels[key].desc}</p>
                <div class="comparison-row ${!isComparison ? 'single-view' : ''}">
                    <div class="snapshot">
                        ${imgA ? `<img src="${imgA}" alt="Serve A ${key}">` : `<div style="height:150px; background:#121826; border-radius:8px; display:flex; align-items:center; justify-content:center;">Awaiting Focus</div>`}
                        <div class="snap-label">${isComparison ? 'Serve A (Pro)' : 'Biomechanical Point'}</div>
                    </div>
                    ${isComparison ? `
                    <div class="snapshot">
                        ${imgB ? `<img src="${imgB}" alt="Serve B ${key}">` : `<div style="height:150px; background:#121826; border-radius:8px; display:flex; align-items:center; justify-content:center;">Awaiting Focus</div>`}
                        <div class="snap-label">Serve B (User)</div>
                    </div>` : ''}
                </div>
            </div>
        `;
    });

    galleryHTML += `</div></div>`;
    container.innerHTML = galleryHTML;
}

function generateResults() {
    resultsContainer.style.display = 'block';
    playerWrapper.style.display = 'none';

    // Update the UI cards
    updateMetricUI(shoulderEl, shoulderFill, trackingDataA.maxShoulder, 'shoulder');
    updateMetricUI(elbowEl, elbowFill, trackingDataA.minElbow, 'elbow');
    updateMetricUI(kneeEl, kneeFill, trackingDataA.minKnee, 'knee');
    updateMetricUI(racketDropEl, racketDropFill, trackingDataA.minRacketDrop, 'racketDrop');
    updateMetricUI(pronationEl, pronationFill, trackingDataA.maxPronation, 'pronation');
    updateMetricUI(xFactorEl, xFactorFill, trackingDataA.maxXFactor, 'xFactor');

    const flawList = document.getElementById('flawList');
    flawList.innerHTML = '';
    let flaws = 0;

    if (comparisonMode) {
        // Comparison Results Output
        const diffs = [
            { label: 'Shoulder Abduction', a: trackingDataA.maxShoulder, b: trackingDataB.maxShoulder, unit: '°' },
            { label: 'Knee Bend', a: Math.round(trackingDataA.minKnee), b: Math.round(trackingDataB.minKnee), unit: '°' },
            { label: 'Racket Drop', a: Math.round(trackingDataA.minRacketDrop), b: Math.round(trackingDataB.minRacketDrop), unit: '°' },
            { label: 'X-Factor', a: Math.round(trackingDataA.maxXFactor), b: Math.round(trackingDataB.maxXFactor), unit: '°' },
        ];

        diffs.forEach(d => {
            const delta = d.b - d.a;
            const color = Math.abs(delta) < 10 ? 'var(--success)' : 'var(--warning)';
            flawList.innerHTML += `
                <li class="flaw-item" style="border-left: 4px solid ${color};">
                    <strong>${d.label}</strong>
                    <span style="display:block; margin-top:5px; font-size: 0.8rem;">Pro: ${d.a}${d.unit} | You: ${d.b}${d.unit}</span>
                    <strong style="display:block; font-size: 0.75rem; color: ${color};">Delta: ${delta > 0 ? '+' : ''}${Math.round(delta)}${d.unit}</strong>
                </li>`;
        });

        const scoreBadge = document.getElementById('overallScore');
        scoreBadge.innerText = 'Comparison Complete';
        scoreBadge.style.background = 'var(--warning)';

    } else {
        // Single Player Logic
        const cfg = BENCHMARKS[selectedLevel];
        if (trackingDataA.maxShoulder < cfg.shoulder.min) {
            flaws++;
            flawList.innerHTML += `<li class="flaw-item"><strong>Shoulder Alignment:</strong> Elbow dropped below shoulder line (${Math.round(trackingDataA.maxShoulder)}°), sacrificing leverage.</li>`;
        }
        if (trackingDataA.minKnee > cfg.knee.max) {
            flaws++;
            flawList.innerHTML += `<li class="flaw-item"><strong>Leg Drive:</strong> Insufficient knee bend (${Math.round(trackingDataA.minKnee)}°). You are arming the serve.</li>`;
        }
        if (trackingDataA.minRacketDrop > cfg.racketDrop.max) {
            flaws++;
            flawList.innerHTML += `<li class="flaw-item"><strong>Racket Drop:</strong> Shallow back-scratch (${Math.round(trackingDataA.minRacketDrop)}°). Limits upward acceleration runway.</li>`;
        }
        if (trackingDataA.maxPronation < cfg.pronation.threshold) {
            flaws++;
            flawList.innerHTML += `<li class="flaw-item"><strong>Pronation Snap:</strong> Weak internal rotation speed. Focus on edge-to-flat acceleration at impact.</li>`;
        }

        const scoreBadge = document.getElementById('overallScore');
        if (flaws === 0) {
            scoreBadge.innerText = 'Elite Status';
            scoreBadge.style.background = 'var(--success)';
            flawList.innerHTML = `<li class="flaw-item" style="border-left-color: var(--success); background: rgba(16, 185, 129, 0.1);">Perfect mechanics for ${selectedLevel.toUpperCase()} benchmarks!</li>`;
        } else {
            scoreBadge.innerText = `${flaws} Mechanics Flaws`;
            scoreBadge.style.background = 'var(--danger)';
        }
    }

    generateVisualGallery(trackingDataA, trackingDataB, comparisonMode);

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}
