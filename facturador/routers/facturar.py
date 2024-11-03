from fastapi import HTTPException, File, UploadFile, APIRouter, Form
import schemas.schemas as schemas
from tools.pyAfipWs_wrapper import (PyAfipWsWrapper, MODE_HOMOLOGACION, 
    INVOICE_CONCEPT_PRODUCTOS, INVOICE_CONCEPT_SERVICIOS, INVOICE_CONCEPT_PRODUCTOS_SERVICIOS)
import base64

router = APIRouter(
    prefix="/facturar",
    tags=["facturar"]
)

@router.post("/", response_model=schemas.CaeResponse)
async def facturar(
    file_afip: UploadFile = File(...),
    file_key: UploadFile = File(...),
    data: schemas.DataFactura = Form(...)
):
    invoice_concept = None

    with open(file_afip, 'rb') as cms_file:
        cms_content = cms_file.read()
        pyafipws_certificate =  cms_content.decode('utf-8')

    with open(file_key, 'rb') as cms_file:
        cms_content = cms_file.read()
        pyafipws_private_key =  cms_content.decode('utf-8')

    pyafip = PyAfipWsWrapper(MODE_HOMOLOGACION)
    token = pyafip.authenticate(pyafipws_certificate, pyafipws_private_key, data.cuit)

    if data.invoice_concept == 'PRODUCTOS':
        invoice_concept = INVOICE_CONCEPT_PRODUCTOS
    elif data.invoice_concept == 'SERVICIOS':
        invoice_concept = INVOICE_CONCEPT_SERVICIOS
    elif data.invoice_concept == 'PRODUCTOS_SERVICIOS':
        invoice_concept = INVOICE_CONCEPT_PRODUCTOS_SERVICIOS

    factura = pyafip.facturar(data.pos, data.invoice_type, token, invoice_concept, data.imp_total)
        
    return factura