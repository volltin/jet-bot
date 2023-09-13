# -*- coding: utf-8 -*-
import datetime
import difflib
import logging
import os
import re

import dotenv
import gradio as gr
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


def generate_new_messages(message, history, system_message=None):
    history_langchain_format = []

    if system_message:
        history_langchain_format.append(SystemMessage(content=system_message))

    # construct history
    for human, ai in history:
        if human:
            history_langchain_format.append(HumanMessage(content=human))
        if ai:
            history_langchain_format.append(AIMessage(content=ai))

    # append the current message
    history_langchain_format.append(HumanMessage(content=message))

    # log the actual history
    logging.info("History: %r", history_langchain_format)

    response = chat(history_langchain_format)

    new_messages = [response]
    return new_messages


with gr.Blocks() as chat_tab:
    heading = gr.Markdown(f"# Chat with {BOT_NAME} (HJY AI bot)")
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
    clear = gr.ClearButton([msg, chatbot])
    system_message = gr.Textbox(
        value=get_chat_system_message, lines=4, label="System Message"
    )

    def respond(message, chat_history, system_message):
        chat_history.append((message, None))
        new_messages = generate_new_messages(
            message, chat_history, system_message=system_message
        )
        for new_message in new_messages:
            if isinstance(new_message, HumanMessage):
                chat_history.append((new_message.content, None))
            elif isinstance(new_message, AIMessage):
                chat_history.append((None, new_message.content))
            elif isinstance(new_message, SystemMessage):
                chat_history.append((None, new_message.content))
        return "", chat_history

    msg.submit(respond, [msg, chatbot, system_message], [msg, chatbot], queue=False)


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
    [chat_tab, writing_tab],
    tab_names=["Chat", "Writing"],
    css="footer {visibility: hidden}",
    title=f"Chat with {BOT_NAME}",
)
demo.launch(share=False)
