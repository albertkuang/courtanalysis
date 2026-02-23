import cv2
import os
import sys

def transcode(input_path, output_path):
    print(f"Opening {input_path}...")
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video Properties: {width}x{height}, {fps} FPS, {total_frames} frames")

    # Use H.264 codec (avc1)
    # If avc1 fails, we can try mp4v
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print("Warning: avc1 codec failed, trying mp4v...")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print("Error: Could not create VideoWriter with any supported codec.")
        return

    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        count += 1
        if count % 100 == 0:
            print(f"Processed {count}/{total_frames} frames...")

    cap.release()
    out.release()
    print(f"Transcoding finished. Saved to {output_path}")

if __name__ == "__main__":
    src = "serve_analyzer_web/jasper_serve_20260201.mp4"
    dest = "serve_analyzer_web/jasper_serve_20260201_fixed.mp4"
    transcode(src, dest)
