"""
pipeline.reframe — Fase 6: Reencuadre vertical 9:16.
Estrategias: center (fallback) | smart (gaming) | face (podcast, mediapipe)
"""
import os
import subprocess


def get_face_crop_coords(video_path: str) -> tuple:
    """
    Analiza el primer frame con mediapipe y devuelve (x_start, crop_width)
    centrado en la cara detectada. Fallback al centro si no detecta cara.
    """
    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError(f"No se pudo leer el primer frame de: {video_path}")

    h, w = frame.shape[:2]
    crop_w = int(h * 9 / 16)
    face_center_x = w // 2  # fallback: centro

    try:
        detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = detector.process(rgb)
        if results.detections:
            box = results.detections[0].location_data.relative_bounding_box
            face_center_x = int((box.xmin + box.width / 2) * w)
    except Exception as e:
        print(f"[reframe] mediapipe falló, usando centro: {e}")

    x_start = max(0, min(face_center_x - crop_w // 2, w - crop_w))
    return x_start, crop_w


def reframe_vertical(clip_path: str, strategy: str = "smart",
                     output_path: str = None) -> str:
    """
    Reencuadra el clip a formato vertical 1080x1920 (9:16).

    Args:
        clip_path:   ruta al clip cortado (_raw.mp4)
        strategy:    'center' | 'smart' | 'face'
        output_path: ruta de salida (por defecto reemplaza _raw con _vertical)

    Returns:
        Ruta al clip vertical generado
    """
    out = output_path or clip_path.replace("_raw.mp4", "_vertical.mp4")

    if strategy == "face":
        x, cw = get_face_crop_coords(clip_path)
        vf = f"crop={cw}:ih:{x}:0,scale=1080:1920"
    else:
        # 'center' y 'smart' usan el mismo crop centrado
        # 'smart' podría extenderse con cropdetect en el futuro
        vf = "crop=ih*9/16:ih:iw/2-ih*9/16/2:0,scale=1080:1920"

    cmd = [
        "ffmpeg", "-i", clip_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-y", out
    ]
    subprocess.run(cmd, check=True)
    return out
