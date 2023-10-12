import gradio as gr
from utils.whisper_utils import transcribe_audio_data


def create_speech_tab(tab_id=""):
    with gr.Blocks() as speech_tab:
        with gr.Row():
            with gr.Column():
                audio_source = gr.Dropdown(
                    label="Audio Source",
                    choices=["microphone", "upload"],
                    value="microphone",
                )
                audio_input = gr.Audio(label="Audio Input", source="microphone")

            with gr.Column():
                audio_output = gr.Text(label="Audio Output", lines=4, interactive=True)

        submit_btn = gr.Button(value="Submit", variant="primary")
        clear_btn = gr.Button(value="Clear", variant="secondary")

        with gr.Accordion("System Message", open=False):
            whisper_prompt = gr.Textbox(
                value="",
                lines=4,
                label="Whisper Prompt",
                show_label=False,
                info="The prompt is limited to only 224 tokens.",
            )

            whisper_prompt_examples = gr.Examples(
                [
                    "Use the term 'Dr. HeLLO'.",
                    "以下是经过校对的中文讲稿：",
                    "Keep all non-speech sounds.",
                ],
                inputs=[whisper_prompt],
                label="Whisper Prompt Examples",
            )

        def update_audio_input_source(audio_source):
            assert audio_source in ["microphone", "upload"]
            return gr.Audio(source=audio_source)

        def submit_audio(audio, whisper_prompt):
            sr, data = audio
            transcript = transcribe_audio_data(sr, data, whisper_prompt)
            return transcript

        def clear_audio():
            return None

        audio_source.change(
            update_audio_input_source, inputs=[audio_source], outputs=[audio_input]
        )

        submit_btn.click(
            submit_audio, inputs=[audio_input, whisper_prompt], outputs=[audio_output]
        )
        clear_btn.click(clear_audio, inputs=[], outputs=[audio_input])

    return speech_tab
