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


@click.command()
@click.option(
    "--bot-name",
    default="Jet",
    help="The name of the bot.",
)
@click.option(
    "--num-chat-tabs",
    default=5,
    help="The number of chat tabs.",
)
@click.option(
    "--share/--no-share",
    default=False,
    help="Share on Gradio's public domain. Share links expire after 72 hours.",
)
@click.option(
    "--auth-username",
    default="test",
    help="Username for basic auth.",
)
@click.option(
    "--auth-password",
    default="test",
    help="Password for basic auth.",
)
def main(bot_name, num_chat_tabs, auth_username, auth_password, share):
    chat_tabs = [
        tabs.create_chat_tab(tab_id=f"chattab{i+1}") for i in range(num_chat_tabs)
    ]
    chat_tab_names = [f"Chat {i+1}" for i in range(num_chat_tabs)]
    writing_tab = tabs.create_writing_tab(tab_id="writingtab")
    speech_tab = tabs.create_speech_tab(tab_id="speechtab")
    demo = gr.TabbedInterface(
        [*chat_tabs, writing_tab, speech_tab],
        tab_names=[*chat_tab_names, "Writing", "Speech"],
        css="footer {visibility: hidden}",
        title=f"Chat with {bot_name} (HJY AI bot)",
        theme=gr.themes.Soft(),
    )
    demo.queue().launch(
        share=share, max_threads=10, auth=[(auth_username, auth_password)]
    )


if __name__ == "__main__":
    main()
