from threading import Event, Thread
from time import time

import ipywidgets as ipw
import traitlets

class ProgressBar(ipw.HBox):
    class AnimationRate(float):
        pass

    description = traitlets.Unicode()
    value = traitlets.Union([traitlets.Float(), traitlets.Instance(AnimationRate)])
    bar_style = traitlets.Unicode()

    _animation_rate = traitlets.Float()

    def __init__(self, description_layout=None, *args, **kwargs):
        if description_layout is None:
            description_layout = ipw.Layout(width="auto", flex="2 1 auto")

        self._label = ipw.Label(layout=description_layout)
        self._progress_bar = ipw.FloatProgress(
            min=0, max=1.0, layout=ipw.Layout(width="auto", flex="1 1 auto")
        )

        traitlets.link((self, "description"), (self._label, "value"))
        traitlets.link((self, "bar_style"), (self._progress_bar, "bar_style"))

        self._animate_stop_event = Event()
        self._animate_thread = None

        super().__init__([self._label, self._progress_bar], *args, **kwargs)

    def _animate(self, refresh_rate=0.01):

        v0 = self._progress_bar.value
        t0 = time()

        while not self._animate_stop_event.wait(refresh_rate):
            self._progress_bar.value = (v0 + (time() - t0) * self._animation_rate) % 1.0

    def _start_animate(self):
        if self._animate_thread is not None:
            raise RuntimeError("Cannot start animation more than once!")

        self._animate_thread = Thread(target=self._animate)
        self._animate_thread.start()

    def _stop_animate(self):
        self._animate_stop_event.set()
        self._animate_thread.join()
        self._animate_stop_event.clear()
        self._animate_thread = None

    @traitlets.default("_animation_rate")
    def _default_animation_rate(self):
        return 0

    @traitlets.observe("_animation_rate")
    def _observe_animation_rate(self, change):
        if change["new"] and not change["old"]:
            self._start_animate()
        elif not change["new"] and change["old"]:
            self._stop_animate()

    @traitlets.validate("value")
    def _validate_value(self, proposal):
        if isinstance(proposal["value"], self.AnimationRate):
            if proposal["value"] < 0:
                raise traitlets.TraitError("The animation rate must be non-negative.")

        elif not 0 <= proposal["value"] <= 1.0:
            raise traitlets.TraitError("The value must be between 0 and 1.0.")

        return proposal["value"]

    @traitlets.observe("value")
    def _observe_value(self, change):
        if isinstance(change["new"], self.AnimationRate):
            self._animation_rate = change["new"]
        else:
            self._animation_rate = 0
            self._progress_bar.value = change["new"]