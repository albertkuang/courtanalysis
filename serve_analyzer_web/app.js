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

let selectedLevel = 'pro';

const BENCHMARKS = {
    pro: {
        shoulder: { min: 90, max: 110, label: "90° - 110°" },
        elbow: { min: 70, max: 100, label: "70° - 100°" },
        knee: { min: 110, max: 140, label: "110° - 140°" },
        racketDrop: { min: 0, max: 105, label: "< 100°" },
        pronation: { threshold: 60, label: "High Velocity Flick" }
    },
    junior: {
        shoulder: { min: 85, max: 115, label: "85° - 115°" },
        elbow: { min: 65, max: 110, label: "65° - 110°" },
        knee: { min: 100, max: 150, label: "100° - 150°" },
        racketDrop: { min: 0, max: 115, label: "< 110°" },
        pronation: { threshold: 45, label: "Stable Snap" }
    }
};

function updateBenchmarkLabels() {
    const config = BENCHMARKS[selectedLevel];
    document.getElementById('target-shoulder').innerText = config.shoulder.label;
    document.getElementById('target-elbow').innerText = config.elbow.label;
    document.getElementById('target-knee').innerText = config.knee.label;
    document.getElementById('target-racketDrop').innerText = config.racketDrop.label;
    document.getElementById('target-pronation').innerText = config.pronation.label;
}

levelSelect.addEventListener('change', (e) => {
    selectedLevel = e.target.value;
    updateBenchmarkLabels();
    if (isVideoSetup) {
        // Recalculate if already processed? Or just update labels.
        // For now, let's just update labels. The next play/results will use new level.
    }
});

let pose;
let isVideoSetup = false;
let isVideoSetupB = false;
let animationId = null;
let comparisonMode = false;
let activeVideo = 'A'; // Which video is currently being processed by pose

// Multi-video Tracking State
let trackingDataA = {
    maxShoulder: 0, maxShoulderTime: 0,
    minElbow: 180, minElbowTime: 0,
    minKnee: 180, minKneeTime: 0,
    minRacketDrop: 180, minRacketDropTime: 0,
    maxPronation: 0, maxPronationTime: 0,
    impactTime: null,
    isServeStarted: false,
    history: [],
    snapshots: { trophy: { img: null, time: null }, racketDrop: { img: null, time: null }, impact: { img: null, time: null } },
    impactDetected: false,
    tossArmPeakY: null,
    peakWristY: null,
    peakWristYTime: 0,
    framesProcessed: 0,
    descendCounter: 0,
    isDescendingFromPeak: false,
    lastWristPos: null,
    reachedTrophy: false
};

let trackingDataB = {
    maxShoulder: 0, maxShoulderTime: 0,
    minElbow: 180, minElbowTime: 0,
    minKnee: 180, minKneeTime: 0,
    minRacketDrop: 180, minRacketDropTime: 0,
    maxPronation: 0, maxPronationTime: 0,
    impactTime: null,
    isServeStarted: false,
    history: [],
    snapshots: { trophy: { img: null, time: null }, racketDrop: { img: null, time: null }, impact: { img: null, time: null } },
    impactDetected: false,
    tossArmPeakY: null,
    peakWristY: null,
    peakWristYTime: 0,
    framesProcessed: 0,
    descendCounter: 0,
    isDescendingFromPeak: false,
    lastWristPos: null,
    reachedTrophy: false
};

let trackingData = trackingDataA; // Default to A for backward compatibility in functions

function captureFrame(video, category) {
    const data = activeVideo === 'A' ? trackingDataA : trackingDataB;
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = video.videoWidth / 2; // Reduced size for performance
    offscreenCanvas.height = video.videoHeight / 2;
    const ctx = offscreenCanvas.getContext('2d');

    // Draw the video frame
    ctx.drawImage(video, 0, 0, offscreenCanvas.width, offscreenCanvas.height);

    // Also draw the skeleton if we have current results
    // Actually, capturing just the video is often cleaner, 
    // but the user might want to see the AI lines. 
    // Let's capture with lines if we are inside onResults.
    const mainCanvas = activeVideo === 'A' ? canvasElement : canvasElementB;
    ctx.drawImage(mainCanvas, 0, 0, offscreenCanvas.width, offscreenCanvas.height);

    data.snapshots[category] = {
        img: offscreenCanvas.toDataURL('image/jpeg', 0.7),
        time: video.currentTime.toFixed(2)
    };
}

// Initialize MediaPipe Pose
async function initPose() {
    pose = new Pose({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
    });

    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });

    pose.onResults(onResults);

    // Test initialization
    await pose.initialize();
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

    if (isPronation) {
        element.innerText = `${angle}%`;
        fillElement.style.width = `${angle}%`;
        fillElement.style.backgroundColor = angle >= config.threshold ? 'var(--success)' : 'var(--warning)';
        return;
    }

    element.innerText = `${angle}°`;
    const percent = Math.min(100, Math.max(0, (angle / 180) * 100));
    fillElement.style.width = `${percent}%`;

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
    const data = mode === 'A' ? trackingDataA : trackingDataB;
    Object.assign(data, {
        maxShoulder: 0, maxShoulderTime: 0,
        minElbow: 180, minElbowTime: 0,
        minKnee: 180, minKneeTime: 0,
        minRacketDrop: 180, minRacketDropTime: 0,
        maxPronation: 0, maxPronationTime: 0,
        impactTime: null,
        isServeStarted: false,
        history: [],
        impactDetected: false,
        tossArmPeakY: null,
        peakWristY: null,
        peakWristYTime: 0,
        framesProcessed: 0,
        descendCounter: 0,
        isDescendingFromPeak: false,
        lastWristPos: null,
        reachedTrophy: false,
        snapshots: {
            trophy: { img: null, time: null },
            kneeBend: { img: null, time: null },
            racketDrop: { img: null, time: null },
            impact: { img: null, time: null },
            finish: { img: null, time: null }
        }
    });

    if (mode === 'A') {
        loadingStatus.innerText = 'AI Ready. Upload video below.';
        document.getElementById('actionPlanContainer').style.display = 'none';
        document.getElementById('flawList').innerHTML = '';
        document.getElementById('trainingPlan').innerHTML = '';
    }
}

// Handle pose results
function onResults(results) {
    const video = activeVideo === 'A' ? videoElement : videoElementB;
    const canvas = activeVideo === 'A' ? canvasElement : canvasElementB;
    const ctx = activeVideo === 'A' ? canvasCtx : canvasCtxB;
    const data = activeVideo === 'A' ? trackingDataA : trackingDataB;

    if (!video.videoWidth) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (results.poseLandmarks) {
        drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS,
            { color: activeVideo === 'A' ? 'rgba(88, 166, 255, 0.6)' : 'rgba(255, 106, 51, 0.6)', lineWidth: 4 });
        drawLandmarks(ctx, results.poseLandmarks,
            { color: '#0d1117', fillColor: activeVideo === 'A' ? '#58a6ff' : '#ff6a33', lineWidth: 2, radius: 4 });

        const landmarks = results.poseWorldLandmarks || results.poseLandmarks;
        const rawLandmarks = results.poseLandmarks;

        const visThreshold = 0.7;
        const shoulderVis = rawLandmarks[12].visibility > visThreshold && rawLandmarks[14].visibility > visThreshold && rawLandmarks[24].visibility > visThreshold;
        const elbowVis = rawLandmarks[14].visibility > visThreshold && rawLandmarks[16].visibility > visThreshold && rawLandmarks[12].visibility > visThreshold;
        const kneeVis = rawLandmarks[26].visibility > visThreshold && rawLandmarks[28].visibility > visThreshold && rawLandmarks[24].visibility > visThreshold;
        const tossingArmVis = rawLandmarks[11].visibility > visThreshold && rawLandmarks[13].visibility > visThreshold && rawLandmarks[15].visibility > visThreshold;


        const isServePhase = rawLandmarks[16].y < (rawLandmarks[12].y + 0.1);

        const currentWristY = rawLandmarks[16].y;
        const currentTime = video.currentTime;
        const isHandUp = rawLandmarks[16].y < rawLandmarks[0].y; // Wrist above nose

        if (isHandUp) {
            if (!data.peakWristY || currentWristY < data.peakWristY) {
                data.peakWristY = currentWristY;
                data.peakWristYTime = currentTime;
                data.isDescendingFromPeak = false;

                // Capture the frame at every new peak reached. 
                // Once impactDetected is true, we stop updating this.
                if (!data.impactDetected) {
                    captureFrame(video, 'impact');
                }
            } else if (currentWristY > data.peakWristY + 0.015 && !data.isDescendingFromPeak) {
                // Confirm it's a real drop, not a flicker
                if (currentWristY > data.peakWristY + 0.04 || (currentTime - data.peakWristYTime > 0.04)) {
                    if (!data.impactDetected) {
                        data.impactTime = data.peakWristYTime;
                        data.impactDetected = true;
                        // The frame at the apex (data.peakWristYTime) is already captured
                    }
                    data.isDescendingFromPeak = true;
                }
            }
        }


        const shoulderAng = shoulderVis ? calculateAngle3D(landmarks[24], landmarks[12], landmarks[14]) : null;
        const elbowAng = elbowVis ? calculateAngle3D(landmarks[12], landmarks[14], landmarks[16]) : null;
        const kneeAng = kneeVis ? calculateAngle3D(landmarks[24], landmarks[26], landmarks[28]) : null;
        // Angle of the tossing arm (left shoulder, left elbow, left wrist) for trophy position
        const tossingArmAngle = tossingArmVis ? calculateAngle3D(landmarks[23], landmarks[11], landmarks[13]) : null;


        let pronationIndex = 0;
        if (data.lastWristPos && isServePhase) {
            const dx = landmarks[16].x - data.lastWristPos.x;
            const dy = landmarks[16].y - data.lastWristPos.y;
            const dz = landmarks[16].z - data.lastWristPos.z;
            const velocity = Math.sqrt(dx * dx + dy * dy + dz * dz) * 1000;
            pronationIndex = Math.min(100, Math.round(velocity));
        }
        data.lastWristPos = { x: landmarks[16].x, y: landmarks[16].y, z: landmarks[16].z };

        // Save History for Comparison
        data.history.push({
            time: video.currentTime,
            shoulder: shoulderAng,
            elbow: elbowAng,
            knee: kneeAng,
            pronation: pronationIndex,
            isDescending: data.isDescendingFromPeak
        });

        updateMetricUI(shoulderEl, shoulderFill, shoulderAng, 'shoulder');
        updateMetricUI(elbowEl, elbowFill, elbowAng, 'elbow');
        updateMetricUI(kneeEl, kneeFill, kneeAng, 'knee');
        updateMetricUI(racketDropEl, racketDropFill, elbowAng, 'racketDrop');
        updateMetricUI(pronationEl, pronationFill, pronationIndex, 'pronation');

        // Tracking peaks (only before impact)
        if (!data.impactDetected) {
            if (shoulderAng > data.maxShoulder) {
                data.maxShoulder = shoulderAng;
                data.maxShoulderTime = video.currentTime;
            }
            // 1. Trophy Capture (when tossing arm is highest AND hitting arm is loaded)
            if (tossingArmVis && shoulderAng > 60 && (data.tossArmPeakY === null || rawLandmarks[15].y < data.tossArmPeakY)) {
                data.tossArmPeakY = rawLandmarks[15].y;
                captureFrame(video, 'trophy');
                data.reachedTrophy = true;
            }
            if (elbowAng < data.minElbow) { data.minElbow = elbowAng; data.minElbowTime = video.currentTime; }
            if (kneeAng < data.minKnee) {
                data.minKnee = kneeAng;
                data.minKneeTime = video.currentTime;
                captureFrame(video, 'kneeBend');
            }

            // 2. Racket Drop Capture (Deepest elbow flexion AFTER trophy phase starts)
            // Hitting elbow must be above shoulder (shoulderAng > 80)
            if (data.reachedTrophy && shoulderAng > 80 && elbowAng < data.minRacketDrop) {
                data.minRacketDrop = elbowAng;
                data.minRacketDropTime = video.currentTime;
                captureFrame(video, 'racketDrop');
            }
        }

        // 3. Follow Through / Finish (Approx 0.5s after impact)
        if (data.impactDetected && !data.snapshots.finish.img && (currentTime > data.impactTime + 0.5)) {
            captureFrame(video, 'finish');
        }
        if (isServePhase && pronationIndex > data.maxPronation) { data.maxPronation = pronationIndex; data.maxPronationTime = video.currentTime; }
        data.framesProcessed++;
    }
    ctx.restore();
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

    // Check Elbow
    if (trackingData.minElbow < config.elbow.min || trackingData.minElbow > config.elbow.max) {
        flawsFound++;
        const timeStr = formatTime(trackingData.minElbowTime);
        flawList.innerHTML += `
            <li class="flaw-item">
                <strong>Check 2: Elbow Flexion (Trophy Position)</strong>
                <span class="timestamp-label">Detected at ${timeStr}</span>
                <span>Flexion reached ${trackingData.minElbow}°. (Target: ${config.elbow.label}). This "Trophy Pose Leak" causes a severe power disconnect during the loading phase.</span>
            </li>`;

        trainingPlan.innerHTML += `
            <div class="training-step">
                <div class="step-number">${stepCount++}</div>
                <h4>The Waiter's Tray Drill</h4>
                <p>Hold the racket in the trophy position. Place a spare ball in the throat of the racket. If your elbow drops too low, the ball will fall out. Perform 20 dry swings focusing entirely on holding the angle before accelerating.</p>
            </div>`;
    }

    // Check Shoulder
    // If the MAX abduction reached during the load was less than benchmarks, it's a collapsed shoulder
    if (trackingData.maxShoulder < config.shoulder.min) {
        flawsFound++;
        const timeStr = formatTime(trackingData.maxShoulderTime);
        flawList.innerHTML += `
            <li class="flaw-item">
                <strong>Check 1: Shoulder Abduction (Elbow Height)</strong>
                <span class="timestamp-label">Detected at ${timeStr}</span>
                <span>Shoulder abduction peaked at only ${trackingData.maxShoulder}°. (Target: ${config.shoulder.label}). Your elbow never reached the necessary height to clear the shoulder line, reducing leverage and increasing injury risk.</span>
            </li>`;

        trainingPlan.innerHTML += `
            <div class="training-step">
                <div class="step-number">${stepCount++}</div>
                <h4>Wall Stretch & Toss Alignment</h4>
                <p>Stand with your back against a fence. Go into your trophy pose. Your right elbow must touch the fence at exactly shoulder-height. If it's lower, adjust immediately. Muscle memory will reset after 50 reps.</p>
            </div>`;
    }

    // Check Knee
    if (trackingData.minKnee > config.knee.max) {
        flawsFound++;
        const timeStr = formatTime(trackingData.minKneeTime);
        flawList.innerHTML += `
            <li class="flaw-item">
                <strong>Check 3: Knee Bend (Power Load)</strong>
                <span class="timestamp-label">Detected at ${timeStr}</span>
                <span>Knee angle reached ${trackingData.minKnee}°. (Target: ${config.knee.label}). This "Insufficient Leg Drive" means you are arming the ball because your lower body is disengaged from the kinetic chain.</span>
            </li>`;

        trainingPlan.innerHTML += `
            <div class="training-step">
                <div class="step-number">${stepCount++}</div>
                <h4>Medicine Ball Throw</h4>
                <p>Hold a 4lb medicine ball. Drop your hips into a deep squat (feeling the tension in your calves and quads), then explode up, throwing the ball vertically. Translate this explosive kinetic sequence back to the serve.</p>
            </div>`;
    }

    // Check Racket Drop
    if (trackingData.minRacketDrop > config.racketDrop.max) {
        flawsFound++;
        const timeStr = formatTime(trackingData.minRacketDropTime);
        flawList.innerHTML += `
            <li class="flaw-item">
                <strong>Check 4: Racket Drop Depth</strong>
                <span class="timestamp-label">Detected at ${timeStr}</span>
                <span>Maximum racket drop was only ${trackingData.minRacketDrop}°. (Target: ${config.racketDrop.label}). A shallow racket drop shortens your "power runway," leading to significantly lower head speeds at impact.</span>
            </li>`;

        trainingPlan.innerHTML += `
            <div class="training-step">
                <div class="step-number">${stepCount++}</div>
                <h4>The "Back-Scratch" Pause</h4>
                <p>Perform serves where you intentionally pause for 1 second at the deepest point of the racket drop. This forces you to feel the stretch in your triceps and chest before the upward explosion.</p>
            </div>`;
    }

    // Check Pronation
    if (trackingData.maxPronation < config.pronation.threshold) {
        flawsFound++;
        const timeStr = formatTime(trackingData.maxPronationTime);
        flawList.innerHTML += `
            <li class="flaw-item">
                <strong>Check 5: Internal Rotation (The Snap)</strong>
                <span class="timestamp-label">Detected at ${timeStr}</span>
                <span>Pronation velocity index: ${trackingData.maxPronation}%. (Target: ${config.pronation.label}). You are "pushing" the serve rather than "snapping" it. This lack of internal rotation is the #1 cause of low serve percentages.</span>
            </li>`;

        trainingPlan.innerHTML += `
            <div class="training-step">
                <div class="step-number">${stepCount++}</div>
                <h4>Edge-to-Flat Shadow Swings</h4>
                <p>Swing your racket edge-first towards an imaginary ball, then at the last millisecond, snap your wrist so the strings are flat at impact. Do this 30 times without a ball to hear the "whoosh" of the racket head.</p>
            </div>`;
    }

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
        { label: 'Elbow Flexion', a: trackingDataA.minElbow, b: trackingDataB.minElbow, unit: '°' },
        { label: 'Knee Bend', a: trackingDataA.minKnee, b: trackingDataB.minKnee, unit: '°' },
        { label: 'Racket Drop', a: trackingDataA.minRacketDrop, b: trackingDataB.minRacketDrop, unit: '°' },
        { label: 'Pronation Speed', a: trackingDataA.maxPronation, b: trackingDataB.maxPronation, unit: '%' }
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

    // Add Visual Gallery
    let galleryHTML = `
        <div class="visual-gallery">
            <h3>Side-by-Side Visuals</h3>
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
        }
    };

    Object.keys(labels).forEach(key => {
        const snapA = trackingDataA.snapshots[key];
        const snapB = trackingDataB.snapshots[key];

        // Show even if only one exists for debugging, or show placeholders
        const imgA = (snapA && snapA.img) ? snapA.img : '';
        const imgB = (snapB && snapB.img) ? snapB.img : '';
        const timeA = snapA ? snapA.time : '--';
        const timeB = snapB ? snapB.time : '--';

        if (imgA || imgB) {
            galleryHTML += `
                <div class="gallery-item" style="${(!imgA || !imgB) ? 'opacity: 0.8;' : ''}">
                    <h4>${labels[key].title}</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">${labels[key].desc}</p>
                    <div class="comparison-row">
                        <div class="snapshot">
                            ${imgA ? `<img src="${imgA}" alt="Serve A ${key}">` : `<div style="height:200px; background:#121826; border-radius:8px; display:flex; align-items:center; justify-content:center;">Awaiting Point A</div>`}
                            <div class="snap-label">Serve A (Pro) (${timeA}s)</div>
                        </div>
                        <div class="snapshot">
                            ${imgB ? `<img src="${imgB}" alt="Serve B ${key}">` : `<div style="height:200px; background:#121826; border-radius:8px; display:flex; align-items:center; justify-content:center;">Awaiting Point B</div>`}
                            <div class="snap-label">Serve B (User) (${timeB}s)</div>
                        </div>
                    </div>
                </div>
            `;
        }
    });

    galleryHTML += `</div></div>`;
    const existingGallery = container.querySelector('.visual-gallery');
    if (existingGallery) existingGallery.remove();
    container.insertAdjacentHTML('beforeend', galleryHTML);

    loadingStatus.innerText = 'Comparison Complete.';
    loadingStatus.style.color = 'var(--success)';
    container.style.display = 'block';
    setTimeout(() => container.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

let isPoseProcessing = false;

// Video processing loop
async function processVideo() {
    if (videoElement.paused || videoElement.ended) return;

    if (canvasElement.width !== videoElement.videoWidth) {
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
    }
    if (comparisonMode && videoElementB.videoWidth > 0 && canvasElementB.width !== videoElementB.videoWidth) {
        canvasElementB.width = videoElementB.videoWidth;
        canvasElementB.height = videoElementB.videoHeight;
    }

    const percent = (videoElement.currentTime / videoElement.duration) * 100;
    progressBar.value = percent;
    updateTimeDisplay();

    if (!isPoseProcessing) {
        isPoseProcessing = true;
        try {
            activeVideo = 'A';
            await pose.send({ image: videoElement });

            if (comparisonMode && isVideoSetupB && !videoElementB.paused) {
                activeVideo = 'B';
                await pose.send({ image: videoElementB });
            }
        } catch (err) {
            console.error("Pose processing error:", err);
        } finally {
            isPoseProcessing = false;
        }
    }

    if ('requestVideoFrameCallback' in videoElement) {
        animationId = videoElement.requestVideoFrameCallback(processVideo);
    } else {
        animationId = requestAnimationFrame(processVideo);
    }
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
    setTimeout(async () => {
        try {
            activeVideo = 'A';
            await pose.send({ image: videoElement });
        } catch (err) { }
    }, 500);
});

videoElementB.addEventListener('loadeddata', async () => {
    while (videoElementB.videoWidth === 0 || videoElementB.videoHeight === 0) {
        await new Promise(r => setTimeout(r, 50));
    }
    canvasElementB.width = videoElementB.videoWidth;
    canvasElementB.height = videoElementB.videoHeight;
    canvasCtxB.clearRect(0, 0, canvasElementB.width, canvasElementB.height);
    setTimeout(async () => {
        try {
            activeVideo = 'B';
            await pose.send({ image: videoElementB });
        } catch (err) { }
    }, 500);
});

playBtn.addEventListener('click', () => {
    if (!isVideoSetup) return;

    if (videoElement.paused) {
        videoElement.play();
        if (comparisonMode && isVideoSetupB) videoElementB.play();
        playBtn.innerText = 'Pause';

        if ('requestVideoFrameCallback' in videoElement) {
            animationId = videoElement.requestVideoFrameCallback(processVideo);
        } else {
            processVideo();
        }
    } else {
        videoElement.pause();
        if (comparisonMode && isVideoSetupB) videoElementB.pause();
        playBtn.innerText = 'Play';
        if (animationId) {
            if ('requestVideoFrameCallback' in videoElement) {
                videoElement.cancelVideoFrameCallback(animationId);
            } else {
                cancelAnimationFrame(animationId);
            }
        }
    }
});

videoElement.addEventListener('ended', () => {
    playBtn.innerText = 'Play';
    if (animationId) {
        if ('requestVideoFrameCallback' in videoElement) {
            videoElement.cancelVideoFrameCallback(animationId);
        } else {
            cancelAnimationFrame(animationId);
        }
    }
    generateActionPlan();
});

progressBar.addEventListener('input', (e) => {
    if (!isVideoSetup || !videoElement.duration) return;
    const time = (e.target.value / 100) * videoElement.duration;
    videoElement.currentTime = time;
    updateTimeDisplay();

    // Process single frame if paused
    if (videoElement.paused) {
        // Just clear the canvas so old skeleton doesn't hang over new video position
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

        // Debounce pose detection during scrub for better performance
        clearTimeout(window.scrubTimeout);
        window.scrubTimeout = setTimeout(async () => {
            try {
                activeVideo = 'A';
                await pose.send({ image: videoElement });
            } catch (err) { }
        }, 150);
    }
});

// Start initialization
initPose();
updateBenchmarkLabels();
