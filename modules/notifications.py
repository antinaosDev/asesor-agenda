import asyncio
from notificationapi_python_server_sdk import notificationapi

def send_verification_email(client_id, client_secret, to_email, code="123456"):
    """
    Envía una notificación usando NotificationAPI.
    Parámetros obtenidos de la hoja de cálculo.
    """
    async def _send():
        try:
            print(f"DEBUG: Iniciando envío a {to_email}")
            print(f"DEBUG: ClientID: {client_id[:5]}... Secret: {'*' * 5}")
            
            notificationapi.init(client_id, client_secret)
            
            # Estructura basada en el snippet del usuario
            response = await notificationapi.send({
                "notificationId": "notificaciones_app", # "type" en snippet antiguo, "notificationId" en SDK nuevo
                "user": {
                    "id": to_email,
                    "email": to_email
                },
                "mergeTags": {
                    "code": code
                },
                # Fallback de contenido si no hay plantilla configurada
                "emailOptions": {
                     "subject": "Código de Verificación - App Ejecutiva",
                     "html": f"<h1>Tu código de verificación es: {code}</h1><p>Enviado desde tu App Streamlit.</p>"
                }
            })
            print(f"DEBUG: Respuesta NotificationAPI: {response}")
            return True
        except Exception as e:
            print(f"DEBUG: Error enviando notificación: {e}")
            import traceback
            traceback.print_exc()
            return False

    # Ejecutar async en contexto sync de Streamlit
    try:
        asyncio.run(_send())
        return True
    except Exception as e:
        return False
