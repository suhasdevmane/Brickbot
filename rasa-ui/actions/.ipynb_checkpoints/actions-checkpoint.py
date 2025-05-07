from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import subprocess
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import csv

# actions.py
from custom_actions.action_get_temperature import ActionGetTemperature
from custom_actions.action_give_report import ActionGiveReport
from custom_actions.action_asked_entities import ActionAskedEntities


class MyCustomActions:
    def __init__(self):
        self.action_get_temperature = ActionGetTemperature()
        self.action_give_report = ActionGiveReport()
        self.action_asked_entities = ActionAskedEntities()