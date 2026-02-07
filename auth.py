import streamlit as st

# Hardcoded users for prototype
USERS = {
    "owner": {
        "password": "admin",
        "role": "Owner",
        "name": "Mr. Boss"
    },
    "attendee1": {
        "password": "user1",
        "role": "Attendee",
        "name": "John Doe"
    },
    "attendee2": {
        "password": "user2",
        "role": "Attendee",
        "name": "Jane Smith"
    },
    "attendee3": {
        "password": "user3",
        "role": "Attendee",
        "name": "Bob Jones"
    }
}

def login_user(username, password):
    """Verify credentials and return user info if valid."""
    if username in USERS:
        if USERS[username]["password"] == password:
            return USERS[username]
    return None

def logout_user():
    """Clear session state for logout."""
    if 'user' in st.session_state:
        del st.session_state['user']
    if 'role' in st.session_state:
        del st.session_state['role']
