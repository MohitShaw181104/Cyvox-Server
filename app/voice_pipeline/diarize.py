import os
from pathlib import Path
from pyannote.audio import Pipeline
from pydub import AudioSegment

# Load HuggingFace token and model
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")  # Add fallback if needed

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization",
    use_auth_token=HF_TOKEN
)

def is_valid_segment(seg: AudioSegment, min_sec=0.5):
        return len(seg) / 1000.0 > min_sec

def diarize_audio(audio_path: Path, output_dir: Path, pipeline):
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Perform diarization
    diarization = pipeline(str(audio_path), num_speakers=2)

    # Load original audio
    audio = AudioSegment.from_wav(audio_path)
    speaker_wavs = {}

    # Extract speaker segments
    for i, (segment, _, speaker) in enumerate(diarization.itertracks(yield_label=True)):
        start_ms = int(segment.start * 1000)
        end_ms = int(segment.end * 1000)
        print(f"{speaker} -> {segment.start:.2f}s to {segment.end:.2f}s")

        chunk = audio[start_ms:end_ms]
        
        if not is_valid_segment(chunk):
            print(f"⛔ Skipping short segment for {speaker} ({(end_ms - start_ms) / 1000:.2f}s)")
            continue

        if speaker not in speaker_wavs:
            speaker_wavs[speaker] = chunk
        else:
            speaker_wavs[speaker] += chunk

    # Export combined segments per speaker
    for speaker, combined in speaker_wavs.items():
        out_path = output_dir / f"{speaker}_combined.wav"
        combined.export(out_path, format="wav")
        print(f"Saved: {out_path}")
