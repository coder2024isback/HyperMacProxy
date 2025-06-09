from flask import request, render_template_string
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPEN_AI_API_KEY)

DOMAIN = "claude.ai"

MAX_HISTORY = 10
selected_model = "gpt-4o"
messages = []

system_prompts = [
    {"role": "system", "content": (
        "Only respond using plain ASCII characters. No emojis, special characters, or advanced HTML formatting."
    )},
    {"role": "system", "content": (
        "Responses will be shown in a vintage browser inside a raw HTML page. Do not include <body> or <html> tags. "
        "Wrap any code in <pre><code>...</code></pre>, and use <b> for bold, <i> for italic, <ul>/<ol> for lists, and <a> for links."
    )}
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Claude</title></head>
<body>
    <form method="post" action="/">
        <select name="model">
            <option value="gpt-4o" {{ 'selected' if selected_model == 'gpt-4o' else '' }}>GPT-4o</option>
            <option value="gpt-4-turbo" {{ 'selected' if selected_model == 'gpt-4-turbo' else '' }}>GPT-4</option>
            <option value="gpt-3.5-turbo" {{ 'selected' if selected_model == 'gpt-3.5-turbo' else '' }}>GPT-3.5</option>
        </select>
        <input type="text" name="command" size="63" required autocomplete="off">
        <input type="submit" value="Submit">
    </form>
    <div id="chat">
        <p>{{ output|safe }}</p>
    </div>
</body>
</html>
"""

def handle_request(req):
    if req.method == 'POST':
        return chat_interface(req), 200
    elif req.method == 'GET':
        return chat_interface(req), 200
    return "Not Found", 404

def chat_interface(req):
    global messages, selected_model
    output = ""

    if req.method == 'POST':
        user_input = req.form['command']
        model = req.form.get('model', 'gpt-4o')
        selected_model = model

        messages.append({"role": "user", "content": user_input})
        all_messages = system_prompts + messages[-MAX_HISTORY:]

        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=all_messages
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"<pre><code>Error: {str(e)}</code></pre>"

        messages.append({"role": "system", "content": reply})

    # Render chat history
    for msg in reversed(messages[-MAX_HISTORY:]):
        role = "User" if msg["role"] == "user" else "Claude"
        output += f"<b>{role}:</b> {msg['content']}<br>"

    return render_template_string(HTML_TEMPLATE, output=output, selected_model=selected_model)
