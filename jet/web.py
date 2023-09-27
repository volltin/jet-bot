import logging
import sys
from pathlib import Path

import dotenv
import gradio as gr
from tabs import chat_tab, writing_tab

sys.path.append(str(Path(__file__).parent))
dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_NAME = "Jet"
demo = gr.TabbedInterface(
    [chat_tab, writing_tab],
    tab_names=["Chat", "Writing"],
    css="footer {visibility: hidden}",
    title=f"Chat with {BOT_NAME} (HJY AI bot)",
    theme=gr.themes.Soft(),
)

if __name__ == "__main__":
    demo.queue().launch(share=False)
