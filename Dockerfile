FROM milleinnovacion/millenlp:develop

ADD milledemosubred/ : /milledemosubred/

WORKDIR /milledemosubred

CMD [ "python", "ai_app.py", "192.168.222.63", "8004", "/nlu-voicebot_demo_subred"]
