"""ML compatibility gates. Never infer from a spectral cube as a temporal triplet."""
import json
import os
from pathlib import Path
import subprocess
import zipfile
import numpy as np
from app.routers.ml import SCRIPT_PATH


def read_stamp(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>8*1024**2:raise ValueError('NPZ ausente o mayor de 8 MiB')
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist())>8*1024**2:raise ValueError('NPZ expandido supera 8 MiB')
    with np.load(path,allow_pickle=False) as data:
        if all(k in data for k in ('science','reference','difference')):
            stamp=np.stack([data[k] for k in ('science','reference','difference')])
        elif 'stamp' in data:stamp=data['stamp']
        else:raise ValueError('NPZ requiere science/reference/difference o stamp')
        if stamp.shape!=(3,63,63) or not np.isfinite(stamp).all():raise ValueError('Entrada requerida: (3,63,63), todos los valores finitos')
    return stamp


def registered():
    manifest=os.getenv('MORLEY_ML_TRIPLETS')
    return json.loads(Path(manifest).read_text()) if manifest and Path(manifest).is_file() else []


def eligibility(product_id=None):
    missing=[name for name in ('ETER_ML_PYTHON','ETER_ML_WEIGHTS') if not os.getenv(name) or not Path(os.environ[name]).is_file()]
    compatible=[];rejected=[]
    for item in registered():
        if product_id not in item.get('product_ids',[]):continue
        try:
            read_stamp(item['path'])
            required=('wcs_aligned','psf_matched','band_compatible','quality_applied','real_epochs')
            if not all(item.get(k) is True for k in required):raise ValueError('Falta procedencia de alineación, PSF, banda, calidad o épocas reales')
            compatible.append(item['id'])
        except (ValueError,OSError,KeyError,zipfile.BadZipFile) as e:rejected.append(str(e))
    return {'status':'PASS' if compatible and not missing else 'BLOCKED','model_available':not missing,
        'missing':missing,'compatible_triplets':compatible,'rejected':rejected,
        'reason':None if compatible and not missing else 'Se necesita un triplete registrado ciencia/referencia/diferencia (3,63,63), con procedencia compatible y pesos disponibles. Un cubo espectral no es un triplete temporal.',
        'input_contract':{'format':'NPZ','shape':[3,63,63],'keys':['science','reference','difference'],'alternative_key':'stamp','finite_required':True,'order':['science','reference','difference']}}


def infer(product_id,triplet_id):
    state=eligibility(product_id)
    if triplet_id not in state['compatible_triplets'] or not state['model_available']:raise ValueError(json.dumps(state))
    item=next(r for r in registered() if r['id']==triplet_id)
    p=subprocess.run([os.environ['ETER_ML_PYTHON'],str(SCRIPT_PATH),'infer','--input',item['path'],'--weights',os.environ['ETER_ML_WEIGHTS']],capture_output=True,text=True,timeout=90)
    if p.returncode:raise ValueError('Inferencia falló; comprueba entorno y checkpoint compatible')
    return {'mode':'registered_real_triplet_experimental','scientifically_validated':False,'product_id':product_id,'triplet_id':triplet_id,'result':json.loads(p.stdout)}
