import firebase_admin
from firebase_admin import credentials, firestore
import json
import streamlit as st

def init_firestore():
    if not firebase_admin._apps:
        firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(firebase_json)
        firebase_admin.initialize_app(cred)
    return firestore.client()
