import pandas as pd
import numpy as np
import matplotlib as mpl
from graphviz import Digraph
from millenlp.pos import pos
import spacy
from scipy import sparse
from scipy.sparse import find
from sklearn.preprocessing import normalize
from millenlp.message import DummyMessage


class Visualizer():

    def __init__(self, ner):
        self.graphs = {}
        self.weights = None
        self.nlp = ner

    def traduce(self, text):
        if text == 'NUM':
            return 'Numero'
        elif text == 'VERB':
            return 'Verbo'
        elif text == 'AUX':
            return 'Auxiliar'
        elif text == 'NOUN':
            return 'Sustantivo'
        elif text == 'PROPN':
            return 'Sustantivo Propio'
        elif text == 'DET':
            return 'Determinante'
        elif text == 'ADJ':
            return 'Adjetivo'
        elif text == 'ADP':
            return 'Preposición'
        elif text == 'CCONJ':
            return 'Conjunción C'
        elif text == 'INTJ':
            return 'Interjección'
        elif text == 'SCONJ':
            return 'Conjunción S'
        elif text == 'obj':
            return 'objecto'
        elif text == 'obj':
            return 'objecto'
        elif text == 'obj':
            return 'objeto'
        return text


    def get_pos_children(self, token, i, root_name):

        for j, subtoken in enumerate(token.lefts):
            colorfactor = self.calculateColorFactor(subtoken)
            name = token.text + subtoken.text

            self.graphs['dot'].node(
                     name =  name,
                     label = subtoken.text + '\n' + self.traduce(subtoken.pos_),
                     style='filled',
                     fillcolor=self.colorFader(colorfactor))
            self.graphs['dot'].edge(root_name, name, color='blue')

            self.graphs['dot_complete'].node(
                     name =  name,
                     label = subtoken.text + '\n' + self.traduce(subtoken.pos_),
                     style='filled',
                     fillcolor=self.colorFader(colorfactor))
            self.graphs['dot_complete'] .edge(root_name, name, color='blue', label=subtoken.dep_)

            self.get_pos_children(subtoken, i+1, name)

        for j, subtoken in enumerate(token.rights):
            colorfactor = self.calculateColorFactor(subtoken)
            name = token.text + subtoken.text

            self.graphs['dot'].node(
                     name = name,
                     label = subtoken.text + '\n' + self.traduce(subtoken.pos_),
                     style = 'filled',
                     fillcolor = self.colorFader(colorfactor))
            self.graphs['dot'].edge(root_name, name)

            self.graphs['dot_complete'].node(
                     name =  name,
                     label = subtoken.text + '\n' + self.traduce(subtoken.pos_),
                     style='filled',
                     fillcolor=self.colorFader(colorfactor))
            self.graphs['dot_complete'].edge(root_name, name, color='blue', label=subtoken.dep_)

            self.get_pos_children(subtoken, i+1, name)


    def get_graph(self, token):

        for ent in self.entities:
            if token.text in ent['text']:
                return ent['subgraph']


    def graph_tree(self, msg, model, prediction):

        doc = self.nlp.ner(str(msg))

        self.weights = self.calculate_weights(msg, model, prediction)

        self.graphs['dot']  = Digraph(comment='POS Diagram', format='png')

        self.graphs['dot_complete'] = Digraph(comment='POS Diagram', format='png')

        root = [token for token in doc if token.head == token][0]

        colorfactor = self.calculateColorFactor(root)

        name = 'root'
        self.graphs['dot'].node(name=name, label=root.text + '\n' + self.traduce(root.pos_), style='filled', fillcolor=self.colorFader(colorfactor))
        self.graphs['dot_complete'].node(name=name, label=root.text + '\n' + self.traduce(root.pos_), style='filled', fillcolor=self.colorFader(colorfactor))

        self.get_pos_children(root, 1, name)

        self.graphs['dot_complete'].render('static/images/graph_complete')
        self.graphs['dot'].render('static/images/graph')

    def calculateColorFactor(self, text):
        if text.text in self.weights.index.values.tolist():
            return self.weights[text.text]
        elif text.lemma_ in self.weights.index.values.tolist():
            return self.weights[text.lemma_]
        else:
            return 0

    def colorFader(self, mix=0): #fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
        c1=np.array(mpl.colors.to_rgb('white'))
        c2=np.array(mpl.colors.to_rgb('#1f77b4'))
        return mpl.colors.to_hex((1-mix)*c1 + mix*c2)


    def calculate_weights(self, msg, model, prediction):
        features = model._vectorizer.transform([model._preprocessing.apply(msg)])

        row, col, values = find(sparse.csr_matrix(features.toarray()))
        feature_names = np.array(model._vectorizer._embedding.get_feature_names())

        words = [feature_names[index] for index in col]

        classes = model._classifier.classes_
        coef = normalize(model._classifier.coef_, axis=1)

        models_coeffs = model._classifier.coef_.transpose()


        heatmap = list()
        if models_coeffs.shape[1] > 1:
            for index in col:
                heatmap += [models_coeffs[index].tolist()]
            table = pd.DataFrame(heatmap, index = words, columns = classes)
        else:
            for index in col:
                heatmap += [models_coeffs[index].tolist() + models_coeffs[index].tolist()]
            table = pd.DataFrame(heatmap, index = words, columns = uniqueclass)


        weights = table[classes[prediction]].values

        if len(weights.tolist()) > 1:
            weights = (weights - min(weights)) / (max(weights)  - min(weights))
        elif len(weights.tolist()) == 1:
            weights = weights / max(weights)

        table[classes[prediction]] = weights

        return table[classes[prediction]]

    def getEntities(self, msg):
        message = DummyMessage(msg)
        message = self.nlp.predict(message)
        ents = []
        for ent in message._entities:
            ents += [{'label' : ent.name, 'text' : ent.value} ]
        return ents

    def getNounChunks(self, msg):

        doc = self.nlp.ner(msg)

        chunks = []
        for chunk in doc.noun_chunks:
            chunks.append([chunk.text, chunk.root.text, chunk.root.dep_, chunk.root.head.text])

        return chunks
