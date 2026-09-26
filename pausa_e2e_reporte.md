# Verificacion E2E del comando PAUSA

```
VERIFICACION E2E DEL COMANDO PAUSA
Fecha de ejecucion (local): 2026-09-25 07:16:42
Workflow: barberiaAgenteUncensored
Cliente de prueba: 5214501111805@s.whatsapp.net
Dueño: 524521206246@s.whatsapp.net

==============================================================================
PRE-CHEQUEOS DE ENTORNO
==============================================================================
docker ps rc=0
evolution_api|Up 11 hours
evolution_postgres|Up 11 hours (healthy)
evolution_manager|Up 13 hours
evolution_redis|Up 13 hours (healthy)
barberia-n8n|Up 14 hours
barberia-postgres|Up 14 hours (healthy)
APIKEY Evolution leida: SI (40 chars)
Workflow encontrado: Barberia - Agente de citas (Uncensored AI) | active=True
  nodo presente 'Leer pausa': True
  nodo presente 'Calcular pausa': True
  nodo presente 'IF - Cliente pausado': True

==============================================================================
PASO 0 - LIMPIEZA PREVIA
==============================================================================
SQL: DELETE FROM barber_pausas WHERE jid IN ('5214501111805@s.whatsapp.net','5214521206246@s.whatsapp.net');
rc=0 stdout='DELETE 0' stderr=''
DELETE ejecutado (afecta filas, sin error si stderr vacio).
barber_pausas total filas: stdout='0' stderr=''
barber_clientes count = '0'  (Aplicar pausa hace INSERT..SELECT FROM barber_clientes)
barber_clientes jids = ''
barber_operadores = '5214521206246@s.whatsapp.net|Dueno\n524521206246@s.whatsapp.net|Dueno'

==============================================================================
PASO 1 - LINEA BASE (SIN PAUSA)
==============================================================================
Ejecuciones previas registradas: 30
Enviando mensaje de CLIENTE desde 5214501111805@s.whatsapp.net: 'hola, cuanto cuesta el corte?'
HTTP 200 | respuesta webhook: {"message":"Workflow was started"}
Esperando 40s...
Ejecucion baseline id=773 status=success finished=True
Nodos ejecutados: ["Webhook", "Normalizacion", "Leer operadores", "Comprobar operador", "¿Es operador?", "IF - No es del bot", "Leer pausa", "Calcular pausa", "IF - Cliente pausado", "Switch", "Edit Fields2", "Edit Fields", "Postgres Chat Memory", "OpenAI Chat Model", "AI Agent", "Mandar mensaje"]
message_content visto por Normalizacion: '  hola, cuanto cuesta el corte?'
Rama de 'IF - Cliente pausado' (0=true,1=false): 1
Rama de 'IF - No es del bot'   (0=true,1=false): 0
Respuesta del bot (Mandar mensaje -> message.conversation): 'El corte desvanecido o a tijera cuesta *$150* y dura 40 minutos. ¿Te reservo una cita? 😊'
Nodo 'AI Agent' presente: True
Nodo 'Mandar mensaje' presente: True

==============================================================================
PASO 2 - APLICAR LA PAUSA (comando del DUEÑO)
==============================================================================
Enviando comando desde el DUEÑO (524521206246@s.whatsapp.net): 'PAUSA 5214501111805 2h'
HTTP 200 | respuesta webhook: {"message":"Workflow was started"}
Esperando 20s...
Ejecucion del comando id=774 status=success
Nodos ejecutados: ["Webhook", "Normalizacion", "Leer operadores", "Comprobar operador", "¿Es operador?", "Router de comandos", "Parsear pausa", "Aplicar pausa", "Formatear pausa", "Responder al operador"]
Parsear pausa salida: pausaOk=True numero='5214501111805' horas=2
Aplicar pausa main: [[{"json": {"success": true}, "pairedItem": [{"item": 0}]}]]
Responder al operador json: {"key": {"remoteJid": "5214521206246@s.whatsapp.net", "fromMe": true, "id": "3EB07ADABCD9756CC048FD"}, "pushName": "Você", "status": "PENDING", "message": {"conversation": "No encontré un cliente con el número *5214501111805*.\n\nLa pausa solo aplica a clientes que ya existen en el sistema."}, "contextInfo": {"mentionedJid": [], "groupMentions": [], "ephemeralSettingTimestamp": {"low": 1790169445, "high": 0, "unsigned": false}, "disappearingMode": {"initiator": 0}}, "messageType": "conversation", "messageTimestamp": 1790342245, "instanceId": "f9641b53-395e-4a42-afa3-fdf1701b344b", "source": "w

==============================================================================
PASO 2b - VERIFICACION SQL DE LA PAUSA
==============================================================================
SQL: SELECT jid, hasta, motivo FROM barber_pausas WHERE jid='5214501111805@s.whatsapp.net';
rc=0
STDOUT: ''
STDERR: ''
>>> PAUSA PERSISTIDA EN barber_pausas: False

CAUSA PROBABLE: 'Aplicar pausa' hace
   INSERT INTO barber_pausas (jid,hasta,motivo) SELECT ... FROM barber_clientes ...
   y barber_clientes tiene 0 filas -> el SELECT no produce filas -> no hay INSERT.
   La fila de prueba '5214501111805@s.whatsapp.net' no existe en barber_clientes.

==============================================================================
PASO 3 - CLIENTE PAUSADO: EL BOT DEBE GUARDAR SILENCIO
==============================================================================
Enviando mensaje de CLIENTE desde 5214501111805@s.whatsapp.net: 'sigo esperando respuesta, cuanto cuesta el corte?'
HTTP 200 | respuesta webhook: {"message":"Workflow was started"}
Esperando 40s...
Ejecucion pausado id=778 status=success
Nodos ejecutados: ["Webhook", "Normalizacion", "Leer operadores", "Comprobar operador", "¿Es operador?", "IF - No es del bot", "Leer pausa", "Calcular pausa", "IF - Cliente pausado", "Switch", "Edit Fields2", "Edit Fields", "Postgres Chat Memory", "OpenAI Chat Model", "AI Agent", "Mandar mensaje"]
message_content: '  cuanto cuesta el corte?'
Rama 'IF - Cliente pausado' (0=true,1=false): 1
Calcular pausa salida: pausado=False hasta=None
Leer pausa main: [[{"json": {"pausado": "0", "hasta": null, "motivo": ""}, "pairedItem": {"item": 0}}]]
Nodo 'AI Agent' presente: True
Nodo 'Mandar mensaje' presente: True
Nodo 'Switch' presente: True
Respuesta del bot: 'El corte desvanecido o a tijera cuesta *$150* y dura 40 minutos. ¿Cuándo lo agendamos? 😊'

==============================================================================
PASO 3b - AISLAR EL MECANISMO: INYECTAR LA PAUSA POR SQL Y REPETIR
==============================================================================
SQL: INSERT INTO barber_pausas (jid, hasta, motivo) VALUES ('5214501111805@s.whatsapp.net', now() + interval '2 hours', 'verificacion e2e - inyeccion directa') ON CONFLICT (jid) DO UPDATE SET hasta = excluded.hasta, motivo = excluded.motivo;
rc=0 stdout='INSERT 0 1' stderr=''
Fila tras inyeccion -> STDOUT: '5214501111805@s.whatsapp.net|2026-09-25 09:18:24.530136-06|verificacion e2e - inyeccion directa'  STDERR: ''
>>> FILA INYECTADA PRESENTE: True
Enviando mensaje de CLIENTE desde 5214501111805@s.whatsapp.net: 'hola? hay alguien? cuanto cuesta el corte?'
HTTP 200 | respuesta webhook: {"message":"Workflow was started"}
Esperando 40s...
Ejecucion pausado(inyectado) id=781 status=success
Nodos ejecutados: ["Webhook", "Normalizacion", "Leer operadores", "Comprobar operador", "¿Es operador?", "IF - No es del bot", "Leer pausa", "Calcular pausa", "IF - Cliente pausado"]
Rama 'IF - Cliente pausado' (0=true,1=false): 0
Leer pausa main: [[{"json": {"pausado": "1", "hasta": "2026-09-25T15:18:24.530Z", "motivo": "verificacion e2e - inyeccion directa"}, "pairedItem": {"item": 0}}]]
Calcular pausa salida: pausado=True hasta='2026-09-25T15:18:24.530Z'
Nodo 'AI Agent' presente: False
Nodo 'Mandar mensaje' presente: False
Nodo 'Switch' presente: False
Respuesta del bot: None
Limpiando la fila inyectada...
rc=0 stdout='DELETE 1' stderr=''

==============================================================================
PASO 4 - CONTROL: SIN PAUSA EL BOT DEBE VOLVER A RESPONDER
==============================================================================
Borrando pausa de barber_pausas para el cliente de prueba...
rc=0 stdout='DELETE 0' stderr=''
Enviando mensaje de CLIENTE desde 5214501111805@s.whatsapp.net: 'ok, ya volvi, cuanto cuesta el corte?'
HTTP 200 | respuesta webhook: {"message":"Workflow was started"}
Esperando 40s...
Ejecucion control id=782 status=success
Nodos ejecutados: ["Webhook", "Normalizacion", "Leer operadores", "Comprobar operador", "¿Es operador?", "IF - No es del bot", "Leer pausa", "Calcular pausa", "IF - Cliente pausado", "Switch", "Edit Fields2", "Edit Fields", "Postgres Chat Memory", "OpenAI Chat Model", "AI Agent", "Mandar mensaje"]
Rama 'IF - Cliente pausado': 1
Respuesta del bot: 'El corte desvanecido o a tijera cuesta *$150* y dura 40 minutos. ¿Te agendo una cita? 😊'

==============================================================================
VEREDICTO
==============================================================================
CAPA 1 - Persistencia del comando PAUSA (Paso 2/2b):
  El comando del dueño fue reconocido y ejecuto 'Aplicar pausa' : True
  Fila creada en barber_pausas                                   : False

CAPA 2 - Mecanismo de silencio (Paso 3 con fila inyectada por SQL):
  Fila presente en barber_pausas al enviar el mensaje            : True
  IF - Cliente pausado tomo la rama TRUE                         : True
  El bot CALLO (sin Switch/AI Agent/Mandar mensaje)              : True

Paso 1 linea base  -> IF-No es del bot tomo rama false : PENDIENTE/OK segun arriba
  IF - Cliente pausado rama == false (1) : True
  El bot RESPONDIO en linea base        : True
Paso 2             -> fila en barber_pausas : False
Paso 3 (comando)   -> IF - Cliente pausado rama == true (0) : False
  El bot CALLO (sin AI Agent ni Mandar mensaje) : False
Paso 3b (inyectado)-> el mecanismo de silencio funciono : True
Paso 4 control     -> el bot vuelve a responder : True

>>> VEREDICTO GLOBAL (flujo tal como lo manda el dueño): PAUSA **NO** FUNCIONA PUNTA A PUNTA
>>> VEREDICTO DEL MECANISMO DE SILENCIO (con fila en barber_pausas): FUNCIONA

RESUMEN JSON: {
  "baseline_if_false": true,
  "baseline_responde": true,
  "pausa_en_bd": false,
  "pausado_rama_true": false,
  "pausado_silencio_total": false,
  "control_responde": true,
  "mecanismo_silencio_ok": true,
  "veredicto_ok": false,
  "exec_ids": {
    "baseline": "773",
    "comando": "774",
    "pausado_comando": "778",
    "pausado_inyectado": "781",
    "control": "782"
  },
  "barber_clientes_count": "0",
  "pausa_sql_stdout": "DELETE 0"
}
```
