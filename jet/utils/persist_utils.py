import logging
from typing import Literal

import gradio as gr
from utils.db_utils import read_user_state, update_user_state

_REGISTERED_COMPONENTS = {}


def make_component_persist(
    root_block: gr.Blocks,
    component: gr.components.Component,
    mode,
):
    """
    NOTE: please call this function before exiting **any** `with` blocks of `gradio.Blocks()`
    """
    assert isinstance(
        component, gr.components.Component
    ), f"component {component} is not a gradio component, it is a {type(component)}"

    assert hasattr(component, "elem_id"), f"component {component} has no elem_id"
    elem_id = component.elem_id
    assert hasattr(
        component, "change"
    ), f"component {component} ({elem_id}) has no change event"

    if elem_id in _REGISTERED_COMPONENTS:
        logging.warning(
            f"component {component} ({elem_id}) has already been registered, the storage will be shared"
        )
    else:
        _REGISTERED_COMPONENTS[elem_id] = component

    """
    Special case: if the component has load_fn
    default behavior: load_fn will be called when the component is loaded
    """

    replace_load_fn = False
    if hasattr(component, "load_event_to_attach") and component.load_event_to_attach:
        load_fn, every = component.load_event_to_attach
        if every:
            logging.warning(
                "skip make_component_persist on %r because it has load event with every not None",
                elem_id,
            )
        else:
            assert every is None
            logging.info(
                "make_component_persist on %r by replacing load_fn",
                elem_id,
            )

            def new_fn(request: gr.Request):
                default_value = load_fn()
                state = read_user_state(
                    request.username, key=elem_id, default=default_value
                )
                return state

            replace_load_fn = True
            component.load_event_to_attach = (new_fn, None)

    def load_session(request: gr.Request):
        state = read_user_state(request.username, key=elem_id)
        return state

    def save_session(value, request: gr.Request):
        update_user_state(request.username, key=elem_id, value=value)

    if not replace_load_fn:
        root_block.load(load_session, inputs=[], outputs=[component], queue=False)

    if mode == "change":
        component.change(save_session, inputs=[component], outputs=[], queue=False)
    elif mode == "input":
        component.input(save_session, inputs=[component], outputs=[], queue=False)
    elif mode == "manual":
        # workaround for https://github.com/gradio-app/gradio/issues/5800
        component.save_session_kwargs = {
            "fn": save_session,
            "inputs": [component],
            "outputs": [],
        }
    else:
        raise ValueError(f"unknown mode {mode}")

    return component


def persist(comp, mode: Literal["change", "input", "manual"] = "change"):
    """
    NOTE: please call this function before exiting **any** `with` blocks of `gradio.Blocks()`
    """
    root_block = gr.context.Context.root_block
    return make_component_persist(root_block, comp, mode)
