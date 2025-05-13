import streamlit as st
import hashlib
from firebase_admin import firestore

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(db):
    st.markdown("### Login")

    # Role picker
    selected_role = st.radio("Login as", ["Researcher", "Reviewer"], horizontal=True)
    requested_role = "reviewer" if selected_role == "Reviewer" else "user"

    with st.form("login_form"):
        email = st.text_input("Work Email").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if not submitted:
        st.stop()

    if not email or not password:
        st.error("Please enter both email and password.")
        st.stop()

    try:
        user_ref = db.collection("users").document(email)
        doc = user_ref.get()
    except Exception as e:
        st.error(f"Failed to fetch user credentials: {e}")
        st.stop()

    if not hasattr(doc, "exists") or not doc.exists:
        st.error("No account found for this email. Please contact the admin.")
        st.stop()

    user_data = doc.to_dict()

    if not user_data.get("authorized", False):
        st.error("This email is not yet authorized to access the app.")
        st.stop()

    # Ensure roles list exists
    roles = user_data.get("roles", ["user"])  # fallback to single-role
    if requested_role not in roles:
        st.error(f"You are not authorized to log in as a {requested_role}.")
        st.stop()

    # First-time password setup
    if not user_data.get("password"):
        user_ref.update({"password": hash_password(password)})
        st.info("Password set. Please click the login button to continue.")
        st.session_state.authenticated_user = email
        st.session_state.user_role = requested_role
        st.stop()

    if user_data["password"] != hash_password(password):
        st.error("Incorrect password.")
        st.stop()

    # ✅ Authentication successful
    st.session_state.authenticated_user = email
    st.session_state.user_role = requested_role
    st.info("User authenticated. Please click the login button to continue.")
    st.stop()
