# -*- coding: utf-8 -*-
from pathlib import Path
from threading import Thread
from shutil import which

from subprocess import CalledProcessError, run
import ipywidgets as ipw
import traitlets

from aiidalab_code_setup.utils import ProgressBar
from filelock import FileLock, Timeout
__all__ = [
    "CodeSetupWidget",
]

# label: code_name, code_package_name, version
CODE_DB = {
    "qe-7.0": ("quantum-espresso", "qe", "7.0"),
}

CONDA_ENV_PREFIX = Path.home().joinpath(
    ".conda", "envs"
)
CACHE_PATH = Path.home().joinpath(".cache", "aiidalab")
CACHE_PATH.mkdir(parents=True, exist_ok=True)
FN_LOCKFILE = CACHE_PATH.joinpath("install-qe-on-localhost.lock")

def conda_env_exist(code_name, version):
    return CONDA_ENV_PREFIX.joinpath(f"{code_name}-{version}").exists()

def code_is_installed(package_name, version):
    flag_path = CACHE_PATH.joinpath(f"installed_finished-{package_name}-{version}")
    return flag_path.exists()

def install(code_name, package_name, version):
    """Install the simulation code
    """

    conda_installed = which("conda")

    try:
        with FileLock(FN_LOCKFILE, timeout=5):
            if not conda_installed:
                raise RuntimeError(
                    "Unable to automatically install code=xx, conda "
                    "is not available."
                )

            if not conda_env_exist(code_name, version):

                # First, install Quantum ESPRESSO.
                yield "Installing QE..."
                try:
                    _run_install(code_name, package_name, version)
                except CalledProcessError as error:
                    raise RuntimeError(f"Failed to install {code_name} from conda : {error}")
                
            else:
                pass # install without create env
        
    except Timeout:
        # Assume that the installation was triggered by a different process e.g reinstall.
        yield "Installation was already started, waiting for it to finish..."
        with FileLock(FN_LOCKFILE, timeout=120):
            if not code_is_installed(package_name, version):
                raise RuntimeError(
                    "Installation process did not finish in the expected time."
                )

def _run_install(code_name, package_name, version):
    """
    run conda command to install the simulation code.
    code_name: used as conda env name
    package_name: the conda forge name
    version: the version of package in conda forge
    """
    run(
        [
            "conda",
            "create",
            "--yes",
            "--override-channels",
            "--channel",
            "conda-forge",
            "--prefix",
            str(CONDA_ENV_PREFIX.joinpath(f"{code_name}-{version}")),
            f"{package_name}={version}",
        ],
        capture_output=True,
        check=True,
    )

class CodeSetupWidget(ipw.VBox):

    def __init__(self, **kwargs):
        
        self.binary_install = BinaryInstallWidget()

        super().__init__(
            [
                self.binary_install,
                # plugin_code_setup,
            ],
            **kwargs,
        )

class BinaryInstallWidget(ipw.VBox):
    
    code = traitlets.Unicode(allow_none=True)
    installed = traitlets.Bool(allow_none=True).tag(readonly=True)
    busy = traitlets.Bool().tag(readonly=True)
    error = traitlets.Unicode().tag(readonly=True)
    
    def __init__(self, **kwargs):

        code_selector = ipw.Dropdown(
            options=['Select code', 'qe-7.0'],
            value='Select code',
            description='Select simulation code to install.',
            disabled=False,
        )
        code_selector.observe(self._code_selected, names='value')
        
        install_button = ipw.Button(
            icon="cogs",
            description="Install",
            disabled=False,
        )
        install_button.on_click(self.install)
        
        self._progress_bar = ProgressBar(
            description="Installing code:",
            description_layout=ipw.Layout(min_width="300px"),
            layout=ipw.Layout(width="auto", flex="1 1 auto"),
        )
        
        self._info_toggle_button = ipw.ToggleButton(
            icon="info-circle",
            disabled=True,
            layout=ipw.Layout(width="36px"),
        )
        self._info_toggle_button.observe(self._toggle_error_view, "value")
        
        self._error_output = ipw.HTML()
        self._reinstall_button = ipw.Button(
            icon="cogs",
            disabled=True,
            description="Reinstall",
            tooltip="Start another installation attempt.",
        )
        self._reinstall_button.on_click(self._trigger_reinstall)
        
        super().__init__(
            children=[
                code_selector,
                install_button,
                self._reinstall_button,
                ipw.HBox(
                    [self._progress_bar, self._info_toggle_button],
                    layout=ipw.Layout(width="auto"),
                ),
            ],
            **kwargs,
        )
        
    @traitlets.default("installed")
    def _default_installed(self):
        return False
        
    @traitlets.default("busy")
    def _default_busy(self):
        return False

    @traitlets.default("failed")
    def _default_error(self):
        return ""
        
    def _code_selected(self, change):
        if change['new']:
            self.code = change["new"]
            _, package_name, version = CODE_DB.get(self.code)
            
            if code_is_installed(package_name, version):
                self.set_trait("installed", True)
            
        
    def set_message(self, msg):
        self._progress_bar.description = f"{msg}"
        
    def install(self, _):
        thread = Thread(target=self._install)
        thread.start()
        
    def _install(self):
        if self.code is not None:
            code_name, package_name, version = CODE_DB.get(self.code)
        
        try:
            self.set_trait("busy", True)
            for msg in install(code_name, package_name, version):
                self.set_message(msg)
                
        except Exception as error:
            self.set_message(f"Failed to install {code_name} (version {version}).")
            self.set_trait("error", str(error))
        else:
            self._set_finished_flag(package_name, version)
            self.set_trait("installed", True)
            self.set_message("OK")
        finally:
            self.set_trait("busy", False)
            
    def _set_finished_flag(self, package_name, version):
        self._flag_path = CACHE_PATH.joinpath(f"installed_finished-{package_name}-{version}")
        self._flag_path.touch()
        
    @traitlets.observe("error")
    def _observe_error(self, change):
        with self.hold_trait_notifications():
            self._error_output.value = f"""
            <div class="alert alert-warning">
            <p>Failed to install code on localhost, due to error:</p>
            <p><code>{change["new"]}</code></p>
            <hr>
            <p>This means you have to install it manually to run it on this host.
            You could try to make another installation attempt via the button
            below.</p>
            """
            self._info_toggle_button.disabled = not bool(change["new"])
            if not change["new"]:
                self._info_toggle_button.value = False
            
    def _toggle_error_view(self, change):
        self.children += (
            [self._error_output] if change["new"] else []
        )
        
    @traitlets.observe("busy")
    @traitlets.observe("error")
    @traitlets.observe("installed")
    def _update(self, change):
        with self.hold_trait_notifications():
            if self.error or self.installed:
                self._progress_bar.value = 1.0
                self._reinstall_button.disabled = False
            elif self.busy:
                self._progress_bar.value = ProgressBar.AnimationRate(1.0)
            else:
                self._progress_bar.value = 0

            self._progress_bar.bar_style = (
                "info"
                if self.busy
                else (
                    "warning"
                    if self.error
                    else {True: "success", False: ""}.get(self.installed, "")
                )
            )
        
    def _trigger_reinstall(self, _=None):
        self._flag_path.unlink()
        self._install()