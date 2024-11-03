from fastapi import HTTPException, File, UploadFile, APIRouter
from fastapi.responses import FileResponse
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import subprocess
import os
from secrets import token_hex
import schemas.schemas as schemas

router = APIRouter(
    prefix="/certificados",
    tags=["certificados"]
)

@router.get("/generate-rsa-key/")
async def generate_rsa_key():
    # Generar la clave privada RSA de 2048 bits
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Guardar la clave privada en un archivo
    private_key_path = "privada.pem"
    with open(private_key_path, "wb") as key_file:
        key_file.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()  # Sin cifrado
            )
        )

    # Devolver el archivo como respuesta
    return FileResponse(path=private_key_path, filename="privada.pem", media_type="application/x-pem-file")


@router.post("/generate-csr/")
async def generate_csr(
    csr_data: schemas.CSRRequest,  # Recibir el cuerpo JSON como un objeto Pydantic
    private_key: UploadFile = File(...)  # Recibir la clave privada como archivo
):
    csr_path = "pedido.csr"  # Ruta de salida para el archivo CSR

    # Guardar la clave privada temporalmente
    private_key_path = "temp_privada.pem"
    with open(private_key_path, "wb") as key_file:
        content = await private_key.read()
        key_file.write(content)

    # Crear el comando OpenSSL con los datos del sujeto
    subj_string = f"/C=AR/O={csr_data.subj_o}/CN={csr_data.subj_cn}/serialNumber=CUIT {csr_data.subj_cuit}"
    command = [
        "openssl", "req", "-new",
        "-key", private_key_path,
        "-subj", subj_string,
        "-out", csr_path
    ]

    try:
        # Ejecutar el comando OpenSSL para generar el CSR
        subprocess.run(command, check=True)

    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Error al generar la solicitud CSR.")

    finally:
        # Eliminar el archivo temporal de la clave privada
        os.remove(private_key_path)

    # Verificar si el CSR se generó correctamente
    if not os.path.exists(csr_path):
        raise HTTPException(status_code=500, detail="Error al crear el archivo CSR.")

    # Devolver el archivo CSR generado como respuesta
    return FileResponse(path=csr_path, filename="pedido.csr", media_type="application/pkcs10")
