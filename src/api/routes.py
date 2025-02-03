# src/api/routes.py
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import cross_origin
import logging
import os
from collections import deque
import time
from werkzeug.utils import secure_filename
from core.error_handlers import TTSBaseError

def register_routes(app: Flask, tts_manager):
    @app.route("/", methods=["GET"])
    @cross_origin(origin='*')
    def index():
        return render_template("index.html")

    @app.route("/recover", methods=["GET"])
    @cross_origin(origin='*')
    def recover():
        tts_manager.reinitialize()
        return jsonify({"success": True})

    @app.route("/voices", methods=["GET"])
    @cross_origin(origin='*')
    def get_voices():
        return jsonify({
            "success": True,
            "voices": tts_manager.get_voices()
        })

    @app.route("/translate", methods=["POST"])
    @cross_origin(origin='*')
    def translate():
        data = request.get_json()
        target_language = data.get("target_language")
        text_to_synthesize = data.get("text")
        return tts_manager.translator.translate_text(text_to_synthesize, target_language)

    @app.route("/generate-realtime", methods=["POST"])
    @cross_origin(origin='*')
    def generate_realtime():
        try:
            data = request.get_json()
            text = data.get("text")
            voice_id = data.get("voice_id")
            session_id = data.get("session_id")
            target_language = data.get("target_language")

            if not text or not session_id:
                return jsonify({
                    "success": False,
                    "message": "Missing text or session_id",
                    "needs_audio": False
                })
                
            if session_id not in tts_manager.speech_queue:
                tts_manager.speech_queue[session_id] = deque()
                
            tts_manager.speech_queue[session_id].append(text)
            
            text_to_synthesize = tts_manager.speech_queue[session_id].popleft()
            
            if target_language is not None and target_language.strip() != '':
                text_to_synthesize = tts_manager.translator.translate_text(
                    text_to_synthesize, 
                    target_language
                )

            start_time = time.time()
            
            filename = tts_manager.synthesize_speech(
                text=text_to_synthesize,
                voice_id=voice_id,
                session_id=session_id
            )
            
            if not filename:
                return jsonify({
                    "success": False,
                    "message": "No new complete sentence to process",
                    "needs_audio": False
                })

            generation_time = time.time() - start_time
            audio_url = f"/audio/{filename}"

            return jsonify({
                "success": True,
                "file_path": audio_url,
                "message": "Audio generated successfully",
                "needs_audio": True,
                "timing_info": {
                    "total_generation_time": generation_time
                }
            })

        except TTSBaseError as e:
            error_msg = str(e)
            logging.error(f"TTS Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error generating voice: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500

    @app.route("/clear-session", methods=["POST"])
    @cross_origin(origin='*')
    def clear_session():
        try:
            data = request.get_json()
            session_id = data.get("session_id")
            
            if not session_id:
                raise ValueError("Missing session_id")
                
            tts_manager.clear_session(session_id)
            
            return jsonify({
                "success": True,
                "message": "Session cleared successfully"
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/audio/<path:filename>')
    def serve_audio(filename):
        try:
            filename = secure_filename(os.path.basename(filename))
            audio_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                tts_manager.config.directories.audio_output_dir
            )
            
            if not os.path.exists(os.path.join(audio_dir, filename)):
                return jsonify({
                    "success": False,
                    "error": "Audio file not found"
                }), 404
                
            return send_from_directory(
                audio_dir,
                filename,
                mimetype='audio/wav',
                as_attachment=True
            )
        
        except Exception as e:
            logging.error(f"Error serving audio file: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/health", methods=["GET"])
    @cross_origin(origin='*')
    def health_check():
        return jsonify({
            "status": "healthy",
            "available_voices": len(tts_manager.get_voices()),
            "timestamp": time.time()
        })