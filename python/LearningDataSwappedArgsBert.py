'''
Changed model to use BERT sentence embeddings
'''

import Util
from collections import Counter

from HyperParameters import name_embedding_size, type_embedding_size

import tensorflow as tf
import requests
import numpy as np


class CodePiece(object):
    def __init__(self, callee, arguments, src):
        self.callee = callee
        self.arguments = arguments
        self.src = src

    def to_message(self):
        return str(self.src) + " | " + str(self.callee) + " | " + str(self.arguments)


class LearningData(object):

    def is_known_type(self, t):
        return t == "boolean" or t == "number" or t == "object" or t == "regex" or t == "string"

    def resetStats(self):
        self.stats = {"calls": 0, "calls_with_two_args": 0, "calls_with_known_names": 0,
                      "calls_with_known_base_object": 0, "calls_with_known_types": 0,
                      "calls_with_both_known_types": 0,
                      "calls_with_known_parameters": 0}

    def pre_scan(self, first_data_paths, second_data_paths=[]):
        print("Stats on first data")
        self.gather_stats(first_data_paths)

        if second_data_paths != []:
            print("Stats on second data")
            self.gather_stats(second_data_paths)

    def gather_stats(self, data_paths):
        callee_to_freq = Counter()
        argument_to_freq = Counter()

        for example in Util.DataReader(data_paths):
            call = example['data']
            callee_to_freq[call["callee"]] += 1
            for argument in call["arguments"]:
                argument_to_freq[argument] += 1

        print("Unique callees        : " + str(len(callee_to_freq)))
        print("  " + "\n  ".join(str(x)
                                 for x in callee_to_freq.most_common(10)))
        Util.analyze_histograms(callee_to_freq)
        print("Unique arguments      : " + str(len(argument_to_freq)))
        print("  " + "\n  ".join(str(x)
                                 for x in argument_to_freq.most_common(10)))
        Util.analyze_histograms(argument_to_freq)

    def code_to_xy_pairs(self, gen_negatives, code, xs, ys, name_to_vector, type_to_vector, node_type_to_vector, calls=None):
        call = code['data']
        bug = code['bug']

        arguments = call["arguments"]
        self.stats["calls"] += 1
        if len(arguments) != 2:
            return
        self.stats["calls_with_two_args"] += 1

        # mandatory information: callee and argument names
        callee_string = call["callee"]
        argument_strings = call["arguments"]
        if not (callee_string in name_to_vector):
            return
        for argument_string in argument_strings:
            if not (argument_string in name_to_vector):
                return
        self.stats["calls_with_known_names"] += 1

        # optional information: base object, argument types, etc.
        base_string = call["base"]
        # base_vector = name_to_vector.get(base_string, [0]*name_embedding_size)
        if base_string in name_to_vector:
            self.stats["calls_with_known_base_object"] += 1

        argument_type_strings = call["argumentTypes"]
        # argument0_type_vector = type_to_vector.get(
        #     argument_type_strings[0], [0]*type_embedding_size)
        # argument1_type_vector = type_to_vector.get(
        #     argument_type_strings[1], [0]*type_embedding_size)
        if (self.is_known_type(argument_type_strings[0]) or self.is_known_type(argument_type_strings[1])):
            self.stats["calls_with_known_types"] += 1
        if (self.is_known_type(argument_type_strings[0]) and self.is_known_type(argument_type_strings[1])):
            self.stats["calls_with_both_known_types"] += 1

        parameter_strings = call["parameters"]
        # parameter0_vector = name_to_vector.get(
        #     parameter_strings[0], [0]*name_embedding_size)
        # parameter1_vector = name_to_vector.get(
        #     parameter_strings[1], [0]*name_embedding_size)
        if (parameter_strings[0] in name_to_vector or parameter_strings[1] in name_to_vector):
            self.stats["calls_with_known_parameters"] += 1

        sentence = callee_string + ' '
        if argument_type_strings[0]:
            sentence += argument_type_strings[0] + ' '
        sentence += argument_strings[0] + ' '
        if argument_type_strings[1]:
            sentence += argument_type_strings[1] + ' '
        sentence += argument_strings[1]
        # Send this off to the docker service to get the embedding back
        url = 'http://localhost:5000/sentenceEmbedding'
        myobj = {'sentence': sentence}
        sentence_embedding = requests.post(url, json=myobj).json()

        # for all xy-pairs: y value = probability that incorrect
        # x_keep = callee_vector + argument0_vector + argument1_vector
        # x_keep += base_vector + argument0_type_vector + argument1_type_vector
        # x_keep += parameter0_vector + parameter1_vector  # + file_name_vector

        x_keep = sentence_embedding
        if bug:
            y_keep = [1]
        else:
            y_keep = [0]
        xs.append(x_keep)
        ys.append(y_keep)
        if calls != None:
            calls.append(
                CodePiece(callee_string, argument_strings, call["src"]))

    def anomaly_score(self, y_prediction_orig, y_prediction_changed):
        # higher means more likely to be anomaly in current code
        return y_prediction_orig - y_prediction_changed

    def normal_score(self, y_prediction_orig, y_prediction_changed):
        # higher means more likely to be correct in current code
        return y_prediction_changed - y_prediction_orig
