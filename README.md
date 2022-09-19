# aiidalab-code-setup

The app is used to quickly install the simulation code from conda and install the corresponting aiida plugin and setup the codes in the profile.
The goal is to:
- Decouple the code setup from qeapp and make a dedicate widget so more vasatile.
- The simulation code with specific version can be installed by using this widget.
- For workflow developers this should be a easy way to have a minimal runnable simulation code that can be used to test the workflow plugin development.
- For use case where a lightweight Quantum Mobile is required with a simulation code installed or easy to install with GUI.