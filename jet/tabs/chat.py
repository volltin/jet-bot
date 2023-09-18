import ast
import logging

import dotenv
import gradio as gr

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

from utils.chat_utils import agenerate_new_text, get_chat_system_message


def model_parameters():
    with gr.Accordion("Parameters", open=False):
        temperature = gr.Slider(
            minimum=0.0,
            maximum=2.0,
            value=1.0,
            step=0.1,
            label="Temperature",
        )
        max_tokens = gr.Slider(
            minimum=0,
            maximum=32_000,
            value=0,
            step=1,
            label="Max Tokens (0 for inf)",
        )
    return temperature, max_tokens


with gr.Blocks() as chat_tab:
    with gr.Accordion("Inspect & Edit", open=True, visible=False) as edit_accordion:
        edit_index = gr.Textbox(
            value="",
            interactive=False,
            label="Message Index",
            visible=False,
        )
        edit_content = gr.Code(
            lines=2,
            language="markdown",
            label="Message Content",
        )
        with gr.Row():
            edit_done = gr.Button(value="Update", variant="primary", size="sm")
            edit_discard = gr.Button(value="Discard", variant="stop", size="sm")

    chatbot = gr.Chatbot(
        height=500,
        container=False,
        bubble_full_width=False,
        latex_delimiters=[
            {"left": "$$", "right": "$$", "display": True},
            {"left": "$", "right": "$", "display": False},
        ],
    )
    msg = gr.Textbox(label="Your Message", autofocus=True, lines=2, placeholder="Hi!")
    with gr.Row():
        # TODO: add retry and undo
        clear = gr.ClearButton([msg, chatbot])

    with gr.Accordion("System Message", open=False):
        system_message = gr.Textbox(
            placeholder="You are ChatGPT.",
            value=get_chat_system_message,
            lines=4,
            label="System Message",
            show_label=False,
        )
    with gr.Column():
        temperature, max_tokens = model_parameters()

    def user(user_message, history):
        return "", history + [[user_message, None]]

    async def bot(history, system_message: str, temperature: float, max_tokens: int):
        async for history in agenerate_new_text(
            message=None,
            history=history,
            return_history=True,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield history

    def load_message_to_edit_area(event: gr.SelectData):
        logging.info("Select Event: value: %r index: %r", event.value, event.index)
        text = event.value
        index = event.index  # [msg_id, user/ai]

        # update layout
        edit_accordion_update = gr.update(visible=True)
        return repr(index), text, edit_accordion_update

    def update_history(index, content, history):
        # index maybe repr(index), to array
        if type(index) == str:
            index = ast.literal_eval(index)

        # update the history
        history[index[0]][index[1]] = content

        # update the layout
        edit_accordion_update = gr.update(visible=False)

        return history, edit_accordion_update

    def discard_update_history():
        # update the layout
        edit_accordion_update = gr.update(visible=False)

        return edit_accordion_update

    msg.submit(user, [msg, chatbot], [msg, chatbot]).then(
        bot, [chatbot, system_message, temperature, max_tokens], [chatbot]
    )
    chatbot.select(
        load_message_to_edit_area,
        inputs=[],
        outputs=[edit_index, edit_content, edit_accordion],
    )
    edit_done.click(
        update_history, [edit_index, edit_content, chatbot], [chatbot, edit_accordion]
    )
    edit_discard.click(discard_update_history, [], [edit_accordion])