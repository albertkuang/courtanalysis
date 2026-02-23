# AI Serve Analyzer: Methodology & Technical Documentation

This document outlines the technical architecture, algorithms, and biomechanical logic used by the AI Serve Analyzer to transform raw video into professional-grade tennis analytics.

## 1. Release Versions: Classic vs. V2
The analyzer is now available in two distinct versions to suit different technical needs:

### A. NeuraSkill Serve V2 (YOLO Powered) - [Recommended]
Located in the main directory, this version uses the **YOLOv8-Pose** server-side engine.
- **Normal Playback**: Because analysis is offloaded to the server, you can play the video at normal 1x speed during the process. No more stuttering.
- **High Precision**: Superior skeletal tracking even in low-light or cluttered backgrounds.
- **Deep Analytics**: Supports advanced metrics like X-Factor and explosive velocity more reliably.

### B. NeuraSkill Classic (MediaPipe)
Located in `serve_analyzer_classic`, this version uses the original browser-based engine.
- **Slow Motion Processing**: Uses a deterministic frame-by-frame loop (approx. 30fps) to ensure every frame is analyzed by the browser AI.
- **Zero Server Dependency**: Runs entirely offline in your browser.
- **High Reliability**: Best for users with limited internet or no access to the Python backend.

## 2. Key Biomechanical Metrics
The analyzer tracks six primary "checkpoint" metrics derived from pro-level service coaching standards:

| Metric | Biomechanical Significance | Calculation Method |
| :--- | :--- | :--- |
| **Shoulder Abduction** | Leverage & Injury Prevention | Angle between Hip (24), Shoulder (12), and Elbow (14). |
| **Elbow Flexion** | The "Trophy Pose" Stability | Angle between Shoulder (12), Elbow (14), and Wrist (16). |
| **Knee Bend** | Kinetic Chain Power Source | Angle between Hip (24), Knee (26), and Ankle (28). |
| **Racket Drop** | The Power Runway | Calculated as the deepest elbow flexion relative to the shoulder line during the acceleration phase. |
| **Pronation Velocity** | "The Snap" (Core speed) | Measures the explosive velocity of the hitting wrist (16) relative to frame-time ($V = d/t$). |
| **X-Factor Separation** | Elastic Storage/Thoracic Rotation | The difference in rotation angles between the Hip line (23-24) and the Shoulder line (11-12). |

## 3. The Comparison Logic: "Temporal Normalization"
Comparing an amateur serve to a pro serve (like Jannik Sinner) is difficult because they move at different speeds. The AI uses **Phase Gating** to achieve "Apple-to-Apples" analysis:
1. **Sync Point**: The AI automatically detects the exact frame of **Impact** (Contact Point) for both videos.
2. **Phase Alignment**: It then aligns all other snapshots (**Trophy**, **Knee Bend**, **Racket Drop**) relative to that impact point.
3. **Benchmarking**: Users are compared against ATP Pro (Elite) or ITF Junior (Advanced) benchmarks to provide an objective "Technical Score."

## 4. Reliability & Validity: Can you trust it?
### Why it is Reliable:
- **Objective Measurement**: Unlike a human eye, the AI doesn't "feel" if a serve is good; it calculates the exact degrees of flexibility and rotation.
- **Visual Evidence**: Every metric is paired with a snapshot. If the AI says your knee bend is 150°, it provides the photo of you at that exact angle for verification.
- **Consistency**: The AI applies the exact same mathematical rules to every player, removing coach-bias.

### Usage Requirements for Best Accuracy:
To ensure the analytics are "Coach-Trustable," the following conditions should be met:
- **Camera Angle**: Best results are achieved from a **45-degree side/rear profile** or **directly from the side**. 
- **Visibility**: The player's full body (head to toe) must be in the frame.
- **Lighting**: Avoid heavy backlighting (e.g., serving directly into the sun) which can obscure joint landmarks.

## 5. Summary for Players & Coaches
The AI Serve Analyzer is designed as a **Diagnostic Tool**. While it cannot replace a coach's tactical advice, it provides the **hard data** needed to identify "power leaks" in the kinetic chain. If the AI detects a 1.5° X-Factor, it is a factual indicator that the player is arms-dominant and needs to work on hip/shoulder separation.
