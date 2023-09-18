import logging

import dotenv
import gradio as gr
from tabs import chat_tab, writing_tab

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

import sys

# this file as project root
from pathlib import Path

sys.path.append(str(Path(__file__).parent))


BOT_NAME = "Jet"
demo = gr.TabbedInterface(
    [chat_tab, writing_tab],
    tab_names=["Chat", "Writing"],
    css="footer {visibility: hidden}",
    title=f"Chat with {BOT_NAME} (HJY AI bot)",
)

if __name__ == "__main__":
    demo.queue().launch(share=False)
