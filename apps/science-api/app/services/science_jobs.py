"""Single-worker bounded jobs; subprocess isolation, persisted states and deadlines."""
import json
import os
import signal
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from app.core.paths import PROJECT_ROOT
from app.services.roi import atomic_write

ROOT = PROJECT_ROOT / 'data/science-mvp/jobs'
TIMEOUT = 120
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='morley-science')
_slots = threading.BoundedSemaphore(4)
_active = set()
_lock = threading.Lock()


def path(job_id):
    if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id): raise FileNotFoundError('Trabajo desconocido')
    return ROOT / (job_id+'.json')


def write(job):
    atomic_write(path(job['id']),json.dumps(job,allow_nan=False).encode())


def get(job_id):
    job=json.loads(path(job_id).read_text())
    with _lock: alive=job_id in _active
    if job['status'] in ('QUEUED','RUNNING') and not alive:
        job.update(status='FAILED',error='Servidor reiniciado; trabajo interrumpido. Reintenta.');write(job)
    return job


def submit(request):
    ROOT.mkdir(parents=True,exist_ok=True)
    if len(list(ROOT.glob('*.json'))) >= 300: raise ValueError('Límite de trabajos guardados alcanzado (300)')
    if not _slots.acquire(blocking=False): raise ValueError('Cola llena: máximo 4 trabajos pendientes')
    job={'id':uuid.uuid4().hex,'status':'QUEUED','request':request,'result':None,'error':None,
         'created_at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':TIMEOUT}
    with _lock: _active.add(job['id'])
    try:
        write(job);_pool.submit(_run,job)
    except Exception:
        with _lock:_active.discard(job['id'])
        _slots.release();raise
    return job


def _run(job):
    try:
        job['status']='RUNNING';write(job)
        env={**os.environ,'PYTHONPATH':str(PROJECT_ROOT/'apps/science-api')+os.pathsep+str(PROJECT_ROOT),
             'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
        process=subprocess.Popen([sys.executable,'-m','app.services.science_worker',str(path(job['id']))],
            cwd=PROJECT_ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try: stdout,stderr=process.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.communicate();raise TimeoutError('Trabajo excedió 120 segundos')
        if process.returncode:
            raise ValueError((stderr.strip().splitlines() or ['Proceso científico falló'])[-1][:1000])
        job.update(status='SUCCEEDED',result=json.loads(stdout))
    except Exception as error:
        job.update(status='FAILED',error=str(error))
    finally:
        job['finished_at']=datetime.now(timezone.utc).isoformat();write(job)
        with _lock:_active.discard(job['id'])
        _slots.release()
