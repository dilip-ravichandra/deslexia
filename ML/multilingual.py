"""Language-aware supplemental support; unsupported checks are never advertised as verified."""
import os,re,threading,wave,io,unicodedata
from pathlib import Path
LANGUAGES={'en':'English','hi':'हिन्दी','kn':'ಕನ್ನಡ','ta':'தமிழ்'}
LANGUAGE_NAMES={'en':'English','hi':'Hindi','kn':'Kannada','ta':'Tamil'}
RANGES={'hi':(0x900,0x97f),'kn':(0xc80,0xcff),'ta':(0xb80,0xbff)}
ROOT=Path(__file__).resolve().parents[1]
def models():return Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))
def detect(text):
    letters=[c for c in text if unicodedata.category(c).startswith('L')]
    counts={lang:sum(low<=ord(c)<=high for c in letters) for lang,(low,high) in RANGES.items()}
    found=max(counts,key=counts.get)
    share=counts[found]/max(1,len(letters))
    return found if (counts[found]>=3 and share>=.35) or (len(letters)<=2 and share>=.8) else 'en'
def script_ok(text,language):
    letters=[c for c in text if unicodedata.category(c).startswith('L')]
    if not letters:return False
    if language=='en':return sum(c.isascii() for c in letters)/len(letters)>=.8
    low,high=RANGES[language];native=sum(low<=ord(c)<=high for c in letters)
    return native>=3 and native/len(letters)>=.5
MESSAGES={
'en':{'uncertain':'Choose the help you need for this part. There is not enough evidence to choose for you.','pronunciation':'Listen to this selected word or phrase. Asking for pronunciation help does not mean that a pronunciation error has been detected.','visual':'Open Reading comfort and choose the font, spacing or colours that suit you. Presentation preferences are separate from language understanding.','unavailable':'A local explanation in this language is unavailable. Your original text is unchanged.'},
'hi':{'uncertain':'इस हिस्से के लिए आपको किस तरह की मदद चाहिए? उपलब्ध जानकारी से सही मदद चुनना स्पष्ट नहीं है।','pronunciation':'चुने हुए शब्द या वाक्यांश का उच्चारण सुनें। इससे यह साबित नहीं होता कि आपके उच्चारण में गलती है।','visual':'पढ़ने की सुविधा वाले विकल्पों में अक्षर, दूरी और रंग चुनें।','unavailable':'इस भाषा में स्थानीय व्याख्या उपलब्ध नहीं है। आपका मूल पाठ बदला नहीं गया है।'},
'kn':{'uncertain':'ಈ ಭಾಗಕ್ಕೆ ಯಾವ ಸಹಾಯ ಬೇಕು ಎಂದು ಆಯ್ಕೆಮಾಡಿ. ಸರಿಯಾದ ಸಹಾಯವನ್ನು ಆಯ್ಕೆ ಮಾಡಲು ಸಾಕಷ್ಟು ಮಾಹಿತಿ ಇಲ್ಲ.','pronunciation':'ಆಯ್ಕೆಮಾಡಿದ ಪದ ಅಥವಾ ವಾಕ್ಯದ ಉಚ್ಚಾರಣೆಯನ್ನು ಕೇಳಿ. ಇದು ನಿಮ್ಮ ಉಚ್ಚಾರಣೆಯಲ್ಲಿ ತಪ್ಪಿದೆ ಎಂದು ಸೂಚಿಸುವುದಿಲ್ಲ.','visual':'ಓದುವ ಅನುಕೂಲದ ಆಯ್ಕೆಗಳಲ್ಲಿ ಅಕ್ಷರ, ಅಂತರ ಮತ್ತು ಬಣ್ಣಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ.','unavailable':'ಈ ಭಾಷೆಯಲ್ಲಿ ಸ್ಥಳೀಯ ವಿವರಣೆ ಲಭ್ಯವಿಲ್ಲ. ನಿಮ್ಮ ಮೂಲ ಪಠ್ಯವನ್ನು ಬದಲಾಯಿಸಿಲ್ಲ.'},
 'ta':{'uncertain':'இந்தப் பகுதிக்கு எந்த உதவி வேண்டும் என்பதைத் தேர்ந்தெடுக்கவும். சரியான உதவியைத் தேர்வு செய்ய போதுமான தகவல் இல்லை.','pronunciation':'தேர்ந்தெடுத்த சொல் அல்லது சொற்றொடரின் உச்சரிப்பைக் கேளுங்கள். உங்கள் உச்சரிப்பு தவறானது என்று இது குறிக்காது.','visual':'வாசிப்பு வசதி அமைப்புகளில் எழுத்து, இடைவெளி மற்றும் நிறத்தைத் தேர்வு செய்யவும்.','unavailable':'இந்த மொழியில் உள்ளூர் விளக்கம் கிடைக்கவில்லை. உங்கள் மூல உரை மாற்றப்படவில்லை.'}}

def explanation(span,context,category,style,source_language,output_language,span_start=None,allow_generation=True):
    if category=='OTHER_UNCERTAIN':return {'summary':MESSAGES[output_language]['uncertain'],'available':True,'source':'clarification','language':output_language,'note':'Insufficient routing evidence; no automatic rewrite.'}
    if category in {'PRONUNCIATION','VISUAL'}:
        return {'summary':MESSAGES[output_language]['pronunciation' if category=='PRONUNCIATION' else 'visual'],'available':True,'source':'localized_interface_instruction','language':output_language,'pronunciation_text':span if category=='PRONUNCIATION' else None,'note':'Speech is a support action, not automatic pronunciation assessment.' if category=='PRONUNCIATION' else 'Reading presentation changes how text looks, not its meaning.'}
    if source_language=='en' and output_language=='en':
        from ML.contextual_support import explain
        result=explain(span,context,style=style,category=category,span_start=span_start,allow_generation=allow_generation);result.update(available=True,language='en');return result
    from ML.local_generation import generate,available
    if not available():return {'summary':MESSAGES[output_language]['unavailable'],'available':False,'source':'model_unavailable','language':output_language,'note':'Run model setup; no English substitute is silently supplied.'}
    try:result=generate(span,context,category,style,language=output_language,span_start=span_start)
    except (ImportError,LookupError,OSError,RuntimeError,ValueError):
        return {'summary':MESSAGES[output_language]['unavailable'],'available':False,'source':'model_unavailable','language':output_language,'note':'Local generation failed. Check service readiness or select a shorter sentence. No generated draft is displayed.'}
    if result and result.get('withheld'):
        return {'summary':MESSAGES[output_language]['unavailable'],'available':False,'source':'source_screen_rejected','language':output_language,'quality':result['quality'],'note':'Source checks rejected both attempts. Select a full sentence or provide more context. No rejected draft is displayed.'}
    if not result or not script_ok(result['explanation'],output_language):
        return {'summary':MESSAGES[output_language]['unavailable'],'available':False,'source':'language_validation_failed','language':output_language,'note':'Generated output did not use the requested script. No unsupported answer is shown.'}
    return {'summary':result['explanation'],'available':True,'source':'native_local_qwen','style':style,'is_real_pretrained_inference':True,'language':output_language,'quality':result.get('quality'),'note':'Source-linked explanation passed automated screening. This does not guarantee correctness. Compare with the original.'}

_TTS=None
_TTS_LANG=None
_TTS_LOCK=threading.Lock()
def speech(text,language):
    global _TTS,_TTS_LANG
    folder=models()/('tts-'+language)
    if not (folder/'config.json').exists():raise LookupError('Offline speech model is missing for '+LANGUAGE_NAMES[language]+'. Run multilingual setup.')
    import torch,numpy as np
    from transformers import VitsModel,AutoTokenizer
    from ML.inference_resources import LOCK
    with LOCK,_TTS_LOCK:
        torch.set_num_threads(4)
        if _TTS_LANG!=language:
            _TTS=None
            tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True)
            model=VitsModel.from_pretrained(folder,local_files_only=True).eval();_TTS=(tokenizer,model);_TTS_LANG=language
        tokenizer,model=_TTS
        inputs=tokenizer(text,return_tensors='pt')
        with torch.inference_mode():audio=model(**inputs).waveform[0].numpy()
        audio=np.clip(audio,-1,1);pcm=(audio*32767).astype('<i2').tobytes();out=io.BytesIO()
        with wave.open(out,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(model.config.sampling_rate);wav.writeframes(pcm)
        return out.getvalue()
