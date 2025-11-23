from __future__ import annotations

import json
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from backend.db.models import PersonaRead
from backend.realtime import create_realtime_session_config


class RealtimePage:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._session_key = "realtime_session_config"

    def render(self, persona: Optional[PersonaRead]) -> None:
        if not persona:
            st.info("Select a persona to use the realtime assistant.")
            return

        st.subheader("Realtime Voice Assistant")
        st.caption(
            "Low-latency persona-aware calls powered by OpenAI Realtime. "
            "Runs locally in your browser; nothing is uploaded beyond the live session."
        )

        config = st.session_state.get(self._session_key)
        if not config:
            try:
                config = create_realtime_session_config(
                    persona=persona,
                    user_id=self.user_id,
                )
                st.session_state[self._session_key] = config
            except Exception as exc:
                st.error(f"Unable to create realtime session: {exc}")
                return

        refresh = st.button("Refresh token", help="Generate a new realtime session token")
        if refresh:
            st.session_state.pop(self._session_key, None)
            st.rerun()

        st.success("Realtime session ready. Click Connect when prompted below.")
        if config.get("expires_at"):
            st.caption(f"Token expires: {config['expires_at']}")

        components.html(
            self._build_client_html(config),
            height=520,
        )

    def _build_client_html(self, config: dict) -> str:
        token = json.dumps(config["token"])
        model = json.dumps(config.get("model", "gpt-4o-realtime-preview"))
        voice = json.dumps(config.get("voice", "synthetic"))
        html = f"""
<style>
#rt-container {{
  font-family: 'Inter', sans-serif;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 16px;
  background: #111;
  color: #f3f3f3;
}}
#rt-buttons {{
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}}
#rt-buttons button {{
  flex: 1;
  border: none;
  border-radius: 8px;
  padding: 10px;
  font-size: 16px;
  cursor: pointer;
}}
#rt-connect {{
  background: #0c8ce9;
  color: #fff;
}}
#rt-stop {{
  background: #353535;
  color: #fff;
}}
#rt-status {{
  margin-top: 6px;
  font-size: 14px;
  opacity: 0.8;
}}
#rt-log {{
  margin-top: 16px;
  background: #1b1b1b;
  border-radius: 10px;
  padding: 12px;
  height: 220px;
  overflow-y: auto;
  font-size: 14px;
}}
</style>
<div id="rt-container">
  <div id="rt-buttons">
    <button id="rt-connect">🎙️ Connect</button>
    <button id="rt-stop" disabled>Stop</button>
  </div>
  <div id="rt-status">Microphone is idle.</div>
  <audio id="rt-audio" autoplay></audio>
  <div id="rt-log"></div>
</div>
<script>
(function() {{
  const TOKEN = {token};
  const MODEL = {model};
  const VOICE = {voice};
  const logEl = document.getElementById('rt-log');
  const statusEl = document.getElementById('rt-status');
  const connectBtn = document.getElementById('rt-connect');
  const stopBtn = document.getElementById('rt-stop');
  const audioEl = document.getElementById('rt-audio');
  let pc = null;
  let localStream = null;

  const log = (msg) => {{
    const entry = document.createElement('div');
    entry.textContent = msg;
    logEl.appendChild(entry);
    logEl.scrollTop = logEl.scrollHeight;
  }};

  async function connect() {{
    if (pc) return;
    try {{
      const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
      localStream = stream;
      pc = new RTCPeerConnection();
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
      pc.ontrack = (event) => {{
        audioEl.srcObject = event.streams[0];
      }};
      const dataChannel = pc.createDataChannel("oai-events");
      dataChannel.onmessage = (event) => {{
        try {{
          const payload = JSON.parse(event.data);
          if (payload.type === "transcript") {{
            log("Assistant: " + payload.text);
          }}
        }} catch (err) {{
          // ignore parse errors
        }}
      }};
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const response = await fetch(
        "https://api.openai.com/v1/realtime?model=" + MODEL,
        {{
          method: "POST",
          headers: {{
            "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/sdp",
            "OpenAI-Beta": "realtime=v1",
          }},
          body: offer.sdp,
        }}
      );
      if (!response.ok) {{
        throw new Error("Realtime API rejected offer");
      }}
      const answer = await response.text();
      await pc.setRemoteDescription({{ type: "answer", sdp: answer }});
      statusEl.textContent = "Connected to realtime model (" + MODEL + ", voice " + VOICE + ")";
      connectBtn.disabled = true;
      stopBtn.disabled = false;
      log("Realtime session connected.");
    }} catch (error) {{
      console.error(error);
      log("Failed to start: " + error.message);
      await stop();
    }}
  }}

  async function stop() {{
    if (pc) {{
      pc.getSenders().forEach((sender) => sender.track && sender.track.stop());
      pc.close();
    }}
    if (localStream) {{
      localStream.getTracks().forEach(track => track.stop());
    }}
    pc = null;
    localStream = null;
    connectBtn.disabled = false;
    stopBtn.disabled = true;
    statusEl.textContent = "Disconnected.";
    log("Realtime session closed.");
  }}

  connectBtn.addEventListener('click', () => connect());
  stopBtn.addEventListener('click', () => stop());
  window.addEventListener('beforeunload', () => stop());
}})();
</script>
"""
        return html

