from __future__ import annotations

import argparse
import base64
import os
import wave
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Kore"
DEFAULT_RATE = 24000
DEFAULT_STYLE = (
    "Read this as a clear capstone demo narrator: confident, warm, natural, "
    "medium pace, no sales hype, with short pauses between sections.\n\n"
)


def write_wave(path: Path, pcm: bytes, channels: int = 1, rate: int = DEFAULT_RATE, sample_width: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(rate)
        wav.writeframes(pcm)


def extract_audio_data(payload: dict[str, Any]) -> str:
    candidates = [
        (
            payload.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("inlineData", {})
            .get("data")
            if payload.get("candidates")
            else None
        ),
        (
            payload.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("inline_data", {})
            .get("data")
            if payload.get("candidates")
            else None
        ),
        payload.get("outputAudio", {}).get("data"),
        payload.get("output_audio", {}).get("data"),
        payload.get("output", {}).get("audio", {}).get("data"),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    error = payload.get("error")
    if error:
        raise ValueError(f"Gemini TTS API error: {error}")
    raise ValueError(
        "Could not find output audio data in Gemini response. "
        f"Top-level keys: {sorted(payload.keys())}. Full response: {payload}"
    )


def synthesize(text: str, output: Path, api_key: str, model: str, voice: str, style: str) -> None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [
                {
                    "parts": [
                        {"text": f"{style}{text}"},
                    ],
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice,
                        }
                    }
                },
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    audio_b64 = extract_audio_data(response.json())
    write_wave(output, base64.b64decode(audio_b64))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate narration with Gemini TTS from Google AI Studio.")
    parser.add_argument("--input", default=str(ROOT / "evidence" / "narration.txt"))
    parser.add_argument("--output", default=str(ROOT / "evidence" / "google_tts_narration.wav"))
    parser.add_argument("--model", default=os.getenv("GEMINI_TTS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--voice", default=os.getenv("GEMINI_TTS_VOICE", DEFAULT_VOICE))
    parser.add_argument("--style", default=os.getenv("GEMINI_TTS_STYLE", DEFAULT_STYLE))
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set GEMINI_API_KEY first. In Google AI Studio, click Get API key, then run: "
            "$env:GEMINI_API_KEY='your_key_here'"
        )

    input_path = Path(args.input)
    output_path = Path(args.output)
    text = input_path.read_text(encoding="utf-8")
    synthesize(text, output_path, api_key=api_key, model=args.model, voice=args.voice, style=args.style)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
