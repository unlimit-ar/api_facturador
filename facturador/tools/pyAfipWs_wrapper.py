from pyafipws.wsaa import WSAA
import hashlib
from datetime import datetime
import time
import os
import sys
import traceback
import logging
from decimal import Decimal
from pytz import timezone

logger = logging.getLogger(__name__)

# MODE
MODE_PRODUCCION = 'produccion'
MODE_HOMOLOGACION = 'homologacion'


# INVOICE_CONCEPT
INVOICE_CONCEPT_PRODUCTOS = 1
INVOICE_CONCEPT_SERVICIOS = 2
INVOICE_CONCEPT_PRODUCTOS_SERVICIOS = 3

INVOICE_TYPE_AFIP_CODE = {
        ('out_invoice', 'A'): ('1', u'01-Factura A'),
        ('out_invoice', 'B'): ('6', u'06-Factura B'),
        ('out_invoice', 'C'): ('11', u'11-Factura C'),  
        ('out_invoice', 'E'): ('19', u'19-Factura E'),
        ('out_credit_note', 'A'): ('3', u'03-Nota de Crédito A'),
        ('out_credit_note', 'B'): ('8', u'08-Nota de Crédito B'),
        ('out_credit_note', 'C'): ('13', u'13-Nota de Crédito C'),
        ('out_credit_note', 'E'): ('21', u'21-Nota de Crédito E'),
        }
TIPO_DOCUMENTO = [
    ('0', 'CI Policía Federal'),
    ('1', 'CI Buenos Aires'),
    ('2', 'CI Catamarca'),
    ('3', 'CI Córdoba'),
    ('4', 'CI Corrientes'),
    ('5', 'CI Entre Ríos'),
    ('6', 'CI Jujuy'),
    ('7', 'CI Mendoza'),
    ('8', 'CI La Rioja'),
    ('9', 'CI Salta'),
    ('10', 'CI San Juan'),
    ('11', 'CI San Luis'),
    ('12', 'CI Santa Fe'),
    ('13', 'CI Santiago del Estero'),
    ('14', 'CI Tucumán'),
    ('16', 'CI Chaco'),
    ('17', 'CI Chubut'),
    ('18', 'CI Formosa'),
    ('19', 'CI Misiones'),
    ('20', 'CI Neuquén'),
    ('21', 'CI La Pampa'),
    ('22', 'CI Río Negro'),
    ('23', 'CI Santa Cruz'),
    ('24', 'CI Tierra del Fuego'),
    ('80', 'CUIT'),
    ('86', 'CUIL'),
    ('87', 'CDI'),
    ('89', 'LE'),
    ('90', 'LC'),
    ('91', 'CI extranjera'),
    ('92', 'en trámite'),
    ('93', 'Acta nacimiento'),
    ('94', 'Pasaporte'),
    ('95', 'CI Bs. As. RNP'),
    ('96', 'DNI'),
    ('99', 'Sin identificar/venta global diaria'),
    ('30', 'Certificado de Migración'),
    ('88', 'Usado por Anses para Padrón'),
    ]



class PyAfipWsWrapper(object):
    'PyAfipWsWrapper'

    def __init__(self, mode, service='wsfe') -> None:
        """_summary_

        Args:
            mode (str): deve ser MODE_HOMOLOGACION o MODE_PRODUCCION
            service (str, optional): 'wsfe', (el unico soportador por el momento).
        """

        # Recivo un diccionario con todos los valores para la factura y validacion.
        self.WSAA_URL = None
        self.service = service
        self.cache = None
        self.cuit = None

        if mode == 'homologacion':
            self.WSAA_URL = 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl'
        else:
            self.WSAA_URL = 'https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl'

        if service == 'wsfe':
            if mode == 'homologacion':
                self.WSDL = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
            elif mode == 'produccion':
                self.WSDL = ("https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL")
        # elif service == 'wsfex':
        #     if mode == 'homologacion':
        #         self.WSDL = "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL"
        #     elif mode == 'produccion':
        #         self.WSDL = ("https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL")
        else:
            logger.critical('AFIP ws is not yet supported! %s', service)


    def authenticate(self, pyafipws_certificate,  pyafipws_private_key, cuit, proxy=None,
            wrapper=None, cacert=None, cache=None) -> str :
        "Método unificado para obtener el ticket de acceso (cacheado)"
        DEFAULT_TTL = 60 * 60 * 5   # five hours

        wsaa = WSAA()
        wsaa.LanzarExcepciones = True
        wsaa.Cuit = cuit
        self.cuit = cuit

        try:
            # creo el nombre para el archivo del TA (según credenciales y ws)
            ta_src = (self.service + pyafipws_certificate + pyafipws_private_key).encode("utf8")
            fn = "TA-%s.xml" % hashlib.md5(ta_src).hexdigest()
            if self.cache:
                fn = os.path.join(cache, fn)
            else:
                fn = os.path.join(wsaa.InstallDir, "cache", fn)

            # leer el ticket de acceso (si fue previamente solicitado)
            if not os.path.exists(fn) or os.path.getsize(fn) == 0 or \
               os.path.getmtime(fn) + (DEFAULT_TTL) < time.time():
                # ticket de acceso (TA) vencido, crear un nuevo req. (TRA)
                logger.debug("Creando TRA...")
                tra = wsaa.CreateTRA(service=self.service, ttl=DEFAULT_TTL)
                # firmarlo criptográficamente
                logger.debug("Frimando TRA...")
                cms = wsaa.SignTRA(tra, pyafipws_certificate, pyafipws_private_key)
                # concectar con el servicio web:
                logger.debug("Conectando a WSAA...")
                ok = wsaa.Conectar(cache, self.WSAA_URL, proxy, wrapper, cacert)
                if not ok or wsaa.Excepcion:
                    raise RuntimeError("Fallo la conexión: %s" %
                        wsaa.Excepcion)
                # llamar al método remoto para solicitar el TA
                logger.debug("Llamando WSAA...")
                ta = wsaa.LoginCMS(cms)
                if not ta:
                    raise RuntimeError("Ticket de acceso vacio: %s" %
                        WSAA.Excepcion)
                # grabar el ticket de acceso para poder reutilizarlo luego
                logger.debug("Grabando TA en %s...", fn)
                try:
                    f = open(fn, 'w')
                    f.write(ta)
                    f.close()
                except IOError as e:
                    wsaa.Excepcion = (
                        "Imposible grabar ticket de accesso: %s" % fn)
            else:
                # leer el ticket de acceso del archivo en cache
                logger.debug("Leyendo TA de %s...", fn)
                f = open(fn, 'r')
                ta = f.read()
                f.close()
            # analizar el ticket de acceso y extraer los datos relevantes
            wsaa.AnalizarXml(xml=ta)
            wsaa.Token = wsaa.ObtenerTagXml("token")
            wsaa.Sign = wsaa.ObtenerTagXml("sign")
        except Exception:
            ta = ""
            if wsaa.Excepcion:
                # get the exception already parsed by the helper
                err_msg = wsaa.Excepcion
            else:
                # avoid encoding problem when reporting exceptions to the user:
                err_msg = traceback.format_exception_only(
                    sys.exc_info()[0], sys.exc_info()[1])[0]
            raise logger.debug("Error")
        return ta


    def facturar(self, pos_number:int, invoice_type:str ,token_auth:str , invoice_concept:int, 
                 total_amount:float, imp_neto_float:float = 0.0, imp_iva_float:float = 0.0, currency_rate='1',
                 iva_condition:str = None, sequences:int = 0, currency_code='PES', 
                 concepto:str = '0', service='wsfe', pyafipws_mode_cert = 'homologacion',
                 fecha_venc_pago = None, fecha_serv_desde = None, fecha_serv_hasta = None, consumidor_final:bool = True
                                ):

        invoice_type, invoice_type_desc = INVOICE_TYPE_AFIP_CODE[('out_invoice', invoice_type)]
        tipo_cbte = int(invoice_type)
        punto_vta = pos_number
        total_amount = Decimal(total_amount)

        for f in [fecha_venc_pago, fecha_serv_desde, fecha_serv_hasta]:
            if f:
                f.strftime("%Y-%m-%d")
        
        # check if it is an electronic invoice sale point:
        ##TODO
        #if not tipo_cbte:
        #    self.raise_user_error('invalid_sequence', pos.invoice_type.invoice_type)

        # import the AFIP webservice helper for electronic invoice
        from pyafipws.wsfev1 import WSFEv1  # local market
        ws = WSFEv1()
        ws.Cuit = self.cuit
        
        # elif service == 'wsfex':
        #     from pyafipws.wsfexv1 import WSFEXv1 # foreign trade
        #     ws = WSFEXv1()

        # connect to the webservice and call to the test method
        ws.LanzarExcepciones = True
        try:
            ws.Conectar(wsdl=self.WSDL, cache=self.cache, cacert=True)
        except Exception as e:
            msg = ws.Excepcion + ' ' + str(e)
            logger.error('WSAA connecting to afip: %s' % msg)

        # set AFIP webservice credentials:
        ws.SetTicketAcceso(token_auth)

        # get the last invoice number registered in AFIP
        cbte_nro_afip = ws.CompUltimoAutorizado(tipo_cbte, punto_vta)
        cbte_nro_next = int(cbte_nro_afip or 0) + 1

        # verify that the invoice is the next one to be registered in AFIP

        # invoice number range (from - to) and date:
        cbte_nro = cbt_desde = cbt_hasta = cbte_nro_next
        
        fecha_cbte = datetime.now(timezone('America/Argentina/Buenos_Aires')).strftime("%Y%m%d")

        # due and billing dates only for concept "services"
        concepto = tipo_expo = invoice_concept

        if consumidor_final:
            nro_doc = "0"           # only "consumidor final"
            tipo_doc = 99           # consumidor final

        # invoice amount totals:
        imp_total = str("%.2f" % abs(total_amount))
        imp_tot_conc = "0.00"
        imp_neto = str("%.2f" % abs(total_amount / Decimal('1.21')))
        imp_iva = str("%.2f" % abs(
            total_amount - total_amount / Decimal('1.21')))
        imp_subtotal = imp_neto  # TODO: not allways the case!
        imp_trib = "0.00"
        imp_op_ex = "0.00"
        if currency_code == 'PES':
            moneda_id = "PES"
            moneda_ctz = 1
        else:
            moneda_id = 'DOL'
            ctz = 1 / currency_rate
            moneda_ctz =  str("%.2f" % ctz)

        # create the invoice internally in the helper
        if service == 'wsfe':
            ws.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                fecha_serv_desde, fecha_serv_hasta,
                moneda_id, moneda_ctz)
        # elif service == 'wsmtxca':
        #     ws.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
        #         cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
        #         imp_subtotal, imp_trib, imp_op_ex, fecha_cbte,
        #         fecha_venc_pago, fecha_serv_desde, fecha_serv_hasta,
        #         moneda_id, moneda_ctz, obs_generales)
        # elif service == 'wsfex':
        #     ws.CrearFactura(tipo_cbte, punto_vta, cbte_nro, fecha_cbte,
        #         imp_total, tipo_expo, permiso_existente, pais_dst_cmp,
        #         nombre_cliente, cuit_pais_cliente, domicilio_cliente,
        #         id_impositivo, moneda_id, moneda_ctz, obs_comerciales,
        #         obs_generales, forma_pago, incoterms,
        #         idioma_cbte, incoterms_ds)

        # analyze VAT (IVA) and other taxes (tributo):
        if service in ('wsfe', 'wsmtxca'):
            iva_id = 5

            base_imp = ("%.2f" % abs(
                total_amount / Decimal('1.21')))
            importe = ("%.2f" % abs(
                total_amount - total_amount / Decimal('1.21')))
            # add the vat detail in the helper
            ws.AgregarIva(iva_id, base_imp, importe)

        # Request the authorization! (call the AFIP webservice method)
        try:
            if service == 'wsfe':
                ws.CAESolicitar()
                vto = ws.Vencimiento

        #except SoapFault as fault:
        #    msg = 'Falla SOAP %s: %s' % (fault.faultcode, fault.faultstring)
        except Exception as e:
            if ws.Excepcion:
                # get the exception already parsed by the helper
                #import ipdb; ipdb.set_trace()  # XXX BREAKPOINT
                msg = ws.Excepcion + ' ' + str(e)
            else:
                # avoid encoding problem when reporting exceptions to the user:
                import traceback
                import sys
                msg = traceback.format_exception_only(sys.exc_type,
                                                      sys.exc_value)[0]
        else:
            msg = u"\n".join([ws.Obs or "", ws.ErrMsg or ""])
        # calculate the barcode:
        if ws.CAE:
            cae_due = ''.join([c for c in str(ws.Vencimiento or '')
                                       if c.isdigit()])
            bars = ''.join([str(ws.Cuit), "%02d" % int(tipo_cbte),
                              "%04d" % int(punto_vta),
                              str(ws.CAE), cae_due])
            bars = bars + self.pyafipws_verification_digit_modulo10(bars)
        else:
            bars = ""

        if ws.CAE:
            # store the results
            vals = {'pyafipws_cae': ws.CAE,
                   'pyafipws_cae_due_date': vto or None,
                   'pyafipws_barcode': bars,
                }
            if not '-' in vals['pyafipws_cae_due_date']:
                fe = vals['pyafipws_cae_due_date']
                vals['pyafipws_cae_due_date'] = '-'.join([fe[:4],fe[4:6],fe[6:8]])

            vals['reference'] = '%05d-%08d' % (punto_vta,
                int(cbte_nro_next))
            return vals
        return msg
        

    def pyafipws_verification_digit_modulo10(self, codigo):
        "Calculate the verification digit 'modulo 10'"
        # http://www.consejo.org.ar/Bib_elect/diciembre04_CT/documentos/rafip1702.htm
        # Step 1: sum all digits in odd positions, left to right
        codigo = codigo.strip()
        if not codigo or not codigo.isdigit():
            return ''
        etapa1 = sum([int(c) for i,c in enumerate(codigo) if not i%2])
        # Step 2: multiply the step 1 sum by 3
        etapa2 = etapa1 * 3
        # Step 3: start from the left, sum all the digits in even positions
        etapa3 = sum([int(c) for i,c in enumerate(codigo) if i%2])
        # Step 4: sum the results of step 2 and 3
        etapa4 = etapa2 + etapa3
        # Step 5: the minimun value that summed to step 4 is a multiple of 10
        digito = 10 - (etapa4 - (int(etapa4 / 10) * 10))
        if digito == 10:
            digito = 0
        return str(digito)