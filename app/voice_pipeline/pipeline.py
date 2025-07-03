import os, requests, shutil
from datetime import datetime
from pydub import AudioSegment
from pathlib import Path
from bson import ObjectId
import ffmpeg
from app.voice_pipeline.diarize import diarize_audio
from app.voice_pipeline.spectrograms import generate_spectrogram
from speechbrain.inference.speaker import SpeakerRecognition
from speechbrain.dataio.dataio import read_audio
import torch
from fastapi import UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from app.utils.cloudinary_upload import upload_audio_to_cloudinary
from io import BytesIO
from tempfile import SpooledTemporaryFile
from pydub.utils import mediainfo
from datetime import datetime, timezone
from .compare_embeddings import compare_with_existing_scammer_embeddings

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# def is_valid_audio(path):
#     try:
#         info = mediainfo(str(path))
#         duration = float(info.get("duration", 0))
#         return duration > 0.5  # skip very short audio
#     except Exception as e:
#         print(f"⚠️ Failed to read audio info for {path}: {e}")
#         return False

def download_file(url, save_path):
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Failed to download: {url}")
    with open(save_path, 'wb') as f:
        f.write(r.content)

def convert_to_wav(input_path, output_path):
    ffmpeg.input(str(input_path)).output(
        str(output_path),
        ar=16000,
        ac=1,
        format='wav',
        loglevel='error'
    ).overwrite_output().run()

async def convert_wav_to_mp3_uploadfile(wav_path: Path) -> UploadFile:
    mp3_path = str(wav_path).replace(".wav", ".mp3")
    
    audio = AudioSegment.from_wav(wav_path)
    audio.export(mp3_path, format="mp3")

    file_obj = open(mp3_path, "rb")
    return UploadFile(filename=os.path.basename(mp3_path), file=file_obj)

async def process_complaint_audio(user_id: str, complaint_id: str, sample_url: str, convo_url: str):
    # Access DB from FastAPI lifespan
    db = __import__('main').app.state.db
    complaints = db["scammer_complaints"]

    # Prepare directories
    user_dir = Path(f"./temp_audio/{complaint_id}")
    ensure_dir(user_dir)
    diarized_dir = user_dir / "diarized_segments"
    ensure_dir(diarized_dir)

    # Paths for downloaded and converted audio
    sample_mp3 = user_dir / "user_sample.mp3"
    convo_mp3 = user_dir / "conversation.mp3"
    sample_wav = user_dir / "user_sample.wav"
    convo_wav = user_dir / "conversation.wav"

    print(f"Downloading audio for user {user_id}...")
    download_file(sample_url, sample_mp3)
    download_file(convo_url, convo_mp3)

    print(f"Converting MP3 to WAV for user {user_id}...")
    convert_to_wav(sample_mp3, sample_wav)
    convert_to_wav(convo_mp3, convo_wav)

    print(f"Running diarization for {convo_wav}...")
    recognizer = __import__('main').app.state.recognizer
    pipeline = __import__('main').app.state.diarization_pipeline

    diarize_audio(convo_wav, diarized_dir, pipeline)

    print(f"Identifying user speaker from diarized segments...")
    # recognizer = SpeakerRecognition.from_hparams(
    #     source="speechbrain/spkrec-ecapa-voxceleb",
    #     savedir="pretrained_models/spkrec-ecapa-voxceleb"
    # )

    # Compare each diarized speaker with user sample
    similarity_scores = {}
    skipped_segments = []
    
    for file in diarized_dir.glob("SPEAKER_*.wav"):
        # if not is_valid_audio(file):
        #     reason = "invalid/short audio"
        #     print(f"⛔ Skipping {file.name} ({reason})")
        #     skipped_segments.append({"file": file.name, "reason": reason})
        #     continue

        try:
            result = recognizer.verify_files(str(sample_wav), str(file))

            if not isinstance(result, (tuple, list)) or len(result) != 2:
                raise ValueError("Unexpected result format")

            score, _ = result
            score = score.item() if isinstance(score, torch.Tensor) else score
            similarity_scores[file.name] = score
            print(f"✅ Compared with {file.name} → Score: {score:.4f}")

        except Exception as e:
            reason = f"verification failed: {str(e)}"
            print(f"⛔ Skipping {file.name} ({reason})")
            skipped_segments.append({"file": file.name, "reason": reason})
            continue


    # Defensive: Check if any scores were collected
    if not similarity_scores:
        raise ValueError("Voice analysis error: no valid speaker similarity scores were generated.")
    if len(similarity_scores) != 2:
        raise ValueError("Voice analysis error: Expected exactly 2 speaker segments for analysis.")

    # Determine who is user and scammer
    user_speaker = max(similarity_scores, key=similarity_scores.get)
    scammer_speaker = [f for f in similarity_scores if f != user_speaker][0]

    print(f"✅ User identified as: {user_speaker}")
    print(f"⚠️ Scammer identified as: {scammer_speaker}")

    # Final file paths
    user_audio_path = diarized_dir / user_speaker
    scammer_audio_path = diarized_dir / scammer_speaker

    # Create user/ and scammer/ subfolders
    user_out_dir = diarized_dir / "user"
    scammer_out_dir = diarized_dir / "scammer"
    ensure_dir(user_out_dir)
    ensure_dir(scammer_out_dir)

    final_user_audio = user_out_dir / "combined.wav"
    final_scammer_audio = scammer_out_dir / "combined.wav"

    # Move audio files
    user_audio_path.rename(final_user_audio)
    scammer_audio_path.rename(final_scammer_audio)

    # Generate spectrograms
    generate_spectrogram(final_user_audio, user_out_dir / "spectrogram.png")
    generate_spectrogram(final_scammer_audio, scammer_out_dir / "spectrogram.png")

    uploadable_mp3 = await convert_wav_to_mp3_uploadfile(final_scammer_audio)
    user_scammer_audio_url = await upload_audio_to_cloudinary(
        uploadable_mp3,
        user_id,
        f"{complaint_id}_scammer"
    )

    print(f"☁️ Uploaded to Cloudinary: {user_scammer_audio_url}")
    
    print("🔍 Extracting scammer embedding...")
    waveform = read_audio(str(final_scammer_audio)).unsqueeze(0)
    embedding = recognizer.encode_batch(waveform).squeeze(0).squeeze(0)
    embedding_list = embedding.detach().cpu().numpy().tolist()
    
    # Save to DB
    complaints.update_one(
    {"_id": ObjectId(complaint_id)},
        {
            "$set": {
                "userScammerAudioUrl": user_scammer_audio_url,
                "scammerEmbedding": embedding_list,
                "updatedAt": datetime.now(timezone.utc)
            },
        }
    )
    matches = compare_with_existing_scammer_embeddings(embedding_list, db, complaint_id=complaint_id)
    
    print("🔍 Matched with existing complaints:", matches)

    print(f"🎧 Final user audio: {final_user_audio}")
    print(f"🎧 Final scammer audio: {final_scammer_audio}")
    print(f"🖼️  Spectrograms saved in user/ and scammer/ folders.")
    print(f"Audio processing for user {user_id} complete.\n")
    
    # Clean up temp directory
    # shutil.rmtree("./temp_audio", ignore_errors=True)
    
    return matches, user_scammer_audio_url