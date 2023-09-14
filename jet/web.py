# -*- coding: utf-8 -*-
import ast
import asyncio
import datetime
import difflib
import logging
import os
import re

import dotenv
import gradio as gr
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chat_models import AzureChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from prompts import (
    CHAT_SYSTEM_MESSAGE,
    WRITING_CORRECT_SYSTEM_MESSAGE,
    WRITING_REFINE_SYSTEM_MESSAGE,
)

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)


chat = AzureChatOpenAI(deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"))
BOT_NAME = "Jet"


def get_chat_system_message():
    # tz: Beijing, format %Y-%m-%d %H:%M:%S
    ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    return CHAT_SYSTEM_MESSAGE.format(time=ts)


def make_langchain_history(gradio_history, message=None, system_message=None):
    """
    Make a history in the format of langchain from gradio history
    """
    history_langchain_format = []

    # append the system message
    if system_message:
        history_langchain_format.append(SystemMessage(content=system_message))

    # append the history
    # gradio_history: List[Tuple[Optional[str], Optional[str]]]
    # e.g. [(None, 'human message'), ('ai message', None)]
    for human, ai in gradio_history:
        if human:
            history_langchain_format.append(HumanMessage(content=human))
        if ai:
            history_langchain_format.append(AIMessage(content=ai))

    # append the current message
    if message:
        history_langchain_format.append(HumanMessage(content=message))

    return history_langchain_format


def generate_new_messages(message, history, system_message=None):
    history_langchain_format = make_langchain_history(
        gradio_history=history, message=message, system_message=system_message
    )

    # log the actual history
    logging.info("History: %r", history_langchain_format)

    response = chat(history_langchain_format)

    new_messages = [response]
    return new_messages


async def agenerate_new_text(
    message,
    history,
    return_history=False,
    system_message=None,
    temperature=1.0,
    max_tokens=0,
):
    messages = make_langchain_history(
        gradio_history=history, message=message, system_message=system_message
    )

    if return_history:
        # append pending bot message
        history[-1][1] = ""

    # log the actual history
    logging.info("Messages: %r", messages)

    handler = AsyncIteratorCallbackHandler()

    async def wrap_done(fn, event: asyncio.Event):
        """Wrap an awaitable with a event to signal when it's done or an exception is raised."""
        try:
            await fn
        except Exception as e:
            logging.error("Exception: %r", e)
        finally:
            event.set()  # Signal the aiter to stop.

    chat = AzureChatOpenAI(
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        streaming=True,
        callbacks=[handler],
        temperature=temperature,
        max_tokens=max_tokens if max_tokens > 0 else None,
    )
    task = asyncio.create_task(
        wrap_done(chat.agenerate(messages=[messages]), handler.done)
    )

    content = ""
    async for token in handler.aiter():
        content += token
        if return_history:
            # only update the bot message in the last item
            history[-1][1] += token
            yield history
        else:
            yield content

    await task
    # logging the return value of chat.agenerate
    logging.info("Return value of chat.agenerate: %r", task.result())


"""
Chat
"""


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
    msg = gr.Textbox(label="Your Message")
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

"""
Chat (Gradio Version)
"""
chat_gr_tab = gr.ChatInterface(
    agenerate_new_text,
)

with gr.Blocks() as writing_tab:

    def text_to_tokens(text):
        return re.split(r"(\s+)", text)

    def diff_texts(text1, text2, word_level=True):
        d = difflib.Differ()

        if word_level:
            comp_results = d.compare(text_to_tokens(text1), text_to_tokens(text2))
        else:
            comp_results = d.compare(text1, text2)

        ret_old = []
        ret_new = []
        for line in comp_results:
            if line[0] in ("+", "-"):
                ret = ret_new if line[0] == "+" else ret_old
                ret.append((line[2:], line[0]))
                if line[2:] == "\n":
                    ret.append((line[2:], line[0]))
            elif line[0] == " ":
                ret_new.append((line[2:], None))
                ret_old.append((line[2:], None))

        return ret_old, ret_new

    input = gr.Textbox(lines=4, label="Input", show_copy_button=True)

    with gr.Row():
        correct_btn = gr.Button(value="Correct")
        refine_btn = gr.Button(value="Refine")

    output = gr.Textbox(lines=4, label="Output", show_copy_button=True)
    word_level = gr.Checkbox(label="Word Level Diff")
    with gr.Row():
        diff_input = gr.HighlightedText(
            label="Diff (input)",
            combine_adjacent=True,
            show_legend=True,
            color_map={"+": "green", "-": "red"},
        )
        diff_output = gr.HighlightedText(
            label="Diff (output)",
            combine_adjacent=True,
            show_legend=True,
            color_map={"+": "green", "-": "red"},
        )

    correct_system_message = gr.Textbox(
        value=WRITING_CORRECT_SYSTEM_MESSAGE, lines=4, label="System Message (Correct)"
    )
    refine_system_message = gr.Textbox(
        value=WRITING_REFINE_SYSTEM_MESSAGE, lines=4, label="System Message (Refine)"
    )

    def submit(input, system_message):
        new_messages = generate_new_messages(input, [], system_message=system_message)
        for new_message in new_messages:
            if isinstance(new_message, AIMessage):
                output_value = new_message.content
                return output_value

    diff_in_args = [input, output, word_level]
    diff_out_args = [diff_input, diff_output]
    input.change(diff_texts, diff_in_args, diff_out_args, queue=False)
    output.change(diff_texts, diff_in_args, diff_out_args, queue=False)
    word_level.change(diff_texts, diff_in_args, diff_out_args, queue=False)

    # deault: correct
    input.submit(submit, [input, correct_system_message], [output], queue=False)
    correct_btn.click(submit, [input, correct_system_message], [output], queue=False)
    refine_btn.click(submit, [input, refine_system_message], [output], queue=False)

demo = gr.TabbedInterface(
    [chat_tab, chat_gr_tab, writing_tab],
    tab_names=["Chat", "Chat (gr)", "Writing"],
    css="footer {visibility: hidden}",
    title=f"Chat with {BOT_NAME} (HJY AI bot)",
)
demo.queue().launch(share=False)
