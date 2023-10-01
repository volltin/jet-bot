import logging
import sys
from pathlib import Path

import click
import dotenv
import gradio as gr
from tabs import chat_tab, speech_tab, writing_tab

sys.path.append(str(Path(__file__).parent))
dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_NAME = "Jet"
demo = gr.TabbedInterface(
    [chat_tab, writing_tab, speech_tab],
    tab_names=["Chat", "Writing", "Speech"],
    css="footer {visibility: hidden}",
    title=f"Chat with {BOT_NAME} (HJY AI bot)",
    theme=gr.themes.Soft(),
)


@click.command()
@click.option(
    "--share/--no-share",
    default=False,
    help="Share on Gradio's public domain. Share links expire after 72 hours.",
)
def main(share):
    demo.queue().launch(share=share)


if __name__ == "__main__":
    main()
