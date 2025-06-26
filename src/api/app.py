import asyncio
import json
import logging
import os
from threading import Thread

import requests
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

# Import your existing bot
from src.core.bot import Bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for web requests

# Global variables
faq_bot = None
initialization_status = {"status": "initializing", "message": "Setting up bot..."}

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # Store securely in .env


def initialize_faq_bot():
    """Initialize the bot in a separate thread"""
    global faq_bot, initialization_status

    try:
        logger.info("Starting bot initialization...")
        initialization_status = {"status": "initializing", "message": "Loading bot..."}

        # Initialize the system with your existing code
        faq_bot = Bot(model_name="ISTA-DASLab/gemma-3-4b-it-GPTQ-4b-128g", temperature=0.2, streaming=True)


        initialization_status = {
            "status": "initializing",
            "message": "Loading vector store...",
        }

        # Setup from vector store
        success = faq_bot.setup_from_vectorstore()

        if success:
            initialization_status = {"status": "ready", "message": "bot ready!"}
            logger.info("bot initialized successfully!")
        else:
            initialization_status = {
                "status": "error",
                "message": "Failed to load vector store",
            }
            logger.error("Failed to initialize bot")

    except Exception as e:
        initialization_status = {
            "status": "error",
            "message": f"Initialization failed: {str(e)}",
        }
        logger.error(f"bot initialization error: {e}")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get the current status of the bot"""
    return jsonify(initialization_status)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat requests"""
    global faq_bot

    if not faq_bot or initialization_status["status"] != "ready":
        return jsonify(
            {
                "error": "bot not ready",
                "status": initialization_status["status"],
                "message": initialization_status["message"],
            }
        ), 503

    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400

        user_message = data["message"].strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        logger.info(f"Processing question: {user_message}")

        # Create a new event loop for this request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Get the answer using your existing system
            result = loop.run_until_complete(get_rag_response(user_message))

            return jsonify(
                {
                    "answer": result.get(
                        "answer", "I apologize, but I couldn't generate a response."
                    ),
                    "sources": result.get("sources", []),
                    "status": "success",
                }
            )

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return jsonify({"error": "Failed to process request", "message": str(e)}), 500


async def get_rag_response(question):
    """Get response from bot"""
    global faq_bot

    try:
        # Collect the full response
        full_answer = ""
        sources = []

        async for chunk in faq_bot.ask_question(question):
            if "answer" in chunk:
                full_answer += chunk["answer"]
            if "source_documents" in chunk and chunk["source_documents"]:
                # Extract unique sources
                for doc in chunk["source_documents"]:
                    source = doc.metadata.get("source", "Unknown")
                    if source not in sources:
                        sources.append(source)

        return {"answer": full_answer.strip(), "sources": sources}

    except Exception as e:
        logger.error(f"Error getting RAG response: {e}")
        return {
            "answer": "I apologize, but I encountered an error processing your query. Please try again.",
            "sources": [],
        }


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Handle streaming chat requests"""
    global faq_bot

    if not faq_bot or initialization_status["status"] != "ready":
        return jsonify(
            {
                "error": "bot not ready",
                "status": initialization_status["status"],
                "message": initialization_status["message"],
            }
        ), 503

    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400

        user_message = data["message"].strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        logger.info(f"Processing streaming question: {user_message}")

        def generate_response():
            """Generator function for streaming response"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def stream_rag_response():
                    async for chunk in faq_bot.ask_question(
                        user_message
                    ):
                        yield chunk

                # Run the async generator
                async_gen = stream_rag_response()

                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield f"data: {json.dumps(chunk)}\n\n"
                    except StopAsyncIteration:
                        break

            except Exception as e:
                logger.error(f"Error in streaming response: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                loop.close()

        return Response(
            generate_response(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except Exception as e:
        logger.error(f"Error setting up streaming: {e}")
        return jsonify({"error": "Failed to setup streaming", "message": str(e)}), 500


@app.route("/api/clear-memory", methods=["POST"])
def clear_memory():
    """Clear the conversation memory"""
    global faq_bot

    if not faq_bot:
        return jsonify({"error": "bot not ready"}), 503

    try:
        faq_bot.clear_memory()
        return jsonify({"message": "Memory cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        return jsonify({"error": "Failed to clear memory"}), 500


@app.route("/api/system-info", methods=["GET"])
def get_system_info():
    """Get system information"""
    global faq_bot

    if not faq_bot:
        return jsonify({"error": "bot not ready"}), 503

    try:
        info = faq_bot.get_system_info()
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return jsonify({"error": "Failed to get system info"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "rag_status": initialization_status["status"],
            "message": initialization_status["message"],
        }
    )


@app.route("/")
def index():
    """Serve a simple status page"""
    return f"""
    <html>
    <head><title>CMU Africa RAG API</title></head>
    <body>
        <h1>CMU Africa Student Assistant API</h1>
        <p>Status: {initialization_status["status"]}</p>
        <p>Message: {initialization_status["message"]}</p>
        <h2>Available Endpoints:</h2>
        <ul>
            <li>GET /api/status - Get system status</li>
            <li>POST /api/chat - Send chat message</li>
            <li>POST /api/chat/stream - Stream chat response</li>
            <li>POST /api/clear-memory - Clear conversation memory</li>
            <li>GET /api/system-info - Get system information</li>
            <li>GET /health - Health check</li>
        </ul>
    </body>
    </html>
    """


@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # Verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    # Respond to mentions
    if "event" in data:
        event = data["event"]
        if event.get("type") == "app_mention":
            user_text = event.get("text", "")
            channel_id = event.get("channel")

            # Strip bot mention (e.g., "<@U0123456> hello")
            cleaned_text = " ".join(
                word for word in user_text.split() if not word.startswith("<@")
            )

            # Get RAG response using your bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(get_rag_response(cleaned_text))
                answer = result.get("answer", "Sorry, I couldn't understand.")
            except Exception as e:
                logger.error(f"Slack bot error: {e}")
                answer = "Oops! Something went wrong processing your message."
            finally:
                loop.close()

            # Send response to Slack
            headers = {
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-type": "application/json",
            }
            payload = {
                "channel": channel_id,
                "text": answer,
            }
            requests.post(
                "https://slack.com/api/chat.postMessage", json=payload, headers=headers
            )

    return "", 200


if __name__ == "__main__":
    # Start bot initialization in background
    init_thread = Thread(target=initialize_faq_bot)
    init_thread.daemon = True
    init_thread.start()

    # Start Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
