import re
import spacy
import datetime
from sklearn.externals import joblib
from millenlp.helpers import nlp_utils
from millenlp.ner.entity_recognition import NER
from millenlp.models import db, Session, Answer, Message, Entity, Label
from millenlp.message import DummyMessage

class SubRed_NER(NER):
    def __init__(self, ner, normalization_dir):
        NER.__init__(self, ner)
        self._normalization = joblib.load(normalization_dir)

    def entity_parser(self, label, value, missing_entity):

        if label == 'IDENTIFICACION':
            value = ''.join(filter(str.isdigit, value))
            if not value:
                return None
            else:
                value = int(value)

        if label == 'DIA':
            value = ''.join(filter(str.isdigit, value))
            if not value:
                return None
            else:
                value = int(value)

        if label == 'ESPECIALIDAD':
            value = self._normalization[label].predict(DummyMessage(value))[0]
            if not value:
                return None

            value = value[0]

        entity = Entity(
            name = label,
            value = value
        )

        return entity

    def predict(self, message):
        # Search continually for entities, in case some is missing it sett the missing one into the DB
        entities = list()
        labels = Label.getLastLabelsbySession(message.sessionId)
        if not message._isMissingEntity or (message._isMissingEntity and labels[0] in ['FECHA', 'MES'] and not Entity.containsEntityBySession(message.session.id, 'MES') and not Entity.containsEntityBySession(message.session.id, 'FECHA')):

            
            doc = self.ner(message._text)

            isInIteration = lambda x: next((ent for ent in doc.ents if ent.label_ == x), None)
            if isInIteration('DIA') and not isInIteration('MES') and not isInIteration('FECHA'):
                day2int = {'lunes': 1,  'martes': 2, 'miercoles': 3, 'jueves': 4, 'viernes': 5, 'sabado': 6, 'domingo': 7}
                int2day = {1: 'lunes', 2: 'martes', 3: 'miercoles', 4: 'jueves', 5: 'viernes', 6: 'sabado', 7: 'domingo'}
                int2month = {1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'}

                today = datetime.date.today()
                nex_day = day2int[isInIteration('DIA').text.lower()]
                difference = (nex_day - today.isoweekday()) % 7 if nex_day !=  today.isoweekday() else 7
                next_day = today + datetime.timedelta(days=difference)

                # day
                entity = self.entity_parser('FECHA', str(next_day.day), True)                
                if entity:
                    entities += [entity]

                # month
                entity = self.entity_parser('MES', int2month[next_day.month], True)
                if entity:
                    entities += [entity]


            for ent in doc.ents:
                entity = self.entity_parser(ent.label_, ent.text, False)
                if entity:
                    entities += [entity]

            if message.session:
                print('\033[1m' + '\nENTITIES: ' + '\033[0m')
                for entity in entities:
                    print('\t ', entity.name, entity.value)
                    message.entities.append(entity)

        else:

            entity = self.entity_parser(labels[0], message._text, True)
            print('\033[1m' + '\nENTITIES: ' + '\033[0m')
            if entity:
                entities += [entity]
                if message.session:
                    print('\t ', entity.name, entity.value)
                    message.entities.append(entity)

        message.ner_evaluated = True
        return message
