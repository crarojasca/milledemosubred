import sys
import logging
import json
import spacy
import traceback
import numpy as np
import random

from flask import Flask, request, Response, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect

from millenlp.config import DevelopmentConfig, ProductionConfig
from millenlp.dialog_engine import AnswerManager
from millenlp.state_machine import StateMachine
from millenlp.models import db, Session, Answer, Message, Transition, Entity
# from millenlp.ner.entity_recognition import SubRed_NER
from subred_ner import SubRed_NER
from millenlp import helpers
from millenlp.message import DummyMessage, Message
from millenlp.ner import NER

from visualization import Visualizer

async_mode = None

app = Flask(__name__, template_folder='./views', static_url_path='/voicebot_demo_subred/static')
app.config.from_object(DevelopmentConfig)
app.config['SECRET_KEY'] = 'secret!'
db.init_app(app)
socketio = SocketIO(app, async_mode=async_mode, path='/voicebot_demo_subred/socket.io')


@app.route('/voicebot_demo_subred')
def structure():
    return render_template("flow/structure.html", async_mode=socketio.async_mode)

@app.route('/voicebot_demo_subred/test_model', methods=['GET', 'POST'])
def test_model():
    req = request.get_json()
    logger.info(req)
    assert type(req['message']) is str, 'message deberia ser de tipo string'
    session = Session(
                        id = 'test_session' + str([random.randint(0,9) for i in range(10)]),
                        transfer = False,
                        attempt = 0,
                        state = answer_manager._state_machine._initial_state,
                        channel = 'Default'
                     )
    message = Message(req['message'], session)
    answer_manager.initialize(session)
    answer_manager._state_machine.initialize(session)
    state_machine_prediction = answer_manager._state_machine.test_transition(message)
    entities = []
    for entity in ner.ner(req['message']).ents:
        entities.append({
            "label": entity.label_,
            "text": entity.text,
            "start_char": entity.start_char,
            "end_char": entity.end_char
        })
    response = {
        "intention" : state_machine_prediction,
        "entities" : entities
    }
    logger.info(response)
    return Response(json.dumps(response), mimetype='application/json')


@app.route(sys.argv[3], methods=['GET', 'POST'])
def dialog():
    global ner
    global state_machine
    global logger
    response = {}
    # try:
    # Captura de los argumentos json
    req = request.get_json()

    # Verificacion de que todos los paramatros se encuentran en la invocacion
    for arg in ['sessionID', 'isSessionActive', 'channel', 'message']:
        if arg not in req:
            raise Exception('Hace falta el parametro ' + arg)

    # Validacion del tipo de dato correcto de cada uno de los parametros
    assert type(req['sessionID']) is str, 'sessionId deberia ser de tipo string'
    assert type(req['isSessionActive']) is bool, 'isSessionActive deberia ser de tipo bool'
    assert type(req['channel']) is str, 'channel deberia ser de tipo string'
    assert type(req['message']) is str, 'message deberia ser de tipo string'
    logger.info(req)

    if not req['isSessionActive']:
        #Delete session
        Session.delete(req['sessionID'])
        response = {'result': 'ok',
                    'isError': False,
                    'traceback': 'Function is not active'}
    else:
        #Get or Create Session
        session = None
        if Session.contains(req['sessionID']):
            session = Session.get(req['sessionID'])
        else:
            session = Session(
                id = req['sessionID'],
                transfer = False,
                attempt = 0,
                channel = req['channel'],
                answer_manager = req['answerManager'] if 'answerManager' in req else 'Default',
                product = 'voicebot_demo_subred'
            )
            Session.add(session)

        socketio.emit('user_interaction',
                        {'message': req['message'],
                         'session': req['sessionID']},
                        namespace='/')


        state = Transition.getLastStatebySession(req['sessionID'])
        state = state if state else answer_manager._state_machine._initial_state
        starting_state = answer_manager._state_machine._states[state]
        lastQuestion = Message.getLastMessagebySession(session.id)

        #State and Intention
        message, answer, length, session, writing_time = answer_manager.get_answer(req['message'], session)

        next_state = Transition.getLastStatebySession(req['sessionID'])

        entities = Entity.getAllEntities(session.id)
        entities = [{'label' : entity.name, 'text' : entity.value} for entity, message in entities]

        """FrontEnd Interaction"""
        
        if starting_state._state in ["general", "despedida"]:
            model = answer_manager._state_machine._states["general"]._model
            classes = model._classifier.classes_.tolist()
            predictions = model._classifier.predict_proba(model._vectorizer.transform([model._preprocessing.apply(req['message'])]))[0].tolist()
            prediction = np.argmax(predictions)
            thresholds = model._thresh

            visualizer.graph_tree(req['message'], model, prediction)
            classes = classes
            predictions = predictions
            chunks = visualizer.getNounChunks(req['message'])
            prediction = {'classes': classes,
                          'prediction' : predictions,
                          'threshold' : thresholds.tolist()}

            socketio.emit('model_interaction',
                        {'objects': chunks,
                         'needed_entites': answer_manager._state_machine._states[next_state]._entities,
                         'entities': entities,
                         'prediction': prediction},
                        namespace='/')
        
        

        if lastQuestion and lastQuestion._isMissingEntity:  
            socketio.emit('update_entities',
                        {'entities': entities},
                        namespace='/')

        tmp = answer.text
        answer.text = answer_manager._templates['default'][answer.templateId]['message'][answer.textIdx]
        socketio.emit('answer_interaction',
                        {'answer': answer_manager._answer_parser.parseMessage(session, answer, answer_manager._templates['default'])},
                        namespace='/')
        answer.text = tmp

        # Add the question to the current session
        #session.questions.append(question)

        entities = {entity['label'] : entity['text'] for entity in entities}

        # Retorno de resultados
        response = {'result': answer.text,
                    'transfer': session.transfer,
                    'endSession': answer.end_session,
                    'sleepMessage': writing_time,
                    'crmAttributes': [],
                    'isError': False,
                    'saveData': answer.saveData,
                    'valueField': answer.valueField,
                    'entities' : entities}
        logger.info(response)

    db.session.commit()

    # except Exception as err:
    #     # Escritura en el log de los errores generados y en el retorno de resultados
    #     error = err.args
    #     logger.error(error)
    #     db.session.rollback()
    #     response = {'isError': True,
    #                 'error': error,
    #                 'traceback' : traceback.format_exc()}


    return Response(json.dumps(response), mimetype='application/json')


if __name__ == '__main__':
    # Configuracion del registro de mensajes de seguimiento
    logging.basicConfig(filename = 'log/chatbot.log')
    logger = logging.getLogger('ai_app')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', '%d-%m-%Y %I:%M:%S %p')
    console_handler = logging.StreamHandler()

    ner = SubRed_NER('SUBRED_pos', 'normalization_models.pkl')
    answer_manager = AnswerManager(state_machine = StateMachine('tree_dialog_config.json',
                                                                'trained_intentions.pkl',
                                                                ner),
                                   templates_dir = 'templates/',
                                   time_per_word = 0)
    answer_manager.return_repeated = False
    
    visualizer = Visualizer(ner)

    with app.app_context():
        db.drop_all()
        db.create_all()
    socketio.run(app, host = sys.argv[1], port = sys.argv[2], debug=False)
    # app.run(host = '192.168.222.63', port = 8004)
