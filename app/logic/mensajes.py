# app/logic/mensajes.py
import random

def obtener_mensaje(modo="recordatorio"):
    recordatorios = [


                {"titulo": "Cinturón de Seguridad", 
                 "texto": "- Es obligatorio usarlo en todo momento.",
                 "imagen": "/static/mensaje/M_1.webp"},


                {"titulo": "Usar el EPP", 
                 "texto": "- Al circular por las áreas operativas.",
                 "imagen": "/static/mensaje/M_3.jpg"},


                {"titulo": "CheckList", 
                 "texto": "- Asegúrate de realizar siempre la inspección preoperativa.",
                 "imagen": "/static/mensaje/M_2.webp"},


                 {"titulo": "Inspección Técnica Vehicular", 
                 "texto": "- Asegúrate que el vehículo cuente con el ITV al día.",
                 "imagen": "/static/mensaje/M_2.webp"},


                {"titulo": "¡PROHIBIDO!", 
                 "texto": "- Transportar pasajeros.",
                 "imagen": "/static/mensaje/M_4.webp"},
            ]
    

    mensaje = {"titulo": "Recuerda", "texto": "Mantén tus documentos y permisos actualizados."}
    return random.choice(recordatorios) if modo == "recordatorio" else mensaje