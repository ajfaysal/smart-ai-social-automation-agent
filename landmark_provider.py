"""Facial-landmark provider boundary used by temporal mouth validation."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LandmarkResult:
    available: bool
    provider: str
    face_count: int
    mouth_visible: bool
    confidence: float
    reason: str
    landmarks: list[tuple[float, float]] | None = None


class LandmarkProvider:
    name = "base"

    def available(self) -> bool:
        return False

    def detect(self, frame) -> LandmarkResult:
        raise NotImplementedError


class DisabledLandmarkProvider(LandmarkProvider):
    name = "disabled"

    def detect(self, frame) -> LandmarkResult:
        return LandmarkResult(False, self.name, 0, False, 0.0, "No facial-landmark provider is configured.")


class MediaPipeLandmarkProvider(LandmarkProvider):
    name = "mediapipe"

    def __init__(self) -> None:
        self._module = None
        try:
            import mediapipe as mp
            self._module = mp
        except ImportError:
            pass

    def available(self) -> bool:
        return self._module is not None

    def detect(self, frame) -> LandmarkResult:
        if not self.available():
            return LandmarkResult(False, self.name, 0, False, 0.0, "MediaPipe is not installed.")
        try:
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with self._module.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=2,
                    refine_landmarks=True, min_detection_confidence=0.5) as mesh:
                result = mesh.process(rgb)
            faces = result.multi_face_landmarks or []
            if not faces:
                return LandmarkResult(True, self.name, 0, False, 0.0, "No facial landmarks detected.")
            face = faces[0]
            points = [(float(p.x), float(p.y)) for p in face.landmark]
            mouth_indices = [61,146,91,181,84,17,314,405,321,375,291,78,308,191,95,88,178,87,14,317,402,318,324,308]
            mouth = [face.landmark[i] for i in mouth_indices if i < len(face.landmark)]
            visible = len(mouth) >= 12
            confidence = 0.9 if visible else 0.25
            return LandmarkResult(True, self.name, len(faces), visible, confidence,
                "Facial landmarks and mouth region detected." if visible else "Face landmarks detected but mouth visibility is uncertain.", points)
        except Exception as exc:
            return LandmarkResult(True, self.name, 0, False, 0.0, f"Landmark detection error: {exc}")


def get_landmark_provider() -> LandmarkProvider:
    value = os.getenv("MOUTH_LANDMARK_PROVIDER", os.getenv("LANDMARK_PROVIDER", "disabled")).strip().lower()
    if value == "mediapipe":
        return MediaPipeLandmarkProvider()
    return DisabledLandmarkProvider()
