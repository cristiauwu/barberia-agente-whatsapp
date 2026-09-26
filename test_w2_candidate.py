"""Offline safety tests for the unpublished W2 reminder candidate; no network calls."""
import json
import re
import subprocess
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name('BarberiaAgenteFLUJO-2-RECORDATORIOS.json')
CANDIDATE = Path(__file__).with_name('W2-CANDIDATE.json')
CALENDAR_ID = 'b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c09143c@group.calendar.google.com'


def link(to):
    return {'node': to, 'type': 'main', 'index': 0}


def build():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    data['id'] = 'w2-candidate-unpublished'
    data['name'] = 'W2 CANDIDATE - NOT PUBLISHED'
    data['description'] = 'Staged only: Calendar validation and migration needed before publication.'
    data['active'] = False
    for field in ('staticData', 'activeVersionId', 'versionId', 'versionCounter', 'triggerCount', 'sourceWorkflowId', 'shared'):
        data.pop(field, None)
    nodes = {n['name']: n for n in data['nodes']}
    nodes['Code']['parameters']['jsCode'] = '''const NOW=Date.now(), HOUR=3600000;
return $input.all().map((item,index)=>{
 const row=item.json, id=String(row.ID||'').trim();
 const fake=/^(?:placeholder|undefined|null|event[_-]?id(?:[_-]?placeholder)?|fake|test)$/i.test(id);
 const phone=String(row['Numero celular']||'').replace(/\\D/g,'');
 const date=String(row['Día ']||row['Día']||row.Fecha||'');
 const time=String(row.Hora||'');
 const formatted=/^\\d{4}-\\d{2}-\\d{2}$/.test(date)&&/^\\d{2}:\\d{2}(?::\\d{2})?$/.test(time);
 const start=formatted?new Date(`${date}T${time.length===5?time+':00':time}-06:00`):new Date(NaN);
 const validDate=Number.isFinite(+start)&&start.toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'})===date;
 return {json:{...row,idValido:validDate&&!fake&&/^[a-v0-9]{10,1024}$/.test(id),
  telefonoValido:phone.length>=10&&phone.length<=13,
  fechaISO:validDate?start.toISOString():'',
  fechaLegible:validDate?start.toLocaleString('es-MX',{timeZone:'America/Mexico_City'}):'',
  recordatorio24ISO:validDate?new Date(+start-24*HOUR).toISOString():'',
  recordatorio1ISO:validDate?new Date(+start-HOUR).toISOString():'',
  mandar24:validDate&&+start-24*HOUR>NOW,
  mandar1:validDate&&+start-HOUR>NOW,
 },pairedItem:{item:index}};
});'''
    nodes['Code1']['parameters']['jsCode'] = '''return $input.all().map((item,index)=>({
 json:{...item.json,executionId:$execution.id},pairedItem:{item:index}
}));'''
    nodes['Append or update row in sheet']['parameters']['columns']['value']['ID'] = '={{ $json.ID }}'
    nodes['IF - Es cita agendada']['parameters']['conditions']['conditions'][0]['leftValue'] = '={{ $json.Estatus }}'
    for rule in nodes['Switch']['parameters']['rules']['values']:
        for condition in rule['conditions']['conditions']:
            condition['leftValue'] = '={{ $json.Estatus }}'
    nodes['IF - Toca recordatorio 24 h']['parameters']['conditions']['conditions'][0]['leftValue'] = "={{ $json.idValido && $json.telefonoValido && $json.mandar24 ? 'si' : 'no' }}"
    nodes['IF - Toca recordatorio 1 h']['parameters']['conditions']['conditions'][0]['leftValue'] = "={{ $('Code').item.json.idValido && $('Code').item.json.telefonoValido && new Date($('Code').item.json.recordatorio1ISO).getTime() > Date.now() ? 'si' : 'no' }}"
    for hours in (24, 1):
        reminder = nodes[f'RECORDATORIO {hours} H']
        reminder['retryOnFail'] = False  # retrying a successful, unacknowledged send can duplicate it
        body = reminder['parameters']['bodyParameters']['parameters']
        body[0]['value'] = '={{ $json.telefonoDestino }}'
        body[1]['value'] = ('=Hola {{ $json.nombreConfirmado }}. Te recordamos tu cita mañana en Barber Chinos: {{ $json.fechaConfirmada }}. Si necesitas cambiarla, escríbenos aquí.' if hours == 24 else '=Hola {{ $json.nombreConfirmado }}. Tu cita en Barber Chinos es aproximadamente en una hora: {{ $json.fechaConfirmada }}. Te esperamos. Si necesitas cancelarla, escríbenos aquí.')
        wait = nodes[f'ESPERAR A {hours} H']
        wait['parameters']['dateTime'] = f"={{ $('Code').item.json.recordatorio{hours}ISO }}"
        data['nodes'].extend([
            {'id': f'w2-calendar-get-{hours}', 'name': f'Calendar GET {hours} H', 'type': 'n8n-nodes-base.googleCalendar', 'typeVersion': 1.3, 'position': [1800, hours * 12], 'parameters': {'resource': 'event', 'operation': 'get', 'calendar': {'__rl': True, 'mode': 'id', 'value': CALENDAR_ID}, 'eventId': "={{ $('Code').item.json.ID }}", 'options': {}}, 'credentials': {'googleCalendarOAuth2Api': {'id': 'I6TpcTTP1cn1tviR', 'name': 'Google Calendar account'}}, 'onError': 'continueErrorOutput'},
            {'id': f'w2-guard-{hours}', 'name': f'Guard {hours} H', 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [1980, hours * 12], 'parameters': {'mode': 'runOnceForEachItem', 'jsCode': guard_code(hours)}},
            {'id': f'w2-if-{hours}', 'name': f'IF Validado {hours} H', 'type': 'n8n-nodes-base.if', 'typeVersion': 2.2, 'position': [2160, hours * 12], 'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict', 'version': 2}, 'conditions': [{'id': f'validated-{hours}', 'leftValue': '={{ $json.recordatorioPermitido ? "si" : "no" }}', 'rightValue': 'si', 'operator': {'type': 'string', 'operation': 'equals'}}], 'combinator': 'and'}, 'options': {}}},
        ])
        data['connections'][f'ESPERAR A {hours} H']['main'][0] = [link(f'Calendar GET {hours} H')]
        data['connections'][f'Calendar GET {hours} H'] = {'main': [[link(f'Guard {hours} H')], []]}
        data['connections'][f'Guard {hours} H'] = {'main': [[link(f'IF Validado {hours} H')]]}
        data['connections'][f'IF Validado {hours} H'] = {'main': [[link(f'RECORDATORIO {hours} H')], []]}
    # Never confuse HTTP API response with original Sheets row.
    data['connections']['Code']['main'][0].append(link('Switch'))
    data['connections']['Notificar cita nueva al encargado']['main'][0] = []
    # Deleting an n8n execution is NOT a safe cancellation mechanism; fail closed instead.
    data['connections']['Switch']['main'][1] = []
    data['connections']['Switch']['main'][2] = []
    data['nodes'] = [n for n in data['nodes'] if n['name'] not in ('QUITAR RECORDATORIO', 'OBTENER INFO DE CITA ELIMINADA')]
    data['connections'].pop('QUITAR RECORDATORIO', None)
    data['connections'].pop('OBTENER INFO DE CITA ELIMINADA', None)
    CANDIDATE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return data


def guard_code(hours):
    return '''const booked=$('Code').item.json, event=$json;
const expected=Date.parse(booked.fechaISO), wake=expected-HOURS*3600000, now=Date.now();
const number=String(booked['Numero celular']||'').replace(/\\D/g,'');
const description=String(event.description||'');
const eventPhones=[...description.matchAll(/\\d{10,13}/g)].map(match=>match[0].slice(-10));
const valid=booked.idValido===true && booked.telefonoValido===true
 && event.id===booked.ID && event.status==='confirmed'
 && Date.parse(event.start?.dateTime||'')===expected
 && now>=wake-300000 && now<=wake+300000 && now<expected
 && eventPhones.includes(number.slice(-10));
return {json:{recordatorioPermitido:!!valid,
 telefonoDestino:valid?booked['Numero celular']:'',
 nombreConfirmado:valid?booked.Nombre:'',
 fechaConfirmada:valid?booked.fechaLegible:''}};'''.replace('HOURS', str(hours))


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build()
        cls.nodes = {n['name']: n for n in cls.data['nodes']}

    def javascript(self, code, expression):
        # JS at top level accepts `return` only in a function.
        source = f'const fn=new Function("$input","$execution","$","$json",{json.dumps("Date.now=()=>"+str(expression["now"])+";"+code)});const result=fn($input,$execution,$,$json);console.log(JSON.stringify(result));'
        setup = f'const $input={{all:()=>{json.dumps(expression["items"])}}};const $execution={{id:"42"}};const $=(name)=>({{item:{{json:{json.dumps(expression.get("booked", {}))}}}}});const $json={json.dumps(expression.get("event", {}))};'
        output = subprocess.check_output(['node', '-e', setup + source], text=True)
        return json.loads(output)

    def sample(self):
        return {'ID': 'abcdef01234567890', 'Estatus': 'agendado', 'Nombre': 'Cliente Prueba', 'Día ': '2026-10-03', 'Hora': '16:00:00', 'Numero celular': '5214500000000@s.whatsapp.net'}

    def test_multi_item_poll_preserves_ids_and_pairings(self):
        a = self.sample()
        b = {**a, 'ID': 'fedcba09876543210'}
        now = 1790000000000
        rows = self.javascript(self.nodes['Code']['parameters']['jsCode'], {'items': [{'json': a}, {'json': b}], 'now': now})
        self.assertEqual([r['json']['ID'] for r in rows], [a['ID'], b['ID']])
        self.assertEqual([r['pairedItem']['item'] for r in rows], [0, 1])
        second = self.javascript(self.nodes['Code1']['parameters']['jsCode'], {'items': rows, 'now': now})
        self.assertEqual([r['json']['executionId'] for r in second], ['42', '42'])
        self.assertEqual([r['json']['ID'] for r in second], [a['ID'], b['ID']])

    def test_calendar_truth_and_wake_window(self):
        booked = self.sample()
        booked.update(idValido=True, telefonoValido=True, fechaISO='2026-10-03T22:00:00.000Z', fechaLegible='3/10/2026, 4:00:00 p.m.')
        event = {'id': booked['ID'], 'status': 'confirmed', 'start': {'dateTime': '2026-10-03T16:00:00-06:00'}, 'description': 'WhatsApp 5214500000000'}
        wake = int(__import__('datetime').datetime.fromisoformat(booked['fechaISO'].replace('Z', '+00:00')).timestamp() * 1000) - 24 * 3600000
        code = self.nodes['Guard 24 H']['parameters']['jsCode']
        def check(evt=event, row=booked, when=wake):
            return self.javascript(code, {'items': [], 'event': evt, 'booked': row, 'now': when})['json']['recordatorioPermitido']
        self.assertTrue(check())
        self.assertFalse(check({**event, 'status': 'cancelled'}))
        self.assertFalse(check({**event, 'id': 'other-calendar-id'}))
        self.assertFalse(check({**event, 'start': {'dateTime': '2026-10-03T17:00:00-06:00'}}))
        self.assertFalse(check({**event, 'description': 'WhatsApp 5214599999999'}))
        self.assertFalse(check({**event, 'description': ''}))
        self.assertFalse(check(when=wake + 6 * 60000))
        self.assertFalse(check(when=wake - 6 * 60000))
        self.assertFalse(check(row={**booked, 'ID': 'placeholder', 'idValido': False}))
        self.assertFalse(check(row={**booked, 'Numero celular': '', 'telefonoValido': False}))
        self.assertFalse(check(evt={**event, 'error': 'Google API unavailable', 'id': None}))

    def test_invalid_date_and_placeholder_fail_closed(self):
        original = self.sample()
        rows = [
            {**original, 'ID': 'undefined'},
            {**original, 'ID': 'placeholder'},
            {**original, 'Día ': '2026-02-30'},
            {**original, 'Hora': '25:00:00'},
            {**original, 'Numero celular': ''},
        ]
        result = self.javascript(self.nodes['Code']['parameters']['jsCode'], {'items': [{'json': row} for row in rows], 'now': 1790000000000})
        self.assertEqual([r['pairedItem']['item'] for r in result], list(range(len(rows))))
        self.assertEqual([r['json']['idValido'] for r in result[:4]], [False] * 4)
        self.assertFalse(result[-1]['json']['telefonoValido'])

    def test_reminders_only_after_guards(self):
        conn = self.data['connections']
        for h in (24, 1):
            self.assertEqual(conn[f'ESPERAR A {h} H']['main'][0], [link(f'Calendar GET {h} H')])
            self.assertEqual(conn[f'IF Validado {h} H']['main'][0], [link(f'RECORDATORIO {h} H')])
        self.assertNotIn('QUITAR RECORDATORIO', self.nodes)
        self.assertFalse(self.data['active'])


if __name__ == '__main__':
    unittest.main()
