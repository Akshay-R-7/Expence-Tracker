import hashlib
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from ask import ask
from voice import transcribe

AUDIO_PATH = Path("receipts/_question.wav")

st.title("Ask about your expenses")

# Streamlit reruns this script on every interaction, so normal variables are
# forgotten each time. st.session_state survives reruns: that's the chat's memory.
if "messages" not in st.session_state:
    st.session_state.messages = []


def speak_button(text, key):
    """A small button that reads the text aloud using the browser's built-in voice."""
    components.html(
        f"""
        <button id="speak" style="padding:4px 10px;border-radius:6px;border:1px solid #ccc;
                background:white;cursor:pointer;font-size:14px;">Read aloud</button>
        <script>
          document.getElementById("speak").onclick = () => {{
            const utterance = new SpeechSynthesisUtterance({json.dumps(text)});
            utterance.lang = "en-US";
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
          }};
        </script>
        """,
        height=40,
    )


def show_message(message, index):
    """Draw one chat bubble, with a read-aloud button and the SQL behind the answer."""
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message["role"] == "assistant":
            speak_button(message["content"], key=index)
        if message.get("sql"):
            with st.expander("How I found this"):
                st.code(message["sql"], language="sql")
                st.write("Database result:", message["rows"])


with st.sidebar:
    audio = st.audio_input("Ask with your voice")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# Redraw the whole conversation so far
for index, message in enumerate(st.session_state.messages):
    show_message(message, index)

question = st.chat_input("e.g. How much did I spend at Kaufland?")

# A recording stays in the audio widget across reruns, so remember which one
# was already answered (by its fingerprint) and only handle new recordings.
if audio is not None:
    audio_bytes = audio.getvalue()
    audio_id = hashlib.sha256(audio_bytes).hexdigest()
    if st.session_state.get("last_audio_id") != audio_id:
        st.session_state.last_audio_id = audio_id
        AUDIO_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIO_PATH.write_bytes(audio_bytes)
        try:
            with st.spinner("Listening..."):
                spoken_text, language = transcribe(str(AUDIO_PATH))
        except RuntimeError:
            spoken_text = None
            st.error(
                "Voice recognition failed, probably because the computer ran out of memory. "
                "Close some programs and try again, or type your question instead."
            )
        if spoken_text:
            question = spoken_text
        elif spoken_text == "":
            st.warning("I couldn't hear any words in that recording. Please try again.")

if question:
    user_message = {"role": "user", "content": question}
    st.session_state.messages.append(user_message)
    show_message(user_message, len(st.session_state.messages) - 1)

    with st.spinner("Thinking..."):
        result = ask(question)

    assistant_message = {
        "role": "assistant",
        "content": result["answer"],
        "sql": result["sql"],
        "rows": result["rows"],
    }
    st.session_state.messages.append(assistant_message)
    show_message(assistant_message, len(st.session_state.messages) - 1)