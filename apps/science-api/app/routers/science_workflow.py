from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from app.services import local_fits, science_jobs, science_targets, ml_inputs
from app.routers.roi import operation
from science.pipeline.region import Region

router=APIRouter(prefix='/api/v1/science/workflow',tags=['Science workflow'])

@router.get('/targets')
def targets(epoch:float=Query(2026.,ge=2000,le=2050)):
    return science_targets.targets(epoch)

class Search(BaseModel):
    region:Region
    target_id:str|None=None

@router.post('/catalog/search')
def search(body:Search):
    return operation(local_fits.search,body.region.center.ra,body.region.center.dec,body.region,body.target_id)

class Job(BaseModel):
    kind:Literal['index','import_local','extract','analysis','temporal','inference','demo']
    region:Region|None=None
    asset_id:str|None=None
    catalog_id:str|None=None
    product_id:str|None=None
    triplet_id:str|None=None
    hdu_index:int=Field(default=0,ge=0)
    channel:int=Field(default=0,ge=0)

    @model_validator(mode='after')
    def required_fields(self):
        fields={'index':[],'demo':[],'import_local':['catalog_id','region'],'extract':['asset_id','region'],
                'analysis':['product_id'],'temporal':['region'],'inference':['product_id','triplet_id']}
        for name in fields[self.kind]:
            if getattr(self,name) is None:raise ValueError(f'Falta {name}')
        return self

@router.post('/jobs',status_code=202)
def submit(body:Job):
    return operation(science_jobs.submit,body.model_dump(mode='json'))

@router.get('/jobs/{job_id}')
def get(job_id:str):return operation(science_jobs.get,job_id)

@router.get('/jobs/{job_id}/result')
def result(job_id:str):
    job=operation(science_jobs.get,job_id)
    if job['status']!='SUCCEEDED':raise HTTPException(409,'El trabajo aún no produjo un resultado')
    return JSONResponse(job['result'],headers={'Content-Disposition':f'attachment; filename="science-{job_id}.json"'})

@router.get('/ml/compatibility')
def compatibility(product_id:str|None=None):return operation(ml_inputs.eligibility,product_id)
