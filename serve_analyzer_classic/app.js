const videoElement = document.getElementById('inputVideo');
const canvasElement = document.getElementById('outputCanvas');
const canvasCtx = canvasElement.getContext('2d');

const videoElementB = document.getElementById('inputVideoB');
const canvasElementB = document.getElementById('outputCanvasB');
const canvasCtxB = canvasElementB.getContext('2d');

const uploadArea = document.getElementById('uploadArea');
const uploadAreaB = document.getElementById('uploadAreaB');
const videoUpload = document.getElementById('videoUpload');
const videoUploadB = document.getElementById('videoUploadB');
const playerWrapper = document.getElementById('playerWrapper');
const playerWrapperB = document.getElementById('playerWrapperB');
const comparisonToggle = document.getElementById('comparisonToggle');
const videoGrid = document.getElementById('videoGrid');
const playbackControls = document.getElementById('playbackControls');

const playBtn = document.getElementById('playBtn');
const progressBar = document.getElementById('progressBar');
const timeDisplay = document.getElementById('timeDisplay');
const loadingStatus = document.getElementById('loadingStatus');
const syncBtn = document.getElementById('syncBtn');
const actionPlanContainer = document.getElementById('actionPlanContainer');
const changeVideoBtnA = document.getElementById('changeVideoA');
const changeVideoBtnB = document.getElementById('changeVideoB');

// Metrics elements
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
const levelSelect = document.getElementById('targetLevel');
const xFactorEl = document.getElementById('xFactorAngle');
const xFactorFill = document.getElementById('xFactorFill');
const jumpHeightEl = document.getElementById('jumpHeight');
const jumpFill = document.getElementById('jumpFill');
const courtDriftEl = document.getElementById('courtDrift');
const driftFill = document.getElementById('driftFill');
const velocityChartCanvas = document.getElementById('velocityChart');

let selectedLevel = 'pro';
let velocityChart = null; // Chart.js instance

const BENCHMARKS = {
    pro: {
        shoulder: { min: 90, max: 110, label: "90° - 110°" },
        elbow: { min: 70, max: 100, label: "70° - 100°" },
        knee: { min: 110, max: 140, label: "110° - 140°" },
        racketDrop: { min: 0, max: 105, label: "< 100°" },
        pronation: { threshold: 60, label: "High Velocity Flick" },
        xFactor: { min: 30, max: 50, label: "30° - 50°" },
        jump: { min: 15, label: "> 15 in" },
        drift: { min: 3, label: "> 3 ft" }
    },
    junior: {
        shoulder: { min: 85, max: 115, label: "85° - 115°" },
        elbow: { min: 65, max: 110, label: "65° - 110°" },
        knee: { min: 100, max: 150, label: "100° - 150°" },
        racketDrop: { min: 0, max: 115, label: "< 110°" },
        pronation: { threshold: 45, label: "Stable Snap" },
        xFactor: { min: 20, max: 40, label: "20° - 40°" },
        jump: { min: 10, label: "> 10 in" },
        drift: { min: 2, label: "> 2 ft" }
    }
};

function updateBenchmarkLabels() {
    const config = BENCHMARKS[selectedLevel];
    document.getElementById('target-shoulder').innerText = config.shoulder.label;
    document.getElementById('target-elbow').innerText = config.elbow.label;
    document.getElementById('target-knee').innerText = config.knee.label;
    document.getElementById('target-racketDrop').innerText = config.racketDrop.label;
    document.getElementById('target-pronation').innerText = config.pronation.label;
    if (document.getElementById('target-xfactor')) document.getElementById('target-xfactor').innerText = config.xFactor.label;
    if (document.getElementById('target-jump')) document.getElementById('target-jump').innerText = config.jump.label;
    if (document.getElementById('target-drift')) document.getElementById('target-drift').innerText = config.drift.label;
}

levelSelect.addEventListener('change', (e) => {
    selectedLevel = e.target.value;
    updateBenchmarkLabels();
    if (isVideoSetup) {
        // Recalculate if already processed? Or just update labels.
        // For now, let's just update labels. The next play/results will use new level.
    }
});

let poseA, poseB;
let isVideoSetup = false;
let isVideoSetupB = false;
let animationId = null;
let poseResolveA = null;
let poseResolveB = null;
let comparisonMode = false;

// Multi-video Tracking State
const PHASE_STATES = {
    PRE_SERVE: 'PRE_SERVE',
    LOADING: 'LOADING',
    DROPPING: 'DROPPING',
    STRIKING: 'STRIKING',
    FINISHED: 'FINISHED'
};

let trackingDataA = {
    phaseState: PHASE_STATES.PRE_SERVE,
    stateStartTime: 0,
    maxShoulder: 0, maxShoulderTime: 0,
    minElbow: 180, minElbowTime: 0,
    minKnee: 180, minKneeTime: 0,
    minRacketDrop: 180, minRacketDropTime: 0,
    maxWristDrop: -1, // wrist depth below nose for racket drop detection
    maxPronation: 0, maxPronationTime: 0,
    maxXFactor: 0, maxXFactorTime: 0,
    impactTime: null,
    isServeStarted: false,
    history: [],
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
    tossArmPeakY: null,
    peakWristY: null,
    peakWristYTime: 0,
    framesProcessed: 0,
    descendCounter: 0,
    isDescendingFromPeak: false,
    lastWristPos: null,
    lastTime: 0,
    lastHipY: null,
    hasJumped: false,
    reachedTrophy: false,
    reachedTrophyPeak: false,
    trophyFlexion: 180,
    baselineHipY: null,
    baselineHipX: null,
    minHipY: 1.0,
    maxJump: 0,
    maxDrift: 0,
    frameBuffer: []
};

let trackingDataB = {
    phaseState: PHASE_STATES.PRE_SERVE,
    stateStartTime: 0,
    maxShoulder: 0, maxShoulderTime: 0,
    minElbow: 180, minElbowTime: 0,
    minKnee: 180, minKneeTime: 0,
    minRacketDrop: 180, minRacketDropTime: 0,
    maxWristDrop: -1,
    maxPronation: 0, maxPronationTime: 0,
    maxXFactor: 0, maxXFactorTime: 0,
    impactTime: null,
    isServeStarted: false,
    history: [],
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
    tossArmPeakY: null,
    peakWristY: null,
    peakWristYTime: 0,
    framesProcessed: 0,
    descendCounter: 0,
    isDescendingFromPeak: false,
    lastWristPos: null,
    lastTime: 0,
    lastHipY: null,
    hasJumped: false,
    reachedTrophy: false,
    reachedTrophyPeak: false,
    trophyFlexion: 180,
    baselineHipY: null,
    baselineHipX: null,
    minHipY: 1.0,
    maxJump: 0,
    maxDrift: 0,
    frameBuffer: []
};

let trackingData = trackingDataA; // Default to A for backward compatibility in functions

let trackingData = trackingDataA; // Default to A for backward compatibility in functions

// Pre-captured frame buffers: capture the exact frame BEFORE sending to MediaPipe
// This prevents the race condition where the video advances during async processing
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

    // Draw the PRE-CAPTURED frame (not the live video which may have advanced)
    ctx.drawImage(frameCanvas, 0, 0);

    // Also draw the skeleton overlay
    const mainCanvas = slot === 'A' ? canvasElement : canvasElementB;
    ctx.drawImage(mainCanvas, 0, 0, offscreenCanvas.width, offscreenCanvas.height);

    // DEBUG: Burn timestamp into frame to verify pre-capture timing
    ctx.fillStyle = 'rgba(0,0,0,0.7)';
    ctx.fillRect(0, 0, 240, 30);
    ctx.fillStyle = '#00ff00';
    ctx.font = '12px monospace';
    ctx.fillText(`PRE:${frameTime.toFixed(2)}s LIVE:${video.currentTime.toFixed(2)}s ${category}`, 5, 18);

    data.snapshots[category] = {
        img: offscreenCanvas.toDataURL('image/jpeg', 0.7),
        time: frameTime.toFixed(2)
    };
}

// Initialize MediaPipe Pose
// Initialize MediaPipe Pose
async function initPose() {
    const commonOptions = {
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    };

    poseA = new Pose({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}` });
    poseA.setOptions(commonOptions);
    poseA.onResults((res) => onResults(res, 'A'));

    poseB = new Pose({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}` });
    poseB.setOptions(commonOptions);
    poseB.onResults((res) => onResults(res, 'B'));

    // Test initialization — wrap in try/catch because the WASM module
    // throws a non-fatal "Module.arguments" error but still loads correctly
    try {
        await Promise.all([poseA.initialize(), poseB.initialize()]);
    } catch (err) {
        console.warn('MediaPipe initialization warning (non-fatal):', err.message || err);
        // The WASM module loads despite this error — processing will still work
    }

    loadingStatus.innerText = 'AI Ready. Please upload a video.';
    loadingStatus.style.background = 'rgba(46, 160, 67, 0.1)';
    loadingStatus.style.color = 'var(--success)';
}

// Calculate 3D angle between three points (A, B, C) where B is the vertex
function calculateAngle3D(a, b, c) {
    if (!a || !b || !c) return null;

    // Vector BA
    const v1 = {
        x: a.x - b.x,
        y: a.y - b.y,
        z: a.z - b.z
    };
    // Vector BC
    const v2 = {
        x: c.x - b.x,
        y: c.y - b.y,
        z: c.z - b.z
    };

    // Dot product
    const dotProduct = v1.x * v2.x + v1.y * v2.y + v1.z * v2.z;

    // Magnitudes
    const mag1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z);
    const mag2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y + v2.z * v2.z);

    // Angle in radians: cos(theta) = (v1 . v2) / (|v1| * |v2|)
    const angleRad = Math.acos(Math.max(-1, Math.min(1, dotProduct / (mag1 * mag2))));

    return Math.round((angleRad * 180.0) / Math.PI);
}

function updateMetricUI(element, fillElement, angle, category) {
    if (angle === null) {
        element.innerText = '--°';
        fillElement.style.width = '0%';
        return;
    }

    const config = BENCHMARKS[selectedLevel][category];
    const isPronation = category === 'pronation';
    const isXFactor = category === 'xFactor';

    if (isPronation) {
        element.innerText = `${angle.toFixed(2)}%`;
        fillElement.style.width = `${angle}%`;
        fillElement.style.backgroundColor = angle >= config.threshold ? 'var(--success)' : 'var(--warning)';
        return;
    }

    if (isXFactor) {
        element.innerText = `${angle.toFixed(2)}°`;
        const percent = Math.min(100, Math.max(0, (angle / 60) * 100));
        fillElement.style.width = `${percent}%`;
    } else {
        element.innerText = `${angle}°`;
        const percent = Math.min(100, Math.max(0, (angle / 180) * 100));
        fillElement.style.width = `${percent}%`;
    }

    const minIdeal = config.min;
    const maxIdeal = config.max;

    if (angle >= minIdeal && angle <= maxIdeal) {
        element.style.color = 'var(--success)';
        fillElement.style.backgroundColor = 'var(--success)';
    } else {
        const diff = Math.min(Math.abs(angle - minIdeal), Math.abs(angle - maxIdeal));
        if (diff < 15) {
            element.style.color = 'var(--warning)';
            fillElement.style.backgroundColor = 'var(--warning)';
        } else {
            element.style.color = 'var(--danger)';
            fillElement.style.backgroundColor = 'var(--danger)';
        }
    }
}

// Helper to update labels when switching modes
function updateUIMode() {
    if (comparisonMode) {
        videoGrid.classList.add('comparison-mode');
        uploadAreaB.style.display = 'flex';
        videoItemB.style.display = 'block';
        document.getElementById('uploadTextA').innerText = 'Upload Serve A (Pro Baseline)';
    } else {
        videoGrid.classList.remove('comparison-mode');
        uploadAreaB.style.display = 'none';
        videoItemB.style.display = 'none';
        playerWrapperB.style.display = 'none';
        document.getElementById('uploadTextA').innerText = 'Drag & Drop serve video here or click to browse';
    }
}

comparisonToggle.addEventListener('change', (e) => {
    comparisonMode = e.target.checked;
    updateUIMode();
});

function resetTracking(mode = 'A') {
    const freshData = {
        phaseState: PHASE_STATES.PRE_SERVE,
        stateStartTime: 0,
        maxShoulder: 0, maxShoulderTime: 0,
        minElbow: 180, minElbowTime: 0,
        minKnee: 180, minKneeTime: 0,
        minRacketDrop: 180, minRacketDropTime: 0,
        maxWristDrop: -1,
        maxPronation: 0, maxPronationTime: 0,
        maxXFactor: 0, maxXFactorTime: 0,
        impactTime: null,
        isServeStarted: false,
        history: [],
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
        tossArmPeakY: null,
        peakWristY: null,
        peakWristYTime: 0,
        framesProcessed: 0,
        descendCounter: 0,
        isDescendingFromPeak: false,
        lastWristPos: null,
        lastTime: 0,
        lastHipY: null,
        hasJumped: false,
        reachedTrophy: false,
        reachedTrophyPeak: false,
        trophyFlexion: 180,
        baselineHipY: null,
        baselineHipX: null,
        minHipY: 1.0,
        maxJump: 0,
        maxDrift: 0,
        frameBuffer: []
    };

    // Replace the entire object reference to guarantee zero state pollution
    if (mode === 'A') {
        trackingDataA = freshData;
    } else {
        trackingDataB = freshData;
    }

    if (mode === 'A') {
        loadingStatus.innerText = 'AI Ready. Upload video below.';
        document.getElementById('actionPlanContainer').style.display = 'none';
        document.getElementById('flawList').innerHTML = '';
        document.getElementById('trainingPlan').innerHTML = '';
    }
}

// Handle pose results
function onResults(results, slot) {
    const video = slot === 'A' ? videoElement : videoElementB;
    const canvas = slot === 'A' ? canvasElement : canvasElementB;
    const ctx = slot === 'A' ? canvasCtx : canvasCtxB;
    const data = slot === 'A' ? trackingDataA : trackingDataB;

    if (!video.videoWidth) return;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (results.poseLandmarks) {
        drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS,
            { color: slot === 'A' ? 'rgba(88, 166, 255, 0.6)' : 'rgba(255, 106, 51, 0.6)', lineWidth: 4 });
        drawLandmarks(ctx, results.poseLandmarks,
            { color: '#0d1117', fillColor: slot === 'A' ? '#58a6ff' : '#ff6a33', lineWidth: 2, radius: 4 });

        const landmarks = results.poseWorldLandmarks || results.poseLandmarks;
        const rawLandmarks = results.poseLandmarks;

        const visThreshold = 0.5; // Lowered to handle adverse lighting/angles
        const shoulderVis = rawLandmarks[12].visibility > visThreshold && rawLandmarks[14].visibility > visThreshold && rawLandmarks[24].visibility > visThreshold;
        const elbowVis = rawLandmarks[14].visibility > visThreshold && rawLandmarks[16].visibility > visThreshold && rawLandmarks[12].visibility > visThreshold;
        const kneeVis = rawLandmarks[26].visibility > visThreshold && rawLandmarks[28].visibility > visThreshold && rawLandmarks[24].visibility > visThreshold;
        const tossingArmVis = rawLandmarks[11].visibility > visThreshold && rawLandmarks[13].visibility > visThreshold && rawLandmarks[15].visibility > visThreshold;

        const shoulderAng = shoulderVis ? calculateAngle3D(landmarks[24], landmarks[12], landmarks[14]) : null;
        const elbowAng = elbowVis ? calculateAngle3D(landmarks[12], landmarks[14], landmarks[16]) : null;
        const kneeAng = kneeVis ? calculateAngle3D(landmarks[24], landmarks[26], landmarks[28]) : null;
        const tossingArmAngle = tossingArmVis ? calculateAngle3D(landmarks[23], landmarks[11], landmarks[13]) : null;

        const isServePhase = rawLandmarks[16].y < (rawLandmarks[12].y + 0.3); // More inclusive window
        const currentWristY = rawLandmarks[16].y;
        const currentTime = video.currentTime;
        const isHandUp = rawLandmarks[16].y < rawLandmarks[12].y; // Hand above shoulder instead of nose for reliability

        // --- Metric Calculations First (Avoid Hoisting) ---
        let pronationIndex = 0;
        let smoothedVelocity = 0;
        if (data.lastWristPos && isServePhase) {
            const dt = currentTime - data.lastTime;
            // Guard against tiny dt which leads to massive velocity spikes from jitter
            if (dt > 0.005) {
                const dx = rawLandmarks[16].x - data.lastWristPos.x;
                const dy = rawLandmarks[16].y - data.lastWristPos.y;
                const dz = rawLandmarks[16].z - data.lastWristPos.z || 0;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
                const velocity = (dist / dt) * 100;
                data.velocityHistory.push({ time: currentTime, v: velocity, dy: dy });

                // 5-frame moving average for professional stability
                const historyLen = data.velocityHistory.length;
                if (historyLen >= 5) {
                    smoothedVelocity = (data.velocityHistory[historyLen - 1].v +
                        data.velocityHistory[historyLen - 2].v +
                        data.velocityHistory[historyLen - 3].v +
                        data.velocityHistory[historyLen - 4].v +
                        data.velocityHistory[historyLen - 5].v) / 5;
                } else if (historyLen > 0) {
                    smoothedVelocity = velocity;
                }
                pronationIndex = Math.min(100, smoothedVelocity);
            } else {
                // Keep previous smoothed velocity if frame time is too small
                smoothedVelocity = data.velocityHistory.length > 0 ?
                    data.velocityHistory[data.velocityHistory.length - 1].v : 0;
            }
        }
        data.lastWristPos = { x: rawLandmarks[16].x, y: rawLandmarks[16].y, z: rawLandmarks[16].z };
        data.lastTime = currentTime;

        const hipVec = { x: landmarks[24].x - landmarks[23].x, z: landmarks[24].z - landmarks[23].z };
        const shldVec = { x: landmarks[12].x - landmarks[11].x, z: landmarks[12].z - landmarks[11].z };
        const hipRot = Math.atan2(hipVec.z, hipVec.x);
        const shldRot = Math.atan2(shldVec.z, shldVec.x);
        let xFactor = Math.abs(shldRot - hipRot) * (180 / Math.PI);
        if (xFactor > 180) xFactor = 360 - xFactor;
        if (xFactor > 90) xFactor = 180 - xFactor;

        const currentHipY = (rawLandmarks[23].y + rawLandmarks[24].y) / 2;
        const hipX = (rawLandmarks[23].x + rawLandmarks[24].x) / 2;

        if (data.reachedTrophy && data.lastHipY && currentHipY < data.lastHipY - 0.03) {
            data.hasJumped = true;
        }

        // --- State Transitions & Snapshot Logic ---

        // Start Serve detection: REQUIRE hitting wrist above nose AND tossing hand above shoulder
        const isWristHigh = rawLandmarks[16].y < rawLandmarks[0].y;
        const isTossingHigh = tossingArmVis && rawLandmarks[15].y < rawLandmarks[12].y;

        if (!data.isServeStarted && isWristHigh && isTossingHigh) {
            // Full Reset for new serve
            data.isServeStarted = true;
            data.phaseState = PHASE_STATES.LOADING;
            data.stateStartTime = currentTime;
            console.log(`[${slot}] SERVE START at ${currentTime.toFixed(2)}s | shoulderAng=${shoulderAng.toFixed(1)} elbowAng=${elbowAng?.toFixed(1)} wristY=${rawLandmarks[16].y.toFixed(3)} noseY=${rawLandmarks[0].y.toFixed(3)}`);
            data.serveStartTime = currentTime; // Store for filtering pre-serve frames
            data.baselineHipY = currentHipY;
            data.baselineHipX = hipX;
            data.maxXFactor = 0;
            data.minRacketDrop = 180;
            data.maxShoulder = 0;
            data.minKnee = 180;
            data.maxPronation = 0;
            data.impactDetected = false;
            data.reachedTrophy = false;
            data.reachedTrophyPeak = false;
            data.snapshots = {
                trophy: { img: null, time: null },
                kneeBend: { img: null, time: null },
                racketDrop: { img: null, time: null },
                impact: { img: null, time: null },
                finish: { img: null, time: null },
                xFactor: { img: null, time: null }
            };
            // NOTE: frameBuffer is NOT cleared here — pre-serve frames contain knee bend data
        }

        const hipY = currentHipY;
        if (data.baselineHipY) {
            // Track highest point of hip during the serve
            if (hipY < data.minHipY) data.minHipY = hipY;
            // Vertical Explosion (Rough estimate: 1.0 screen height ≈ 80 inches)
            const jumpInches = Math.max(0, (data.baselineHipY - data.minHipY) * 80);
            data.maxJump = Math.max(data.maxJump, jumpInches);

            // Court Penetration (Horizontal Drift)
            const horizontalDrift = Math.abs(hipX - data.baselineHipX) * 15;
            data.maxDrift = Math.max(data.maxDrift, horizontalDrift);
        }

        // Save History for Comparison
        data.history.push({
            time: video.currentTime,
            shoulder: shoulderAng,
            elbow: elbowAng,
            knee: kneeAng,
            pronation: pronationIndex,
            xFactor: xFactor,
            isDescending: data.isDescendingFromPeak
        });

        // UI Updates: Prioritize Slot A for sidebar to avoid flickering in comparison mode
        if (slot === 'A') {
            updateMetricUI(shoulderEl, shoulderFill, shoulderAng, 'shoulder');
            updateMetricUI(elbowEl, elbowFill, elbowAng, 'elbow');
            updateMetricUI(kneeEl, kneeFill, kneeAng, 'knee');
            updateMetricUI(racketDropEl, racketDropFill, elbowAng, 'racketDrop');
            updateMetricUI(pronationEl, pronationFill, pronationIndex, 'pronation');
            updateMetricUI(xFactorEl, xFactorFill, xFactor, 'xFactor');

            if (data.maxJump > 0) {
                jumpHeightEl.innerText = `${data.maxJump.toFixed(1)} in`;
                jumpFill.style.width = `${Math.min(100, (data.maxJump / 30) * 100)}%`;
                jumpFill.style.background = 'linear-gradient(90deg, var(--success), #34d399)';
            }
            if (data.maxDrift > 0) {
                courtDriftEl.innerText = `${data.maxDrift.toFixed(1)} ft`;
                driftFill.style.width = `${Math.min(100, (data.maxDrift / 6) * 100)}%`;
                driftFill.style.background = 'linear-gradient(90deg, #58a6ff, #00d2ff)';
            }
        }

        // --- Impact detection & State Transitions ---
        const isImpactHeight = currentWristY < rawLandmarks[12].y - 0.1;

        // Transition: DROPPING -> STRIKING
        const isExtending = elbowAng !== null && data.minRacketDrop < 155 && (elbowAng > data.minRacketDrop + 15);
        // Robust Trigger: High smoothed velocity (>250), upward movement (dy < 0), and arm raised
        const latestVelData = data.velocityHistory.length > 0 ? data.velocityHistory[data.velocityHistory.length - 1] : null;
        const isMovingUp = latestVelData && latestVelData.dy < -0.005; // Significant upward movement

        if (data.phaseState === PHASE_STATES.DROPPING && isHandUp && shoulderAng > 100 && (isMovingUp && (isExtending || smoothedVelocity > 250))) {
            console.log(`[${slot}] DROPPING -> STRIKING at ${currentTime.toFixed(2)}s | vel=${smoothedVelocity.toFixed(1)} extending=${isExtending} movingUp=${isMovingUp}`);
            data.phaseState = PHASE_STATES.STRIKING;
            data.stateStartTime = currentTime;
            data.strikeStartTime = currentTime;

            // === RETROACTIVE CAPTURES at DROPPING→STRIKING ===
            if (data.frameBuffer && data.frameBuffer.length > 0) {
                const sst = data.serveStartTime || 0;
                // Racket drop: only search LAST 40% of serve (back-scratch is late, not during early backswing)
                const racketDropEarliestTime = sst + 0.6 * (currentTime - sst);
                let bestRacket = null;
                let lowestElbow = 180;
                let bestKnee = null;
                let lowestKnee = 180;
                let bestXFactor = null;
                let highestXF = 0;

                for (const frame of data.frameBuffer) {
                    const isServeFrame = frame.time >= sst;
                    // Racket drop: ONLY late serve frames (last 40%)
                    if (isServeFrame && frame.time >= racketDropEarliestTime && frame.elbowAng != null && frame.elbowAng < lowestElbow) { lowestElbow = frame.elbowAng; bestRacket = frame; }
                    // Knee bend: ALL frames including pre-serve
                    if (frame.kneeAng != null && frame.kneeAng < lowestKnee) { lowestKnee = frame.kneeAng; bestKnee = frame; }
                    // X-Factor: ONLY serve frames
                    if (isServeFrame && frame.xFactor != null && frame.xFactor > highestXF) { highestXF = frame.xFactor; bestXFactor = frame; }
                }

                // Apply racket drop (lowest elbow angle = deepest back-scratch position)
                if (bestRacket) {
                    console.log(`[${slot}] RACKET DROP (retroactive) from ${bestRacket.time.toFixed(2)}s | elbowAng=${lowestElbow.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                    data.snapshots.racketDrop = { img: bestRacket.img, time: bestRacket.time.toFixed(2) };
                    data.minRacketDropTime = bestRacket.time;
                }

                // Apply knee bend (retroactive) if better than real-time capture
                if (bestKnee && lowestKnee < data.minKnee) {
                    console.log(`[${slot}] KNEE BEND (retroactive) from ${bestKnee.time.toFixed(2)}s | kneeAng=${lowestKnee.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                    data.minKnee = lowestKnee;
                    data.minKneeTime = bestKnee.time;
                    data.snapshots.kneeBend = { img: bestKnee.img, time: bestKnee.time.toFixed(2) };
                }

                // Apply X-Factor: ALWAYS pick best from entire buffer (overrides early LOADING captures)
                if (bestXFactor) {
                    console.log(`[${slot}] X-FACTOR (retroactive) from ${bestXFactor.time.toFixed(2)}s | xFactor=${highestXF.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                    data.maxXFactor = highestXF;
                    data.maxXFactorTime = bestXFactor.time;
                    data.snapshots.xFactor = { img: bestXFactor.img, time: bestXFactor.time.toFixed(2) };
                }
            }
        }
        // FIX #4: Fallback - If stuck in DROPPING > 1.5s, force transition to STRIKING
        if (data.phaseState === PHASE_STATES.DROPPING && (currentTime - data.stateStartTime) > 1.5) {
            data.phaseState = PHASE_STATES.STRIKING;
            data.stateStartTime = currentTime;
            data.strikeStartTime = currentTime;
        }

        // Loosened impact requirements: 145° extension and -0.05 margin (was 160° and -0.1)
        const isImpactCandidate = isImpactHeight || currentWristY < rawLandmarks[12].y - 0.05;
        if (data.phaseState === PHASE_STATES.STRIKING && !data.impactDetected && isImpactCandidate && (elbowAng === null || elbowAng > 145)) {
            if (!data.peakWristY || currentWristY < data.peakWristY) {
                data.peakWristY = currentWristY;
                data.peakWristYTime = currentTime;
                data.isDescendingFromPeak = false;
                captureFrame(video, 'impact', slot);
            } else if (currentWristY > data.peakWristY + 0.015 && !data.isDescendingFromPeak) {
                if (currentWristY > data.peakWristY + 0.03 || (currentTime - data.peakWristYTime > 0.04)) {
                    data.impactTime = data.peakWristYTime;
                    data.impactDetected = true;
                    data.isDescendingFromPeak = true;

                    // === RETROACTIVE CAPTURES at IMPACT (override STRIKING-based selections) ===
                    // By IMPACT, the buffer has MORE frames than at STRIKING, including the correct back-scratch
                    if (data.frameBuffer && data.frameBuffer.length > 0) {
                        // RACKET DROP: lowest elbowAng from serve frames (speed-independent)
                        let bestRacket = null;
                        let lowestElbow = 180;
                        let bestXF = null;
                        let highestXF = 0;

                        // Racket drop: only last 40% of serve (back-scratch is late, not backswing)
                        const sst = data.serveStartTime || 0;
                        const racketDropEarliestTime = sst + 0.6 * (data.impactTime - sst);
                        for (const frame of data.frameBuffer) {
                            const isServeFrame = frame.time >= sst;
                            if (!isServeFrame) continue;
                            // Racket drop: lowest elbowAng from LATE serve frames only
                            if (frame.time >= racketDropEarliestTime && frame.elbowAng != null && frame.elbowAng < lowestElbow) { lowestElbow = frame.elbowAng; bestRacket = frame; }
                            if (frame.xFactor != null && frame.xFactor > highestXF) { highestXF = frame.xFactor; bestXF = frame; }
                        }

                        if (bestRacket) {
                            console.log(`[${slot}] RACKET DROP (impact-based) from ${bestRacket.time.toFixed(2)}s | elbowAng=${bestRacket.elbowAng?.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                            data.snapshots.racketDrop = { img: bestRacket.img, time: bestRacket.time.toFixed(2) };
                            data.minRacketDropTime = bestRacket.time;
                        }
                        if (bestXF) {
                            console.log(`[${slot}] X-FACTOR (impact-based) from ${bestXF.time.toFixed(2)}s | xFactor=${highestXF.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                            data.maxXFactor = highestXF;
                            data.maxXFactorTime = bestXF.time;
                            data.snapshots.xFactor = { img: bestXF.img, time: bestXF.time.toFixed(2) };
                        }
                    }
                }
            }
        }


        // X-Factor peak detection: Removed from STRIKING, moved to LOADING/DROPPING for better coil capture
        // (Moved logic below to phase-specific blocks)

        // Tracking peaks (only before FINISHED)
        if (data.phaseState !== PHASE_STATES.FINISHED) {
            // Update Shoulder Abduction (Check 1) - Gate by serve start
            if (data.isServeStarted && shoulderAng > data.maxShoulder) {
                data.maxShoulder = shoulderAng;
                data.maxShoulderTime = video.currentTime;
            }

            // 1. Trophy & Phase Transition Logic
            if (data.phaseState === PHASE_STATES.LOADING) {
                const tossVisThresh = 0.3;
                const isArmLoaded = elbowAng !== null && elbowAng < 165;
                const currentTossY = rawLandmarks[15].y;

                if (rawLandmarks[15].visibility > tossVisThresh && isArmLoaded && shoulderAng > 60) {
                    if (data.tossArmPeakY === null || currentTossY < data.tossArmPeakY) {
                        if (currentTossY < rawLandmarks[0].y && shoulderAng > 80) {
                            data.tossArmPeakY = currentTossY;
                            data.trophyFlexion = elbowAng;
                            data.reachedTrophy = true;
                            // Real-time trophy capture (will be improved retroactively at DROPPING transition)
                            console.log(`[${slot}] TROPHY tracked at ${currentTime.toFixed(2)}s | shoulderAng=${shoulderAng.toFixed(1)} elbowAng=${elbowAng?.toFixed(1)} tossY=${currentTossY.toFixed(3)}`);
                            captureFrame(video, 'trophy', slot);
                        }
                    } else if (currentTossY > data.tossArmPeakY + 0.05) {
                        console.log(`[${slot}] LOADING -> DROPPING (toss descent) at ${currentTime.toFixed(2)}s | tossY=${currentTossY.toFixed(3)} peakY=${data.tossArmPeakY.toFixed(3)}`);
                        data.reachedTrophyPeak = true;
                        data.phaseState = PHASE_STATES.DROPPING;
                        data.stateStartTime = currentTime;

                        // === RETROACTIVE CAPTURES at LOADING→DROPPING ===
                        if (data.frameBuffer && data.frameBuffer.length > 0) {
                            // TROPHY: The trophy position = maximum body loading.
                            // This is when legs are bent AND hitting arm is back.
                            // Search ALL frames (including pre-serve) since in slow-mo,
                            // the real trophy happens before our serve detection triggers.
                            // Composite score: kneeAng + elbowAng (lower = more loaded)
                            const sst = data.serveStartTime || 0;
                            let bestTrophy = null;
                            let bestTrophyScore = Infinity;
                            for (const frame of data.frameBuffer) {
                                // Only consider frames where toss arm is reasonably elevated
                                if (frame.tossY != null && frame.tossY < 0.50
                                    && frame.kneeAng != null && frame.elbowAng != null) {
                                    const score = frame.kneeAng + frame.elbowAng;
                                    if (score < bestTrophyScore) {
                                        bestTrophyScore = score;
                                        bestTrophy = frame;
                                    }
                                }
                            }
                            // Fallback: if no frame with toss elevated, use lowest elbowAng from buffer
                            if (!bestTrophy) {
                                let lowestElbow = 180;
                                for (const frame of data.frameBuffer) {
                                    if (frame.elbowAng != null && frame.elbowAng < lowestElbow) {
                                        lowestElbow = frame.elbowAng;
                                        bestTrophy = frame;
                                    }
                                }
                            }
                            if (bestTrophy) {
                                console.log(`[${slot}] TROPHY (retroactive) from ${bestTrophy.time.toFixed(2)}s | kneeAng=${bestTrophy.kneeAng?.toFixed(1)} elbowAng=${bestTrophy.elbowAng?.toFixed(1)} score=${bestTrophyScore.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                                data.snapshots.trophy = { img: bestTrophy.img, time: bestTrophy.time.toFixed(2) };
                            }
                            // X-FACTOR and KNEE BEND: scan buffer for best values
                            let bestXF = null, highestXF = 0;
                            let bestKnee = null, lowestKnee = 180;
                            for (const frame of data.frameBuffer) {
                                const isServeFrame = frame.time >= sst;
                                // X-Factor: ONLY serve frames
                                if (isServeFrame && frame.xFactor != null && frame.xFactor > highestXF) { highestXF = frame.xFactor; bestXF = frame; }
                                // Knee bend: ALL frames including pre-serve
                                if (frame.kneeAng != null && frame.kneeAng < lowestKnee) { lowestKnee = frame.kneeAng; bestKnee = frame; }
                            }
                            if (bestXF) {
                                console.log(`[${slot}] X-FACTOR (retroactive/LOADING) from ${bestXF.time.toFixed(2)}s | xFactor=${highestXF.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                                data.maxXFactor = highestXF;
                                data.maxXFactorTime = bestXF.time;
                                data.snapshots.xFactor = { img: bestXF.img, time: bestXF.time.toFixed(2) };
                            }
                            if (bestKnee) {
                                console.log(`[${slot}] KNEE BEND (retroactive/LOADING) from ${bestKnee.time.toFixed(2)}s | kneeAng=${lowestKnee.toFixed(1)} | bufferSize=${data.frameBuffer.length}`);
                                data.minKnee = lowestKnee;
                                data.minKneeTime = bestKnee.time;
                                data.snapshots.kneeBend = { img: bestKnee.img, time: bestKnee.time.toFixed(2) };
                            }
                        }
                    }
                }

                // Fallback: If toss is obscured, shoulder height confirms loading phase
                const timeSinceStart = currentTime - data.stateStartTime;
                if (!data.reachedTrophy && shoulderAng > 90 && isArmLoaded && timeSinceStart > 0.3) {
                    console.log(`[${slot}] TROPHY (fallback) at ${currentTime.toFixed(2)}s | shoulderAng=${shoulderAng.toFixed(1)} elbowAng=${elbowAng?.toFixed(1)}`);
                    data.reachedTrophy = true;
                    data.trophyFlexion = elbowAng;
                    captureFrame(video, 'trophy', slot);
                }

                // Fallback: Transition to DROPPING if arm bends significantly
                const timeInLoadingAfterTrophy = currentTime - data.stateStartTime;
                if (data.reachedTrophy && isHandUp && elbowAng < 135 && timeInLoadingAfterTrophy > 0.3) {
                    console.log(`[${slot}] LOADING -> DROPPING (elbow bend fallback) at ${currentTime.toFixed(2)}s | elbowAng=${elbowAng?.toFixed(1)} timeInLoading=${timeInLoadingAfterTrophy.toFixed(2)}`);
                    data.reachedTrophyPeak = true;
                    data.phaseState = PHASE_STATES.DROPPING;
                    data.stateStartTime = currentTime;
                }

                // Real-time knee bend tracking (updated retroactively at transitions)
                if (kneeAng != null && kneeAng < data.minKnee && !data.hasJumped) {
                    data.minKnee = kneeAng;
                    data.minKneeTime = video.currentTime;
                    captureFrame(video, 'kneeBend', slot);
                }

                // Real-time X-Factor tracking in LOADING
                // Gate: at least 0.5s after serve start so body has time to coil
                const timeForXFactor = currentTime - data.stateStartTime;
                if (data.reachedTrophy && timeForXFactor > 0.5 && xFactor != null && xFactor > data.maxXFactor) {
                    console.log(`[${slot}] X-FACTOR captured at ${currentTime.toFixed(2)}s | xFactor=${xFactor.toFixed(1)} phase=LOADING`);
                    data.maxXFactor = xFactor;
                    data.maxXFactorTime = currentTime;
                    captureFrame(video, 'xFactor', slot);
                }
            } // END of LOADING phase block

            // FRAME BUFFER: Buffer ALL frames (including pre-serve) for retroactive capture
            // Pre-serve frames are needed to capture knee bend during wind-up (before arms trigger serve detection)
            if (data.phaseState !== PHASE_STATES.FINISHED) {
                const frameCanvas = slot === 'A' ? lastCapturedFrameA : lastCapturedFrameB;
                const frameTime = slot === 'A' ? lastCapturedTimeA : lastCapturedTimeB;
                if (frameCanvas) {
                    const bufCanvas = document.createElement('canvas');
                    bufCanvas.width = frameCanvas.width;
                    bufCanvas.height = frameCanvas.height;
                    const bufCtx = bufCanvas.getContext('2d');
                    bufCtx.drawImage(frameCanvas, 0, 0);
                    const mainCanvas = slot === 'A' ? canvasElement : canvasElementB;
                    bufCtx.drawImage(mainCanvas, 0, 0, bufCanvas.width, bufCanvas.height);
                    // Debug overlay
                    bufCtx.fillStyle = 'rgba(0,0,0,0.7)';
                    bufCtx.fillRect(0, 0, 280, 30);
                    bufCtx.fillStyle = '#00ff00';
                    bufCtx.font = '12px monospace';
                    bufCtx.fillText(`PRE:${frameTime.toFixed(2)}s LIVE:${video.currentTime.toFixed(2)}s ${data.phaseState}`, 5, 18);

                    if (!data.frameBuffer) data.frameBuffer = [];
                    data.frameBuffer.push({
                        img: bufCanvas.toDataURL('image/jpeg', 0.7),
                        time: frameTime,
                        elbowAng: elbowAng,
                        kneeAng: kneeAng,
                        shoulderAng: shoulderAng,
                        tossY: rawLandmarks[15].y,
                        xFactor: xFactor
                    });
                    // Keep 80 frames (~4s at 20fps) to capture pre-serve wind-up
                    if (data.frameBuffer.length > 80) data.frameBuffer.shift();
                }
            }

            // Also track knee bend in DROPPING (deepest bend often spans phases)
            if (data.phaseState === PHASE_STATES.DROPPING && kneeAng != null && kneeAng < data.minKnee && !data.hasJumped) {
                data.minKnee = kneeAng;
                data.minKneeTime = video.currentTime;
                captureFrame(video, 'kneeBend', slot);
            }

            // Continue tracking metrics in DROPPING phase
            if (data.phaseState === PHASE_STATES.DROPPING) {
                // Track elbow angle for the metric display
                if (elbowAng != null && elbowAng < data.minRacketDrop) {
                    data.minRacketDrop = elbowAng;
                    data.minRacketDropTime = currentTime;
                }
                // Track X-Factor metric (no snapshot — handled retroactively)
                if (xFactor != null && xFactor > data.maxXFactor) {
                    data.maxXFactor = xFactor;
                    data.maxXFactorTime = currentTime;
                }
            }
        }

        // 3. Follow Through / Finish
        // Gate: Start looking for finish once striking begins
        if (data.phaseState === PHASE_STATES.STRIKING || data.phaseState === PHASE_STATES.FINISHED) {
            const timeSinceImpact = data.impactDetected ? (currentTime - data.impactTime) : 0;
            const handDropped = rawLandmarks[16].y > rawLandmarks[12].y + 0.15; // Hand well below shoulder

            // Transition to FINISHED
            if (!data.impactDetected && handDropped && currentTime > (data.peakWristYTime || 0) + 0.2) {
                // Safety transition if impact missed but follow-through started
                data.phaseState = PHASE_STATES.FINISHED;
            }

            if (data.impactDetected && data.phaseState !== PHASE_STATES.FINISHED) {
                data.phaseState = PHASE_STATES.FINISHED;
            }

            // Capture Finish Snapshot
            // Capture Finish Snapshot: Accelerated timing (0.4s instead of 0.6s)
            if (data.phaseState === PHASE_STATES.FINISHED && !data.snapshots.finish.img) {
                if (timeSinceImpact > 1.2 || (timeSinceImpact > 0.4 && handDropped)) {
                    captureFrame(video, 'finish', slot);
                }
            }
        }

        // Only track pronation speed during active serve strike
        const isLiveStrike = data.phaseState === PHASE_STATES.STRIKING;
        if (isLiveStrike && pronationIndex > data.maxPronation) {
            data.maxPronation = pronationIndex;
            data.maxPronationTime = video.currentTime;
        }

        data.framesProcessed++;
        data.lastHipY = currentHipY;
    }
    ctx.restore();

    if (slot === 'A' && poseResolveA) { poseResolveA(); poseResolveA = null; }
    if (slot === 'B' && poseResolveB) { poseResolveB(); poseResolveB = null; }
}

function generateActionPlan() {
    if (comparisonMode) {
        generateComparisonReport();
        return;
    }

    if (trackingDataA.framesProcessed < 1) {
        loadingStatus.innerText = 'Error: No serve motion detected.';
        return;
    }

    // Default to A data
    const trackingData = trackingDataA;

    const container = document.getElementById('actionPlanContainer');
    const flawList = document.getElementById('flawList');
    const trainingPlan = document.getElementById('trainingPlan');
    const scoreBadge = document.getElementById('overallScore');
    const assessmentLevel = document.getElementById('assessmentLevel');
    const config = BENCHMARKS[selectedLevel];

    assessmentLevel.innerText = selectedLevel === 'pro' ? 'ATP/WTA PRO LEVEL' : 'ITF JUNIOR TOP 200';

    flawList.innerHTML = '';
    trainingPlan.innerHTML = '';
    let flawsFound = 0;
    let stepCount = 1;

    // List of all checks to perform
    const checks = [
        {
            id: 1,
            name: 'Shoulder Abduction (Elbow Height)',
            value: Math.round(trackingData.maxShoulder),
            target: config.shoulder.label,
            isFlaw: trackingData.maxShoulder < config.shoulder.min,
            unit: '°',
            snapshot: trackingData.snapshots.trophy?.img || null,
            time: trackingData.snapshots.trophy?.time || '0:00',
            flawTitle: 'Shoulder Angle Error',
            flawText: `Shoulder abduction peaked at only ${Math.round(trackingData.maxShoulder)}°. Your elbow never reached the necessary height to clear the shoulder line, reducing leverage and increasing injury risk.`,
            drillTitle: 'Wall Stretch & Toss Alignment',
            drillText: 'Stand with your back against a fence. Go into your trophy pose. Your right elbow must touch the fence at exactly shoulder-height. If it\'s lower, adjust immediately. Muscle memory will reset after 50 reps.'
        },
        {
            id: 2,
            name: 'Elbow Flexion (Trophy Position)',
            value: Math.round(trackingData.trophyFlexion || 180),
            target: config.elbow.label,
            isFlaw: trackingData.trophyFlexion < config.elbow.min || trackingData.trophyFlexion > config.elbow.max,
            unit: '°',
            snapshot: trackingData.snapshots.trophy?.img || null,
            time: trackingData.snapshots.trophy?.time || '0:00',
            flawTitle: 'Trophy Pose Leak',
            flawText: `Flexion reached ${Math.round(trackingData.trophyFlexion || 180)}°. This "Trophy Pose Leak" causes a severe power disconnect during the loading phase.`,
            drillTitle: 'The Waiter\'s Tray Drill',
            drillText: 'Hold the racket in the trophy position. Place a spare ball in the throat of the racket. If your elbow drops too low, the ball will fall out. Perform 20 dry swings focusing entirely on holding the angle before accelerating.'
        },
        {
            id: 3,
            name: 'Knee Bend (Power Load)',
            value: Math.round(trackingData.minKnee),
            target: config.knee.label,
            isFlaw: trackingData.minKnee > config.knee.max,
            unit: '°',
            snapshot: trackingData.snapshots.kneeBend?.img || null,
            time: trackingData.snapshots.kneeBend?.time || '0:00',
            flawTitle: 'Insufficient Leg Drive',
            flawText: `Knee angle reached ${Math.round(trackingData.minKnee)}°. This "Insufficient Leg Drive" means you are arming the ball because your lower body is disengaged from the kinetic chain.`,
            drillTitle: 'Medicine Ball Throw',
            drillText: 'Hold a 4lb medicine ball. Drop your hips into a deep squat (feeling the tension in your calves and quads), then explode up, throwing the ball vertically. Translate this explosive kinetic sequence back to the serve.'
        },
        {
            id: 4,
            name: 'Racket Drop Depth',
            value: Math.round(trackingData.minRacketDrop),
            target: config.racketDrop.label,
            isFlaw: trackingData.minRacketDrop > config.racketDrop.max,
            unit: '°',
            snapshot: trackingData.snapshots.racketDrop?.img || null,
            time: trackingData.snapshots.racketDrop?.time || '0:00',
            flawTitle: 'Shallow Racket Drop',
            flawText: `Maximum racket drop was only ${Math.round(trackingData.minRacketDrop)}°. A shallow racket drop shortens your "power runway," leading to significantly lower head speeds at impact.`,
            drillTitle: 'The "Back-Scratch" Pause',
            drillText: 'Perform serves where you intentionally pause for 1 second at the deepest point of the racket drop. This forces you to feel the stretch in your triceps and chest before the upward explosion.'
        },
        {
            id: 5,
            name: 'Pronation Snap',
            value: Math.round(trackingData.maxPronation),
            target: config.pronation.label,
            isFlaw: trackingData.maxPronation < config.pronation.threshold,
            unit: '%',
            snapshot: trackingData.snapshots.impact?.img || null,
            time: trackingData.snapshots.impact?.time || '0:00',
            flawTitle: 'Weak Pronation Snap',
            flawText: `Pronation velocity index: ${Math.round(trackingData.maxPronation)}%. You are "pushing" the serve rather than "snapping" it. This lack of internal rotation is the #1 cause of low serve percentages.`,
            drillTitle: 'Edge-to-Flat Shadow Swings',
            drillText: 'Swing your racket edge-first towards an imaginary ball, then at the last millisecond, snap your wrist so the strings are flat at impact. Do this 30 times without a ball to hear the "whoosh" of the racket head.'
        },
        {
            id: 6,
            name: 'X-Factor Separation',
            value: Math.round(trackingData.maxXFactor),
            target: config.xFactor.label,
            isFlaw: trackingData.maxXFactor < config.xFactor.min,
            unit: '°',
            snapshot: trackingData.snapshots.xFactor?.img || null,
            time: trackingData.snapshots.xFactor?.time || '0:00',
            flawTitle: 'Flat Rotation',
            flawText: `Maximum hip-shoulder separation was ${Math.round(trackingData.maxXFactor)}°. Kinetic energy leak: Your torso is rotating as a single block.`,
            drillTitle: 'The "Dynamic X" Drill',
            drillText: 'Sit on a chair to lock your hips forward. Holding a racket, turn your shoulders as far back as possible while keeping your knees facing forward. This isolated rotation trains the "stretch" needed for a high-powered serve.'
        }
    ];

    checks.forEach(check => {
        const statusClass = check.isFlaw ? '' : 'success-item';
        const borderColor = check.isFlaw ? 'var(--danger)' : 'var(--success)';
        const background = check.isFlaw ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)';

        flawList.innerHTML += `
            <li class="flaw-item" style="background: ${background}; border-left: 4px solid ${borderColor}; border-color: ${check.isFlaw ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'};">
                ${check.snapshot ? `<img src="${check.snapshot}" class="flaw-snapshot" alt="${check.name}">` : ''}
                <div class="flaw-content">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <strong>Check ${check.id}: ${check.name}</strong>
                        <span class="status-badge" style="background: ${borderColor}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold;">
                            ${check.isFlaw ? 'FLAW DETECTED' : 'PASSED'}
                        </span>
                    </div>
                    <span class="timestamp-label">Detected at ${check.time}</span>
                    <div style="margin: 0.5rem 0; font-size: 1.1rem; font-weight: bold; color: white;">
                        Value: ${check.value}${check.unit} <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-secondary); margin-left: 10px;">(Target: ${check.target})</span>
                    </div>
                    ${check.isFlaw ? `<span>${check.flawText}</span>` : `<span style="color: #a7f3d0;">Perfect execution. Your movement is within the elite range for this checkpoint.</span>`}
                </div>
            </li>`;

        if (check.isFlaw) {
            flawsFound++;
            trainingPlan.innerHTML += `
                <div class="training-step">
                    <div class="step-number">${stepCount++}</div>
                    <h4>${check.drillTitle}</h4>
                    <p>${check.drillText}</p>
                </div>`;
        }
    });

    // Baseline good technique if no major flaws
    if (flawsFound === 0) {
        scoreBadge.innerText = 'Elite Mechanics Detected';
        scoreBadge.className = 'score-badge success';
        flawList.innerHTML = `
            <li class="flaw-item success" style="background: rgba(16, 185, 129, 0.1); border-color: var(--success);">
                <strong>Perfect Technical Score</strong>
                <span>All 5 biomechanical checkpoints are within the ${selectedLevel.toUpperCase()} benchmark range.</span>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem; line-height: 1.6;">
                    <p style="margin-bottom: 0.4rem;"><span style="color: #58a6ff; margin-right: 5px;">▶</span> <strong>Leg Drive</strong>: Deep knee bend (Check 3) successfully offloads stress from your rotator cuff.</p>
                    <p style="margin-bottom: 0.4rem;"><span style="color: #58a6ff; margin-right: 5px;">▶</span> <strong>Elastic Storage</strong>: High elbow & trophy position (Checks 1-2) maximizes chest-stretch energy.</p>
                    <p style="margin-bottom: 0.4rem;"><span style="color: #58a6ff; margin-right: 5px;">▶</span> <strong>Power Runway</strong>: Deep racket drop (Check 4) creates maximum acceleration distance.</p>
                    <p><span style="color: #58a6ff; margin-right: 5px;">▶</span> <strong>The Snap</strong>: High-velocity internal rotation (Check 5) ensures peak compression at impact.</p>
                </div>
            </li>`;

        trainingPlan.innerHTML = `
            <div class="training-step">
                <div class="step-number">1</div>
                <h4>Accuracy & Target Practice</h4>
                <p>Mechanics are elite. Focus on hitting the "T" and "Wide" corners 8/10 times. Work on disguise (same toss/motion for all placements).</p>
            </div>
            <div class="training-step">
                <div class="step-number">2</div>
                <h4>Second Serve Kick/Slice</h4>
                <p>Translate this optimized chain into spin serves. Maintain the same leg drive but adjust the contact point and pronation angle for heavy rotation.</p>
            </div>`;
    } else if (flawsFound === 1) {
        scoreBadge.innerText = 'Minor Adjustments Needed';
        scoreBadge.className = 'score-badge warning';
    } else {
        scoreBadge.innerText = 'Critical Flaws Detected';
        scoreBadge.className = 'score-badge';
    }

    loadingStatus.innerText = 'Analysis Complete.';
    loadingStatus.style.color = 'var(--success)';
    container.style.display = 'block';

    // Add Visual Gallery for Single Analysis
    generateVisualGallery(trackingDataA, null, false);

    // Update Velocity Chart
    updateVelocityChart(trackingDataA);

    setTimeout(() => container.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

function generateComparisonReport() {
    const container = document.getElementById('actionPlanContainer');
    const flawList = document.getElementById('flawList');
    const trainingPlan = document.getElementById('trainingPlan');
    const scoreBadge = document.getElementById('overallScore');
    const assessmentLevel = document.getElementById('assessmentLevel');

    // Incompatible Check (Apple to Orange)
    // Relaxed check: as long as we have frames and a decent shoulder height
    const isAServe = trackingDataA.maxShoulder > 50 && trackingDataA.framesProcessed > 0;
    const isBServe = trackingDataB.maxShoulder > 50 && trackingDataB.framesProcessed > 0;

    // Use peakWristY-based estimation if impactTime is null
    if (isAServe && !trackingDataA.impactTime) trackingDataA.impactTime = trackingDataA.maxShoulderTime + 0.5;
    if (isBServe && !trackingDataB.impactTime) trackingDataB.impactTime = trackingDataB.maxShoulderTime + 0.5;

    if (trackingDataA.framesProcessed === 0 || trackingDataB.framesProcessed === 0) {
        console.log("Comparison Blocked - Zero Frames Metadata:", {
            A: { frames: trackingDataA.history.length },
            B: { frames: trackingDataB.history.length }
        });
        loadingStatus.innerText = 'Error: Pose data missing for one or both videos. Please ensure they play through.';
        loadingStatus.style.color = 'var(--danger)';
        return;
    }

    assessmentLevel.innerText = `COMPARISON: SERVE A VS SERVE B (${selectedLevel.toUpperCase()})`;
    scoreBadge.innerText = 'Comparison Analysis';
    scoreBadge.className = 'score-badge warning';

    flawList.innerHTML = '';
    trainingPlan.innerHTML = '';

    const diffs = [
        { label: 'Shoulder Abduction', a: trackingDataA.maxShoulder, b: trackingDataB.maxShoulder, unit: '°' },
        { label: 'Elbow Flexion', a: Math.round(trackingDataA.trophyFlexion || 180), b: Math.round(trackingDataB.trophyFlexion || 180), unit: '°' },
        { label: 'Knee Bend', a: Math.round(trackingDataA.minKnee), b: Math.round(trackingDataB.minKnee), unit: '°' },
        { label: 'Racket Drop', a: Math.round(trackingDataA.minRacketDrop), b: Math.round(trackingDataB.minRacketDrop), unit: '°' },
        { label: 'X-Factor', a: Math.round(trackingDataA.maxXFactor), b: Math.round(trackingDataB.maxXFactor), unit: '°' },
        { label: 'Pronation Speed', a: Math.round(trackingDataA.maxPronation), b: Math.round(trackingDataB.maxPronation), unit: '%' },
        { label: 'Vertical Jump', a: trackingDataA.maxJump.toFixed(1), b: trackingDataB.maxJump.toFixed(1), unit: ' in' },
        { label: 'Court Drift', a: trackingDataA.maxDrift.toFixed(1), b: trackingDataB.maxDrift.toFixed(1), unit: ' ft' }
    ];

    diffs.forEach(d => {
        const delta = d.b - d.a;
        const color = Math.abs(delta) < 10 ? 'var(--success)' : 'var(--warning)';
        flawList.innerHTML += `
            <li class="flaw-item" style="border-left: 4px solid ${color};">
                <strong>${d.label}</strong>
                <span>Serve A (Pro): ${d.a}${d.unit} | Serve B (User): ${d.b}${d.unit}</span>
                <p style="margin-top: 5px; font-size: 0.8rem;">Difference: ${delta > 0 ? '+' : ''}${delta}${d.unit}</p>
            </li>`;
    });

    trainingPlan.innerHTML = `
        <div class="training-step">
            <div class="step-number">!</div>
            <h4>Optimization Focus</h4>
            <p>To match Serve B's efficiency, focus on closing the delta in ${diffs.reduce((a, b) => Math.abs(a.b - a.a) > Math.abs(b.b - b.a) ? a : b).label}.</p>
        </div>`;

    // Add Visual Gallery for Comparison
    generateVisualGallery(trackingDataA, trackingDataB, true);

    // Update Velocity Chart (show both if A and B exist)
    updateVelocityChart(trackingDataA, trackingDataB);

    // Show Sync button if we have impact times for both
    if (trackingDataA.impactTime && trackingDataB.impactTime) {
        syncBtn.style.display = 'flex';
        syncBtn.style.alignItems = 'center';
        syncBtn.style.gap = '8px';
    }

    loadingStatus.innerText = 'Comparison Complete.';
    loadingStatus.style.color = 'var(--success)';
    container.style.display = 'block';
    setTimeout(() => container.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

function generateVisualGallery(dataA, dataB, isComparison) {
    const container = document.getElementById('actionPlanContainer');
    let galleryHTML = `
        <div class="visual-gallery">
            <h3>${isComparison ? 'Side-by-Side Visuals' : 'Biomechanical Snapshots'}</h3>
            <div class="gallery-grid">
    `;

    const labels = {
        trophy: {
            title: 'Peak Trophy Position',
            desc: 'The point of maximum coil: tossing arm is high, hitting elbow is back, and body is coiled for power.'
        },
        kneeBend: {
            title: 'Maximum Knee Bend',
            desc: 'The primary power source: legs are loaded at their deepest point to initiate the upward explosion.'
        },
        racketDrop: {
            title: 'Deepest Racket Drop',
            desc: 'The "back scratch" position: hitting wrist is low behind the back, indicating maximum stretch-shortening cycle.'
        },
        impact: {
            title: 'Contact Point (Impact)',
            desc: 'The apex of the serve: the arm and racket reach full extension as the strings meet the ball.'
        },
        finish: {
            title: 'Follow Through / Finish',
            desc: 'Deceleration and balance: the hitting arm sweeps across the body as the weight transfers forward.'
        },
        xFactor: {
            title: 'X-Factor Separation',
            desc: 'The "Stretch": Maximum rotation difference between hips and shoulders, creating elastic energy for the explosion.'
        }
    };

    Object.keys(labels).forEach(key => {
        const snapA = dataA.snapshots[key];
        const snapB = isComparison ? (dataB ? dataB.snapshots[key] : null) : null;

        const imgA = (snapA && snapA.img) ? snapA.img : '';
        const imgB = (snapB && snapB.img) ? snapB.img : '';
        const timeA = (snapA && snapA.time && snapA.time !== 'null') ? snapA.time : '--';
        const timeB = (snapB && snapB.time && snapB.time !== 'null') ? snapB.time : '--';

        if (true) { // Always show sections for consistency
            galleryHTML += `
                <div class="gallery-item" style="${(isComparison && (!imgA || !imgB)) ? 'opacity: 0.8;' : ''}">
                    <h4>${labels[key].title}</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">${labels[key].desc}</p>
                    <div class="comparison-row ${!isComparison ? 'single-view' : ''}">
                        <div class="snapshot">
                            ${imgA ? `<img src="${imgA}" alt="Serve A ${key}">` : `<div style="height:200px; background:#121826; border-radius:8px; display:flex; align-items:center; justify-content:center;">Awaiting Point A</div>`}
                            <div class="snap-label">${isComparison ? 'Serve A (Pro)' : 'Biomechanical Point'} (${timeA}s)</div>
                        </div>
                        ${isComparison ? `
                        <div class="snapshot">
                            ${imgB ? `<img src="${imgB}" alt="Serve B ${key}">` : `<div style="height:200px; background:#121826; border-radius:8px; display:flex; align-items:center; justify-content:center;">Awaiting Point B</div>`}
                            <div class="snap-label">Serve B (User) (${timeB}s)</div>
                        </div>` : ''}
                    </div>
                </div>
            `;
        }
    });

    galleryHTML += `</div></div>`;
    const existingGallery = container.querySelector('.visual-gallery');
    if (existingGallery) existingGallery.remove();
    container.insertAdjacentHTML('beforeend', galleryHTML);
}

function updateVelocityChart(dataA, dataB = null) {
    if (!velocityChartCanvas) return;

    const ctx = velocityChartCanvas.getContext('2d');
    if (velocityChart) velocityChart.destroy();

    const datasets = [{
        label: 'Serve A (Pro) Velocity',
        data: dataA.velocityHistory.map(h => ({ x: h.time, y: h.v })),
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88, 166, 255, 0.1)',
        tension: 0.4,
        fill: true,
        pointRadius: 0
    }];

    if (dataB) {
        datasets.push({
            label: 'Serve B (User) Velocity',
            data: dataB.velocityHistory.map(h => ({ x: h.time, y: h.v })),
            borderColor: '#ff6a33',
            backgroundColor: 'rgba(255, 106, 51, 0.1)',
            tension: 0.4,
            fill: true,
            pointRadius: 0
        });
    }

    velocityChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Time (seconds)', color: '#8b949e' },
                    grid: { color: 'rgba(250,250,250,0.05)' },
                    ticks: { color: '#8b949e' }
                },
                y: {
                    title: { display: true, text: 'Wrist Speed', color: '#8b949e' },
                    grid: { color: 'rgba(250,250,250,0.05)' },
                    ticks: { color: '#8b949e' }
                }
            },
            plugins: {
                legend: { labels: { color: '#c9d1d9' } },
                tooltip: { mode: 'index', intersect: false }
            }
        }
    });
}

function syncVideos() {
    if (!comparisonMode || !isVideoSetup || !isVideoSetupB) return;
    if (!trackingDataA.impactTime || !trackingDataB.impactTime) {
        console.log("Cannot sync - impactTime not detected for both yet.");
        return;
    }

    // Aligns Video B to the same "relative" moment as Video A
    const offset = trackingDataB.impactTime - trackingDataA.impactTime;

    // We adjust videoB player to match videoA's current "stage" of the serve
    videoElementB.currentTime = videoElement.currentTime + offset;
}

let isPoseProcessing = false;

async function processPoseFrame(video, slot) {
    const poseInst = slot === 'A' ? poseA : poseB;
    return new Promise(resolve => {
        if (slot === 'A') poseResolveA = resolve;
        else poseResolveB = resolve;

        poseInst.send({ image: video });
        // Max timeout to prevent hang if pose fails
        // 3000ms to handle dual mode + high-res slow-mo videos
        setTimeout(() => {
            if (slot === 'A' && poseResolveA) { poseResolveA(); poseResolveA = null; }
            if (slot === 'B' && poseResolveB) { poseResolveB(); poseResolveB = null; }
        }, 3000);
    });
}

// Video processing loop — FRAME-BY-FRAME for deterministic results
// The video is paused; we process each frame, then seek forward by a fixed step.
// This ensures every run analyzes the exact same frames at the same timestamps.
const FRAME_STEP = 1 / 30; // Analyze at 30fps (every ~0.033s of video) for more granular capture
let isAnalyzing = false;

// Helper: seek video and wait for frame to be decoded & painted
async function seekAndWait(videoEl, time) {
    videoEl.currentTime = time;
    await new Promise(resolve => {
        const onSeeked = () => {
            videoEl.removeEventListener('seeked', onSeeked);
            // Double requestAnimationFrame ensures the browser has decoded + painted the frame
            requestAnimationFrame(() => requestAnimationFrame(resolve));
        };
        videoEl.addEventListener('seeked', onSeeked);
        // Fallback if seeked doesn't fire (e.g., already at that position)
        setTimeout(() => {
            videoEl.removeEventListener('seeked', onSeeked);
            requestAnimationFrame(() => requestAnimationFrame(resolve));
        }, 500);
    });
}

async function processVideo() {
    if (isAnalyzing) return; // Prevent double-start
    isAnalyzing = true;

    // Pause immediately — we control playback via seeking
    videoElement.pause();
    if (comparisonMode && isVideoSetupB) videoElementB.pause();

    // Start from beginning
    let currentPos = 0;
    const duration = videoElement.duration;

    if (canvasElement.width !== videoElement.videoWidth) {
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
    }
    if (comparisonMode && videoElementB.videoWidth > 0 && canvasElementB.width !== videoElementB.videoWidth) {
        canvasElementB.width = videoElementB.videoWidth;
        canvasElementB.height = videoElementB.videoHeight;
    }

    // Reset tracking for fresh analysis
    resetTracking('A');
    if (comparisonMode) resetTracking('B');

    loadingStatus.innerText = 'Analyzing...';

    while (currentPos < duration) {
        // Seek and wait for the frame to be fully decoded
        await seekAndWait(videoElement, currentPos);

        // Update progress
        const percent = (currentPos / duration) * 100;
        progressBar.value = percent;
        updateTimeDisplay();
        loadingStatus.innerText = `Analyzing... ${percent.toFixed(0)}%`;

        // PRE-CAPTURE: Draw the decoded frame to a canvas
        const preCapA = document.createElement('canvas');
        preCapA.width = videoElement.videoWidth / 2;
        preCapA.height = videoElement.videoHeight / 2;
        preCapA.getContext('2d').drawImage(videoElement, 0, 0, preCapA.width, preCapA.height);
        lastCapturedFrameA = preCapA;
        lastCapturedTimeA = currentPos;

        // Create full-resolution canvas for MediaPipe (canvas is guaranteed to have pixel data)
        const fullCapA = document.createElement('canvas');
        fullCapA.width = videoElement.videoWidth;
        fullCapA.height = videoElement.videoHeight;
        fullCapA.getContext('2d').drawImage(videoElement, 0, 0);

        // Process this frame through MediaPipe (send canvas, not video element)
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
        } catch (err) {
            console.error("Pose processing error at", currentPos.toFixed(2), ":", err);
        }

        // Advance to next frame
        currentPos += FRAME_STEP;
    }

    // Analysis complete
    progressBar.value = 100;
    loadingStatus.innerText = 'Analysis Complete!';
    isAnalyzing = false;

    // Generate report
    generateActionPlan();
    updateVelocityChart(trackingDataA, comparisonMode ? trackingDataB : null);
    generateVisualGallery(trackingDataA, comparisonMode ? trackingDataB : null, comparisonMode);

    playBtn.innerText = 'Re-Analyze';
    playBtn.disabled = false;
}

async function runServerAnalysis() {
    if (isAnalyzingServer) return;
    isAnalyzingServer = true;
    loadingStatus.innerHTML = '<span class="status-dot blur" style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #f1e05a; margin-right: 8px;"></span> Analyzing on Server with YOLO...';

    playBtn.innerText = 'Analyzing...';
    playBtn.disabled = true;

    try {
        const formData = new FormData();
        const videoFileA = videoUpload.files[0];
        if (!videoFileA) throw new Error("No video selected for Serve A");
        formData.append('video', videoFileA);

        console.log("Sending Serve A to server for YOLO analysis...");
        const response = await fetch(`${serverUrl}/analyze`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(`Server analysis failed: ${response.statusText}`);
        const results = await response.json();

        console.log("Server Results (A):", results);
        mapPythonResultsToDashboard(results, 'A');

        if (comparisonMode && videoUploadB.files[0]) {
            loadingStatus.innerHTML = '<span class="status-dot blur" style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #f1e05a; margin-right: 8px;"></span> Analyzing comparison video...';
            const formDataB = new FormData();
            formDataB.append('video', videoUploadB.files[0]);
            const responseB = await fetch(`${serverUrl}/analyze`, {
                method: 'POST',
                body: formDataB
            });
            if (responseB.ok) {
                const resultsB = await responseB.json();
                console.log("Server Results (B):", resultsB);
                mapPythonResultsToDashboard(resultsB, 'B');
            }
        }

        loadingStatus.innerText = 'Server Analysis Complete!';
        generateActionPlan();
        generateVisualGallery(trackingDataA, comparisonMode ? trackingDataB : null, comparisonMode);
        updateVelocityChart(trackingDataA, comparisonMode ? trackingDataB : null);
    } catch (err) {
        console.error("Server analysis exception:", err);
        loadingStatus.innerText = `Error: ${err.message}. Switching back to Browser AI.`;
        useYoloMode = false;
        if (engineToggle) engineToggle.checked = false;
        if (engineLabel) engineLabel.innerText = 'Engine: Browser AI';
        await processVideo();
    } finally {
        isAnalyzingServer = false;
        playBtn.innerText = 'Re-Analyze';
        playBtn.disabled = false;
    }
}

function mapPythonResultsToDashboard(results, slot) {
    const data = slot === 'A' ? trackingDataA : trackingDataB;

    // Map snapshots
    if (results.snapshots) {
        for (let key in results.snapshots) {
            const snap = results.snapshots[key];
            if (data.snapshots[key]) {
                data.snapshots[key] = {
                    img: snap.img,
                    time: snap.time
                };
            }
        }
    }

    // Map metrics for UI Gauges
    const m = results.metrics;
    if (m.shoulderAbduction) { data.maxShoulder = m.shoulderAbduction.value; data.maxShoulderTime = m.shoulderAbduction.time; }
    if (m.elbowFlexion) { data.minElbow = m.elbowFlexion.value; data.minElbowTime = m.elbowFlexion.time; }
    if (m.kneeBend) { data.minKnee = m.kneeBend.value; data.minKneeTime = m.kneeBend.time; }
    if (m.racketDrop) { data.minRacketDrop = m.racketDrop.value; data.minRacketDropTime = m.racketDrop.time; }
    if (m.xFactor) { data.maxXFactor = m.xFactor.value; data.maxXFactorTime = m.xFactor.time; }

    // Map impact time and general state
    data.impactTime = results.phases?.impact_time || null;
    data.isServeStarted = true;
    data.framesProcessed = results.total_frames || 100;
    data.impactDetected = !!data.impactTime;

    // Trigger UI updates
    updateAllGauges(slot);
}

function updateTimeDisplay() {
    const curr = formatTime(videoElement.currentTime);
    const total = formatTime(videoElement.duration || 0);
    timeDisplay.innerText = `${curr} / ${total}`;
}

function formatTime(seconds) {
    if (isNaN(seconds)) seconds = 0;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// Event Listeners
videoUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        resetTracking('A');
        const url = URL.createObjectURL(file);
        videoElement.src = url;
        uploadArea.style.display = 'none';
        playerWrapper.style.display = 'flex';
        isVideoSetup = true;
        if (comparisonMode) uploadAreaB.style.display = 'flex';
        playbackControls.style.display = 'flex';
        actionPlanContainer.style.display = 'none';
    }
});

videoUploadB.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        resetTracking('B');
        const url = URL.createObjectURL(file);
        videoElementB.src = url;
        uploadAreaB.style.display = 'none';
        playerWrapperB.style.display = 'flex';
        isVideoSetupB = true;
        if (comparisonMode) actionPlanContainer.style.display = 'none';
    }
});

videoElement.addEventListener('loadeddata', async () => {
    updateTimeDisplay();
    while (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
        await new Promise(r => setTimeout(r, 50));
    }
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    // No initial processPoseFrame — frame-by-frame analysis handles everything
});

videoElementB.addEventListener('loadeddata', async () => {
    while (videoElementB.videoWidth === 0 || videoElementB.videoHeight === 0) {
        await new Promise(r => setTimeout(r, 50));
    }
    canvasElementB.width = videoElementB.videoWidth;
    canvasElementB.height = videoElementB.videoHeight;
    canvasCtxB.clearRect(0, 0, canvasElementB.width, canvasElementB.height);
    // No initial processPoseFrame — frame-by-frame analysis handles everything
});

playBtn.addEventListener('click', () => {
    if (!isVideoSetup) return;

    if (!isAnalyzing) {
        playBtn.innerText = 'Analyzing...';
        playBtn.disabled = true;
        processVideo().then(() => {
            playBtn.innerText = 'Re-Analyze';
            playBtn.disabled = false;
        });
    }
});

videoElement.addEventListener('ended', () => {
    // No-op: frame-by-frame loop handles completion
});

progressBar.addEventListener('input', (e) => {
    if (!isVideoSetup || !videoElement.duration || isAnalyzing) return;
    const time = (e.target.value / 100) * videoElement.duration;
    videoElement.currentTime = time;
    updateTimeDisplay();

    // Process single frame if paused (only outside analysis)
    if (videoElement.paused) {
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        clearTimeout(window.scrubTimeout);
        window.scrubTimeout = setTimeout(async () => {
            try {
                await processPoseFrame(videoElement, 'A');
            } catch (err) { }
        }, 150);
    }
});

syncBtn.addEventListener('click', () => {
    syncVideos();
    // Briefly highlight success
    syncBtn.style.borderColor = 'var(--success)';
    setTimeout(() => syncBtn.style.borderColor = 'rgba(88, 166, 255, 0.3)', 1000);
});

changeVideoBtnA.addEventListener('click', () => {
    resetTracking('A');
    videoElement.pause();
    videoElement.src = "";
    isVideoSetup = false;
    playerWrapper.style.display = 'none';
    uploadArea.style.display = 'flex';
    actionPlanContainer.style.display = 'none';
    playbackControls.style.display = 'none';
    playBtn.innerText = 'Play';
    loadingStatus.innerText = 'Analyze another serve...';
    loadingStatus.style.color = 'var(--text-secondary)';
});

changeVideoBtnB.addEventListener('click', () => {
    resetTracking('B');
    videoElementB.pause();
    videoElementB.src = "";
    isVideoSetupB = false;
    playerWrapperB.style.display = 'none';
    uploadAreaB.style.display = 'flex';
});

// Start initialization
initPose();
updateBenchmarkLabels();
