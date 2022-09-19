# -*- coding: utf-8 -*-
import ipywidgets as ipw


def get_start_widget(appbase, jupbase, notebase):
    return ipw.HTML(
        f"""
    <div align="center">
        <a href="{appbase}/code-setup.ipynb" target="_blank">
            code setup
        </a>
    </div>"""
    )