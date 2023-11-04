import ast
import logging

import dotenv
import gradio as gr

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

from utils.chat_utils import (
    get_all_models,
    get_current_model,
    agenerate_new_text,
    get_chat_system_message,
)
from utils.persist_utils import persist


def create_chat_tab(tab_id=""):
    def model_parameters():
        with gr.Accordion("Parameters", open=False):
            model_status = gr.HTML()
            model_name = persist(
                gr.Dropdown(
                    value=get_current_model(),
                    choices=get_all_models(),
                    label="Current Model",
                    elem_id=tab_id + "chat-model-name",
                )
            )
            temperature = persist(
                gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=1.0,
                    step=0.1,
                    label="Temperature",
                    elem_id=tab_id + "chat-temperature",
                )
            )
            max_tokens = persist(
                gr.Slider(
                    minimum=0,
                    maximum=32_000,
                    value=0,
                    step=1,
                    label="Max Tokens (0 for inf)",
                    elem_id=tab_id + "chat-max-tokens",
                )
            )
            model_parameters_reset = gr.Button(
                value="Reset",
                variant="secondary",
                size="sm",
            )

            model_parameters_reset.click(
                lambda: [get_current_model(), 1.0, 0],
                [],
                [model_name, temperature, max_tokens],
            )

            def update_model_status(model_name, temperature, max_tokens):
                if max_tokens == 0:
                    max_tokens = "inf"

                model_status_update = f"""
                <small>
                <b>Current Model:</b> {model_name}
                <b>Temperature:</b> {temperature}
                <b>Max Tokens:</b> {max_tokens}
                </small>
                """
                return model_status_update

            gr.on(
                [
                    model_name.change,
                    temperature.change,
                    max_tokens.change,
                ],
                update_model_status,
                [model_name, temperature, max_tokens],
                [model_status],
            )
        return model_status, model_name, temperature, max_tokens, model_parameters_reset

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
                edit_discard = gr.Button(
                    value="Discard", variant="secondary", size="sm"
                )

        chatbot_status = gr.HTML()
        chatbot = persist(
            gr.Chatbot(
                height=500,
                container=False,
                bubble_full_width=False,
                latex_delimiters=[
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": "$", "right": "$", "display": False},
                ],
                elem_id=tab_id + "chat-chatbot",
            )
        )
        msg = persist(
            gr.Textbox(
                label="Your Message",
                autofocus=True,
                lines=2,
                placeholder="Hi!",
                elem_id=tab_id + "chat-msg",
            )
        )

        submit_btn = gr.Button(value="Submit", variant="primary")
        with gr.Row():
            retry_btn = gr.Button(value="Retry", variant="secondary", size="sm")
            undo_btn = gr.Button(value="Undo", variant="secondary", size="sm")
            clear_btn = gr.Button(value="Clear", variant="secondary", size="sm")

        with gr.Accordion("System Message", open=False):
            system_message = persist(
                gr.Textbox(
                    value=get_chat_system_message,
                    placeholder="You are ChatGPT.",
                    lines=4,
                    label="System Message",
                    show_label=False,
                    elem_id=tab_id + "chat-system-message",
                )
            )
            system_message_reset_btn = gr.Button(
                value="Reset",
                variant="secondary",
                size="sm",
            )
        with gr.Column():
            (
                model_status,
                model_name,
                temperature,
                max_tokens,
                model_parameters_reset,
            ) = model_parameters()

        def user(user_message, history):
            return "", history + [[user_message, None]]

        async def bot(
            history,
            system_message: str,
            model_name: str,
            temperature: float,
            max_tokens: int,
        ):
            async for history in agenerate_new_text(
                message=None,
                history=history,
                return_history=True,
                model_name=model_name,
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
            edit_accordion_update = gr.Accordion(visible=True)
            return repr(index), text, edit_accordion_update

        def update_history(index, content, history):
            # index maybe repr(index), to array
            if type(index) == str:
                index = ast.literal_eval(index)

            # update the history
            history[index[0]][index[1]] = content

            # update the layout
            edit_accordion_update = gr.Accordion(visible=False)

            return history, edit_accordion_update

        def discard_update_history():
            # update the layout
            edit_accordion_update = gr.Accordion(visible=False)

            return edit_accordion_update

        async def retry(history, system_message, model_name, temperature, max_tokens):
            if history:
                history[-1][1] = None
                yield history
                async for history in agenerate_new_text(
                    message=None,
                    history=history,
                    return_history=True,
                    system_message=system_message,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield history
            else:
                yield history

        def undo(history):
            last_human_message = None
            if history:
                last_human_message = history[-1][0]
                history = history[:-1]
            return history, last_human_message

        def clear():
            return (
                [],  # history
                "",  # message
                get_chat_system_message(),  # system_message
            )

        gr.on(
            [msg.submit, submit_btn.click],
            user,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        ).then(
            bot,
            inputs=[chatbot, system_message, model_name, temperature, max_tokens],
            outputs=[chatbot],
        )

        retry_btn.click(
            retry,
            [chatbot, system_message, model_name, temperature, max_tokens],
            [chatbot],
        )
        undo_btn.click(undo, [chatbot], [chatbot, msg])
        clear_btn.click(clear, [], [chatbot, msg, system_message])

        chatbot.select(
            load_message_to_edit_area,
            inputs=[],
            outputs=[edit_index, edit_content, edit_accordion],
        )
        edit_done.click(
            update_history,
            [edit_index, edit_content, chatbot],
            [chatbot, edit_accordion],
        )
        edit_discard.click(discard_update_history, [], [edit_accordion])

        system_message_reset_btn.click(get_chat_system_message, [], [system_message])

        model_status.change(lambda x: x, [model_status], [chatbot_status])

    return chat_tab
