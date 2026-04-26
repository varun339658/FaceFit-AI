/**
 * VoiceInput.jsx — Voice Input via Web Speech API (browser-native)
 * Feature 5: Mic button in React chat — transcribes speech to text
 * No backend needed — uses browser's SpeechRecognition API
 */
import { useState, useRef, useEffect } from "react";

export default function VoiceInput({ onTranscript, disabled }) {
  const [listening, setListening]   = useState(false);
  const [supported, setSupported]   = useState(false);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSupported(true);
      const rec = new SpeechRecognition();
      rec.continuous      = false;
      rec.interimResults  = true;
      rec.lang            = "en-IN";
      rec.maxAlternatives = 1;

      rec.onresult = (e) => {
        let interim = "", final = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) final += t;
          else interim += t;
        }
        const current = (final || interim).trim();
        setTranscript(current);
        if (final) {
          onTranscript?.(final.trim());
          setListening(false);
          setTranscript("");
        }
      };

      rec.onerror = (e) => {
        console.warn("Speech error:", e.error);
        setListening(false);
        setTranscript("");
        if (e.error === "no-speech") {
          // silently ignore
        }
      };

      rec.onend = () => {
        setListening(false);
      };

      recognitionRef.current = rec;
    }
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    if (listening) {
      recognitionRef.current.stop();
      setListening(false);
      setTranscript("");
    } else {
      setTranscript("");
      recognitionRef.current.start();
      setListening(true);
    }
  };

  if (!supported) return null;

  return (
    <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
      <button
        onClick={toggleListening}
        disabled={disabled}
        title={listening ? "Stop recording" : "Speak your question"}
        style={{
          width: 42, height: 42,
          border: `1.5px solid ${listening ? "#c8a55a" : "#ddd3c2"}`,
          background: listening
            ? "linear-gradient(135deg,rgba(200,165,90,.2),rgba(200,165,90,.08))"
            : "#fff",
          borderRadius: "50%",
          cursor: disabled ? "not-allowed" : "pointer",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
          transition: "all .2s",
          boxShadow: listening ? "0 0 0 4px rgba(200,165,90,.15)" : "none",
          animation: listening ? "micPulse 1.2s ease infinite" : "none",
          opacity: disabled ? 0.4 : 1,
        }}
      >
        {/* Mic SVG icon */}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke={listening ? "#c8a55a" : "#8a7a6a"} strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
      </button>

      {/* Live transcript preview bubble */}
      {listening && transcript && (
        <div style={{
          position: "absolute", bottom: "calc(100% + 8px)", right: 0,
          background: "#1a0f00", color: "#c8a55a",
          padding: "7px 12px", borderRadius: "10px 10px 2px 10px",
          fontSize: 12, maxWidth: 220, whiteSpace: "normal",
          boxShadow: "0 4px 16px rgba(0,0,0,.2)",
          lineHeight: 1.5, fontStyle: "italic",
          animation: "fadeUp .15s ease",
          zIndex: 100,
        }}>
          "{transcript}"
        </div>
      )}

      {/* Listening indicator */}
      {listening && !transcript && (
        <div style={{
          position: "absolute", bottom: "calc(100% + 8px)", right: 0,
          background: "#1a0f00", padding: "7px 14px",
          borderRadius: "10px 10px 2px 10px",
          display: "flex", alignItems: "center", gap: 6,
          boxShadow: "0 4px 16px rgba(0,0,0,.2)",
          zIndex: 100,
        }}>
          {[0,.2,.4].map((d, i) => (
            <span key={i} style={{
              width: 5, height: 5, borderRadius: "50%",
              background: "#c8a55a", display: "inline-block",
              animation: `blink 1s ease ${d}s infinite`,
            }}/>
          ))}
          <span style={{ fontSize: 10, color: "#c8a55a", letterSpacing: ".08em" }}>Listening...</span>
        </div>
      )}
    </div>
  );
}