import sys
import logging
from pathlib import Path

import tabs
import click
import dotenv
import gradio as gr

sys.path.append(str(Path(__file__).parent))
dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_NAME = "Jet"
chat_tab = tabs.create_chat_tab(tab_id="chattab-1")
writing_tab = tabs.create_writing_tab(tab_id="writingtab")
speech_tab = tabs.create_speech_tab(tab_id="speechtab")
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
    demo.queue(concurrency_count=4).launch(share=share, auth=[("test", "test")])


if __name__ == "__main__":
    main()
