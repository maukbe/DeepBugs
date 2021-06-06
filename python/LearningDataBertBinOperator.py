'''
Created on Nov 9, 2017

@author: Michael Pradel, Sabine Zach
'''

import Util
import random
import requests

from HyperParameters import type_embedding_size, node_type_embedding_size

ALL_OPERATORS = ['==', '===', '!=', '!==',
                 '&', '&&', '|', '||', '<', '<=', '<', '>=']


class CodePiece(object):
    def __init__(self, left, right, op, src):
        self.left = left
        self.right = right
        self.op = op
        self.src = src

    def to_message(self):
        return str(self.src) + " | " + str(self.left) + " | " + str(self.op) + " | " + str(self.right)


class LearningData(object):
    def __init__(self):
        self.all_operators = []
        self.stats = {}

    def resetStats(self):
        self.stats = {}

    def pre_scan(self, first_data_paths, second_data_paths=[]):
        pass

    def code_to_xy_pairs(self, gen_negatives, code_piece, xs, ys, name_to_vector, type_to_vector, node_type_to_vector, code_pieces):
        bin_op = code_piece['data']
        bug = code_piece['bug']

        left = bin_op["left"]
        right = bin_op["right"]
        operator = bin_op["op"]
        left_type = bin_op["leftType"]
        right_type = bin_op["rightType"]
        parent = bin_op["parent"]
        grand_parent = bin_op["grandParent"]
        src = bin_op["src"]
        if not (left in name_to_vector):
            return
        if not (right in name_to_vector):
            return

        left_vector = name_to_vector[left]
        right_vector = name_to_vector[right]
        operator_vector = [0] * len(ALL_OPERATORS)
        operator_vector[ALL_OPERATORS.index(operator)] = 1
        left_type_vector = type_to_vector.get(
            left_type, [0]*type_embedding_size)
        right_type_vector = type_to_vector.get(
            right_type, [0]*type_embedding_size)
        parent_vector = node_type_to_vector[parent]
        grand_parent_vector = node_type_to_vector[grand_parent]

        # for all xy-pairs: y value = probability that incorrect
        x = left_vector + right_vector + operator_vector + \
            left_type_vector + right_type_vector + parent_vector + grand_parent_vector

        sentence = left + ' ' + right + ' ' + operator + ' ' + \
            left_type + ' ' + right_type + ' ' + parent + ' ' + grand_parent

        url = 'http://localhost:5000/sentenceEmbedding'
        myobj = {'sentence': sentence}
        sentence_embedding = requests.post(url, json=myobj).json()
        xs.append(sentence_embedding)

        if bug:
            y_correct = [1]
        else:
            y_correct = [0]
        ys.append(y_correct)

        # code_pieces.append(CodePiece(left, right, operator, src))

    def anomaly_score(self, y_prediction_orig, y_prediction_changed):
        return y_prediction_orig

    def normal_score(self, y_prediction_orig, y_prediction_changed):
        return y_prediction_changed
