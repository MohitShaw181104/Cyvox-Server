# import io
# import os
# import pathlib
# import requests
# import torch
# import ffmpeg
# import warnings
# import tempfile
# from bson import ObjectId
# from datetime import datetime, timezone
# from pydub import AudioSegment
# from pyannote.audio import Pipeline
# from huggingface_hub import login
# from speechbrain.inference.speaker import SpeakerRecognition
# from app.utils.cloudinary_upload import upload_audio_to_cloudinary
# import urllib.parse
# from collections import defaultdict
# from fastapi import UploadFile
# from starlette.datastructures import UploadFile as StarletteUploadFile

# # Globals
# pipeline = None
# recognizer = None
# THRESHOLD = 0.6
# USER_MATCH_THRESHOLD = 0.5

# def init_models():
#     global pipeline, recognizer

#     warnings.filterwarnings("ignore", category=UserWarning, message="torchaudio.*")

#     HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
#     if not HUGGINGFACE_TOKEN:
#         raise RuntimeError("Missing HuggingFace token in environment.")

#     login(token=HUGGINGFACE_TOKEN)

#     pipeline = Pipeline.from_pretrained(
#         "pyannote/speaker-diarization",
#         use_auth_token=True,
#         cache_dir="./models"
#     )

#     recognizer = SpeakerRecognition.from_hparams(
#         source="speechbrain/spkrec-ecapa-voxceleb",
#         savedir=os.path.join("pretrained_models", "spkrec-ecapa-voxceleb")
#     )

# def safe_path(path):
#     return pathlib.Path(path).resolve().as_posix()

# def download_audio(url, temp_dir):
#     response = requests.get(url)
#     if response.status_code != 200:
#         raise Exception(f"Failed to download audio: {url}")
#     url_path = urllib.parse.urlparse(url).path
#     filename = os.path.basename(url_path)
#     temp_path = os.path.join(temp_dir, filename)
#     with open(temp_path, 'wb') as f:
#         f.write(response.content)
#     return safe_path(temp_path)

# def convert_to_wav(input_path, temp_dir):
#     base_name = os.path.splitext(os.path.basename(input_path))[0]
#     out_path = os.path.join(temp_dir, base_name + ".wav")
#     ffmpeg.input(input_path).output(
#         out_path, ar=16000, ac=1, format='wav', loglevel='error'
#     ).overwrite_output().run()
#     return safe_path(out_path)

# async def convert_wav_to_mp3_uploadfile(wav_path: str) -> UploadFile:
#     audio = AudioSegment.from_wav(wav_path)
#     mp3_path = wav_path.replace(".wav", ".mp3")
#     audio.export(mp3_path, format="mp3")

#     file_obj = open(mp3_path, "rb")
#     return UploadFile(filename=os.path.basename(mp3_path), file=file_obj)

# def diarize_audio(wav_path):
#     return pipeline(wav_path, num_speakers=2)  # Force 2 speakers

# def extract_segments_by_speaker(diarization_result, wav_path):
#     full_audio = AudioSegment.from_wav(wav_path)
#     segments = defaultdict(list)
#     seen_speakers = set()

#     for turn, _, speaker in diarization_result.itertracks(yield_label=True):
#         seg_start = int(turn.start * 1000)
#         seg_end = int(turn.end * 1000)
#         if seg_end - seg_start <= 0:
#             continue  # skip invalid or empty segments

#         seen_speakers.add(speaker)
#         print("---------------------------------------------------------------")
#         print(f"Speaker: {speaker}, Start: {turn.start}, End: {turn.end}")
#         print("---------------------------------------------------------------")
#         seg = full_audio[seg_start:seg_end]
#         segments[speaker].append(seg)

#     print(f"Detected speakers: {list(seen_speakers)}")
#     return segments

# # Helper to verify if a segment is user's voice
# def is_user_segment(segment_audio: AudioSegment, user_sample_path: str, temp_dir: str) -> bool:
#     segment_path = os.path.join(temp_dir, "temp_seg.wav")
#     segment_audio.export(segment_path, format="wav")
#     score, _ = recognizer.verify_files(user_sample_path, segment_path)
#     os.remove(segment_path)
#     return score.item() >= USER_MATCH_THRESHOLD

# # Rebuilds clean scammer voice from all non-user segments
# def build_clean_scammer_audio(segments_by_speaker, user_sample_path, temp_dir):
#     clean_scammer_audio = AudioSegment.empty()
#     for speaker, segments in segments_by_speaker.items():
#         for seg in segments:
#             if not is_user_segment(seg, user_sample_path, temp_dir):
#                 clean_scammer_audio += seg
#     out_path = os.path.join(temp_dir, "clean_scammer.wav")
#     clean_scammer_audio.export(out_path, format="wav")
#     return safe_path(out_path)

# def identify_user_speaker(speaker_audio_map, user_sample_path):
#     for speaker, segment_path in speaker_audio_map.items():
#         score, _ = recognizer.verify_files(user_sample_path, segment_path)
#         score_val = score.item() if isinstance(score, torch.Tensor) else score
#         if score_val >= USER_MATCH_THRESHOLD:
#             return speaker, score_val
#     return None, None

# def compare_with_scammer_db(db_collection, exclude_doc_id, audio_path):
#     results = []
#     existing_records = list(db_collection.find({
#         "_id": {"$ne": ObjectId(exclude_doc_id)},
#         "userScammerAudioUrl": {"$exists": True}
#     }))
#     temp_dir = os.path.dirname(audio_path)

#     for record in existing_records:
#         scammer_audio_temp = download_audio(record["userScammerAudioUrl"], temp_dir)
#         score, _ = recognizer.verify_files(audio_path, scammer_audio_temp)
#         score_val = score.item() if isinstance(score, torch.Tensor) else score

#         if score_val >= THRESHOLD:
#             results.append({
#                 "matched_score": score_val,
#                 "matched_id": str(record["_id"])
#             })

#         os.remove(scammer_audio_temp)
    
#     return results

# # ENTRY POINT
# async def analyze_voice(
#     complaint_doc_id: str,
#     db,
#     user_sample_audio_url: str,
#     user_conversation_audio_url: str
# ):
#     if pipeline is None or recognizer is None:
#         init_models()

#     scammer_collection = db["scammer_complaints"]
#     complaint_doc = scammer_collection.find_one({"_id": ObjectId(complaint_doc_id)})
#     if not complaint_doc:
#         raise Exception("Complaint document not found.")

#     with tempfile.TemporaryDirectory() as temp_dir:
#         user_sample_raw = download_audio(user_sample_audio_url, temp_dir)
#         conv_audio_raw = download_audio(user_conversation_audio_url, temp_dir)

#         user_sample_wav = convert_to_wav(user_sample_raw, temp_dir)
#         conv_audio_wav = convert_to_wav(conv_audio_raw, temp_dir)

#         diarization_result = diarize_audio(conv_audio_wav)
#         speaker_segments = extract_segments_by_speaker(diarization_result, conv_audio_wav)
#         print("Speaker segments extracted.")

#         if len(speaker_segments) < 2:
#             print("⚠️ Warning: Only one speaker detected. Diarization may have failed.")

#         # 🧠 NEW: Build clean scammer audio by filtering segments
#         clean_scammer_wav = build_clean_scammer_audio(speaker_segments, user_sample_wav, temp_dir)

#         matched_results = compare_with_scammer_db(
#             scammer_collection,
#             exclude_doc_id=complaint_doc_id,
#             audio_path=clean_scammer_wav
#         )
#         print("Matched results:", matched_results)

#         scammer_file = await convert_wav_to_mp3_uploadfile(clean_scammer_wav)

#         user_scammer_audio_url = await upload_audio_to_cloudinary(
#             scammer_file,
#             str(complaint_doc["userId"]),
#             f"{complaint_doc_id}_scammer"
#         )

#         scammer_file.file.close()

#         print(f"User Scammer Audio URL: {user_scammer_audio_url}")
#         if not user_scammer_audio_url:
#             raise Exception("Failed to upload scammer audio to Cloudinary.")

#         scammer_collection.update_one(
#             {"_id": ObjectId(complaint_doc_id)},
#             {
#                 "$set": {
#                     "userScammerAudioUrl": user_scammer_audio_url,
#                     "updatedAt": datetime.now(timezone.utc)
#                 },
#                 "$push": {
#                     "matchedResults": {
#                         "$each": matched_results
#                     }
#                 }
#             }
#         )

#         return matched_results, user_scammer_audio_url