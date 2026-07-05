$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$videoDir = "C:\Users\ravja\OneDrive\Documents\New project\output\insurance_copilot_submission\video"
$rawVideo = Join-Path $videoDir "b0234e40ac027a4aaa0423bd419ae3e8.webm"
$narrationText = Join-Path $videoDir "narration.txt"
$googleAudio = Join-Path $videoDir "google_tts_narration.wav"
$finalVideo = Join-Path $videoDir "insurance-copilot-capstone-demo-google-tts.mp4"

if (-not $env:GEMINI_API_KEY) {
  throw "Set GEMINI_API_KEY first. In Google AI Studio, click Get API key, then run: `$env:GEMINI_API_KEY='your_key_here'"
}

Set-Location $root
$env:PYTHONPATH = "$root\.deps;$root\app"
python scripts\gemini_tts.py --input $narrationText --output $googleAudio --voice Kore
ffmpeg -y -i $rawVideo -i $googleAudio -filter:a "apad" -shortest -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart $finalVideo
Write-Host "Wrote $finalVideo"
