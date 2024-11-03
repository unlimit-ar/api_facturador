from pydantic import BaseModel
from datetime import datetime
from typing import List

class CartaResponse(BaseModel):
    pass

class CartaRequest(BaseModel):
    carta: List

class CSRRequest(BaseModel):
    subj_o: str
    subj_cn: str
    subj_cuit: str

class DataFactura(BaseModel):
    mode: str = 'homologacion'
    cuit: str
    pos: int
    invoice_type: str
    invoice_concept: str
    imp_total: float

class CaeResponse(BaseModel):
    pyafipws_cae: str
    pyafipws_cae_due_date: str
    pyafipws_barcode: str
    reference: str