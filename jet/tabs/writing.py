import re
import difflib
import logging

import dotenv
import gradio as gr
from prompts import WRITING_REFINE_SYSTEM_MESSAGE, WRITING_CORRECT_SYSTEM_MESSAGE
from utils.chat_utils import generate_new_messages

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)


def create_writing_tab(tab_id=""):
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
        word_level = gr.Checkbox(label="Word Level Diff", value=True)
        with gr.Row():
            diff_input = gr.HighlightedText(
                value="",  # workaround for https://github.com/gradio-app/gradio/issues/5584
                label="Diff (input)",
                combine_adjacent=True,
                show_legend=True,
                color_map={"+": "green", "-": "red"},
            )
            diff_output = gr.HighlightedText(
                value="",  # workaround for https://github.com/gradio-app/gradio/issues/5584
                label="Diff (output)",
                combine_adjacent=True,
                show_legend=True,
                color_map={"+": "green", "-": "red"},
            )

        correct_system_message = gr.Textbox(
            value=WRITING_CORRECT_SYSTEM_MESSAGE,
            lines=4,
            label="System Message (Correct)",
        )
        refine_system_message = gr.Textbox(
            value=WRITING_REFINE_SYSTEM_MESSAGE,
            lines=4,
            label="System Message (Refine)",
        )

        def submit(input, system_message):
            new_messages = generate_new_messages(
                input, [], system_message=system_message
            )
            for new_message in new_messages:
                output_value = new_message.content
                return output_value

        diff_in_args = [input, output, word_level]
        diff_out_args = [diff_input, diff_output]
        input.change(diff_texts, diff_in_args, diff_out_args, queue=False)
        output.change(diff_texts, diff_in_args, diff_out_args, queue=False)
        word_level.change(diff_texts, diff_in_args, diff_out_args, queue=False)

        # deault: correct
        input.submit(submit, [input, correct_system_message], [output], queue=False)
        correct_btn.click(
            submit, [input, correct_system_message], [output], queue=False
        )
        refine_btn.click(submit, [input, refine_system_message], [output], queue=False)
    return writing_tab
