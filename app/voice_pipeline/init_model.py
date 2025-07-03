# import os
# import warnings
# from pyannote.audio import Pipeline
# from huggingface_hub import login
# from speechbrain.inference.speaker import SpeakerRecognition

# pipeline = None
# recognizer = None

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

from pyannote.audio import Pipeline
from speechbrain.inference.speaker import SpeakerRecognition
import os

def init_voice_models():
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    
    # Load models once
    recognizer = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="pretrained_models/spkrec-ecapa-voxceleb"
    )

    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization",
        use_auth_token=hf_token
    )

    return recognizer, diarization_pipeline