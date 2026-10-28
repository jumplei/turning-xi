import os
import secrets
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env', override=False)

from .engine import EVENTS, TEAMS, DATASET_VERSION, state
from .match_clock import DURATION, DEMO_PRESS, DEMO_GOAL, HALF_TIME_START, SECOND_HALF_START, schedule
from .narrative import configured, narrate, session_status
from .phases import detect_phases
from .revisions import view_events
from .corrections import correction_preview, verification_demo

app = FastAPI(title='Turning XI', version='0.2.0')


class InsightRequest(BaseModel):
    second: int = Field(default=DEMO_GOAL, ge=0, le=DURATION)
    mode: Literal['fan', 'analyst'] = 'fan'
    language: Literal['en', 'zh'] = 'en'
    focus: Literal['neutral', 'home', 'away'] = 'neutral'
    recap: bool = False
    analysis_path: Literal['fast','deep'] = 'fast'
    revision: Literal['original','goal_removed'] = 'original'
    phase_id: Optional[str] = Field(default=None,max_length=40,pattern=r'^phase_evt_[0-9]+$')


@app.get('/api/health')
def health():
    return dict(status='ok', model_configured=configured(),
                auth_mode=os.getenv('AZURE_OPENAI_AUTH_MODE', 'api_key'),
                model=os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-6-luna'),
                protected=bool(os.getenv('MATCHMIND_ACCESS_TOKEN')), synthetic=True, model_session=session_status())


@app.get('/api/match')
def match():
    extras=[]
    for key,kind,predicate,label in [
        ('offside','offside',lambda e:True,'Offside'),
        ('yellow_card','card',lambda e:e.get('card_color')=='yellow','Yellow card'),
        ('red_card','card',lambda e:e.get('card_color')=='red','Red card'),
        ('second_yellow','card',lambda e:e.get('card_reason')=='second_yellow','Second caution'),
        ('substitution','substitution',lambda e:not e['at_half_time'],'Substitution')]:
        event=next((e for e in EVENTS if e['type']==kind and predicate(e)),None)
        if event: extras.append(dict(key=key,second=event['second'],label=label))
    return dict(id='synthetic_001', title='Northbridge FC vs Harbour Athletic',
                duration=DURATION, seed=42, dataset_version=DATASET_VERSION, synthetic=True, teams=TEAMS, schedule=schedule(),
                key_moments=[dict(key='half_time', second=HALF_TIME_START, label='Half time'),
                             dict(key='second_half', second=SECOND_HALF_START, label='Second half'),
                             dict(key='pressure', second=DEMO_PRESS, label='The press'),
                             dict(key='goal', second=DEMO_GOAL, label='Pressure to goal'),
                             dict(key='full_time', second=DURATION, label='Full time')]+extras)


@app.get('/api/state')
def get_state(second: int = Query(0, ge=0, le=DURATION), revision: Literal['original','goal_removed']='original'):
    snapshot=state(second,revision)
    snapshot['phases']=detect_phases(second,revision)
    return snapshot


@app.post('/api/insight')
def insight(body: InsightRequest, x_matchmind_token: str = Header(default='')):
    expected = os.getenv('MATCHMIND_ACCESS_TOKEN', '')
    if expected and not secrets.compare_digest(expected.encode(), x_matchmind_token.encode()):
        raise HTTPException(status_code=401, detail='A demo access token is required for insights.')
    try:
        return narrate(body.second,body.mode,body.language,body.focus,body.recap,body.revision,body.phase_id,body.analysis_path)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc))


@app.get('/api/events/export')
def export_events(second: int = Query(0, ge=0, le=DURATION),revision: Literal['original','goal_removed']='original'):
    return dict(synthetic=True, through_second=second,
                revision=state(second,revision)['revision'],events=view_events(EVENTS,second,revision))


class Artifact(BaseModel):
    id: str = Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
    kind: Literal['insight','recap','overlay']
    second: int = Field(ge=0,le=DURATION)
    revision_id: Literal['r1','r2']


class CorrectionRequest(BaseModel):
    second: int = Field(ge=0,le=DURATION)
    artifacts: list[Artifact] = Field(default_factory=list,max_length=50)
    language: Literal['en','zh'] = 'en'


@app.post('/api/corrections/preview')
def preview_correction(body: CorrectionRequest):
    try:
        return correction_preview(body.second,[a.model_dump() for a in body.artifacts],body.language)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc))


@app.post('/api/verification/demo')
def verify_demo(body: InsightRequest):
    return verification_demo(body.second,body.revision,body.language)


@app.get('/')
def index():
    return FileResponse(ROOT / 'frontend' / 'index.html')


app.mount('/static', StaticFiles(directory=ROOT / 'frontend'), name='static')
